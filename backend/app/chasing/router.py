import uuid
from datetime import datetime
from typing import Annotated, Literal

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel
from sqlalchemy import Select, select

from app.auth.deps import CurrentOfficial, CurrentStudent, SessionDep, SettingsDep
from app.auth.sms import SmsSender, get_sms_sender
from app.chasing.service import check_student, send_approved
from app.models import AuditEvent, Identity, Nudge, Official
from app.sources.http import SourceHttp

router = APIRouter(tags=["nudges"])
SmsDep = Annotated[SmsSender, Depends(get_sms_sender)]


class NudgeOut(BaseModel):
    id: uuid.UUID
    kind: str
    message: str
    level: str | None
    district: str | None
    state: str | None
    status: str
    created_at: datetime


class DecisionIn(BaseModel):
    decision: Literal["approve", "dismiss"]


def _out(n: Nudge) -> NudgeOut:
    return NudgeOut(
        id=n.id,
        kind=n.kind,
        message=n.message,
        level=n.level,
        district=n.district,
        state=n.state,
        status=n.status,
        created_at=n.created_at,
    )


@router.get("/me/nudges")
async def my_nudges(student: CurrentStudent, session: SessionDep) -> list[NudgeOut]:
    """Reminders sent to the Student about their own applications and documents."""
    rows = (
        await session.scalars(
            select(Nudge)
            .where(Nudge.student_id == student.id)
            .where(Nudge.audience == "student")
            .order_by(Nudge.created_at.desc())
            .limit(50)
        )
    ).all()
    return [_out(n) for n in rows]


def _scoped(query: Select, official: Official) -> Select:
    query = query.where(Nudge.audience == "office")
    if official.level == "ministry":
        return query
    query = query.where(Nudge.level == official.level).where(Nudge.state == official.state)
    if official.level in ("district", "institute"):
        query = query.where(Nudge.district == official.district)
    return query


@router.get("/review/nudges")
async def office_nudges(
    official: CurrentOfficial,
    session: SessionDep,
    status_filter: Literal["proposed", "sent", "dismissed"] = Query("proposed", alias="status"),
) -> list[NudgeOut]:
    """Reminders the chasing agent proposes to send to offices. Nothing is sent until approved."""
    query = _scoped(select(Nudge), official).where(Nudge.status == status_filter)
    rows = (await session.scalars(query.order_by(Nudge.created_at))).all()
    return [_out(n) for n in rows]


@router.post("/review/nudges/{nudge_id}/decision")
async def decide_nudge(
    nudge_id: uuid.UUID,
    body: DecisionIn,
    official: CurrentOfficial,
    session: SessionDep,
    sms: SmsDep,
) -> NudgeOut:
    nudge = (
        await session.scalars(_scoped(select(Nudge), official).where(Nudge.id == nudge_id))
    ).first()
    if nudge is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "No such reminder in your area")
    if nudge.status != "proposed":
        raise HTTPException(status.HTTP_409_CONFLICT, "This reminder has already been decided.")
    if body.decision == "approve":
        await send_approved(session, sms, nudge, official)
    else:
        nudge.status, nudge.decided_by = "dismissed", official.id
        session.add(
            AuditEvent(
                actor_type="official",
                actor_id=official.id,
                action="nudge.dismiss",
                subject_type="nudge",
                subject_id=nudge.id,
                detail={},
            )
        )
    await session.commit()
    return _out(nudge)


@router.post("/ministry/chasing/sweep")
async def sweep(
    official: CurrentOfficial,
    session: SessionDep,
    settings: SettingsDep,
    http: SourceHttp,
    sms: SmsDep,
) -> dict[str, int]:
    """Check every linked Student now, as the daily workflow would."""
    if official.level != "ministry":
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Only the ministry can run a sweep.")
    sent = proposed = checked = 0
    for student_id in (await session.scalars(select(Identity.student_id))).all():
        result = await check_student(session, settings, http, sms, student_id)
        sent += result.sent_to_student
        proposed += result.proposed_to_offices
        checked += 1
    await session.commit()
    return {"students_checked": checked, "sent_to_students": sent, "proposed_to_offices": proposed}
