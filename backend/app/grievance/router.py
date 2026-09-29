"""Grievances on CPGRAMS: what the Student could file now, and what they have filed."""

from datetime import UTC, datetime
from typing import Annotated

from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy import select

from app.applications.service import track
from app.auth.deps import CurrentStudent, SessionDep, SettingsDep
from app.grievance.service import CATEGORY, Draft, drafts
from app.models import AuditEvent, Consent, Grievance, Identity, Nudge, Student
from app.sources.cpgrams import CpgramsClient
from app.sources.http import SourceHttp, SourceUnavailable
from app.sources.scholarship_systems import ScholarshipSystemsClient

router = APIRouter(prefix="/me/grievances", tags=["grievances"])


class DraftOut(BaseModel):
    key: str
    kind: str
    scheme: str
    reason: str
    subject: str
    description: str


class GrievanceOut(BaseModel):
    id: str
    kind: str
    registration_number: str
    subject: str
    status: str
    reply: str | None
    filed_at: datetime
    closed_at: datetime | None


class GrievancesOut(BaseModel):
    drafts: list[DraftOut]
    filed: list[GrievanceOut]
    linked: bool


class FileIn(BaseModel):
    key: str
    note: Annotated[str, Field(max_length=500)] = ""


def _out(g: Grievance) -> GrievanceOut:
    return GrievanceOut(
        id=str(g.id),
        kind=g.kind,
        registration_number=g.registration_number,
        subject=g.subject,
        status=g.status,
        reply=g.reply,
        filed_at=g.created_at,
        closed_at=g.closed_at,
    )


async def _drafts(session, student: Student, settings, http) -> tuple[bool, list[Draft]]:
    try:
        tracked = await track(session, student, ScholarshipSystemsClient(http, settings))
    except SourceUnavailable:
        return True, []
    reminders = (
        await session.execute(
            select(Nudge.dedupe_key, Nudge.sent_at)
            .where(Nudge.student_id == student.id)
            .where(Nudge.audience == "office")
            .where(Nudge.status == "sent")
        )
    ).all()
    filed = set(
        (
            await session.scalars(
                select(Grievance.subject_key).where(Grievance.student_id == student.id)
            )
        ).all()
    )
    today = datetime.now(UTC).date()
    reminded = {key: sent_at for key, sent_at in reminders if sent_at is not None}
    return tracked.linked, drafts(tracked.applications, reminded, filed, today)


async def _filed(session, student: Student) -> list[Grievance]:
    return list(
        (
            await session.scalars(
                select(Grievance)
                .where(Grievance.student_id == student.id)
                .order_by(Grievance.created_at.desc())
            )
        ).all()
    )


@router.get("")
async def my_grievances(
    student: CurrentStudent, session: SessionDep, settings: SettingsDep, http: SourceHttp
) -> GrievancesOut:
    linked, found = await _drafts(session, student, settings, http)
    filed = await _filed(session, student)
    cpgrams = CpgramsClient(http, settings)
    for grievance in filed:
        if grievance.closed_at is not None:
            continue
        try:
            record = await cpgrams.status(grievance.registration_number)
        except SourceUnavailable:
            continue
        grievance.status = record["status"]
        grievance.reply = record.get("reply")
        grievance.checked_at = datetime.now(UTC)
        if record.get("closed_on"):
            grievance.closed_at = datetime.fromisoformat(record["closed_on"])
    await session.commit()
    return GrievancesOut(
        drafts=[DraftOut(**d.__dict__) for d in found],
        filed=[_out(g) for g in filed],
        linked=linked,
    )


@router.post("", status_code=status.HTTP_201_CREATED)
async def file_grievance(
    body: FileIn,
    student: CurrentStudent,
    session: SessionDep,
    settings: SettingsDep,
    http: SourceHttp,
) -> GrievanceOut:
    """File one of the drafted grievances, exactly as shown, with the Student's approval."""
    _, found = await _drafts(session, student, settings, http)
    draft = next((d for d in found if d.key == body.key), None)
    if draft is None:
        raise HTTPException(
            status.HTTP_409_CONFLICT,
            "This problem cannot be taken to CPGRAMS now: it is solved, already filed, or "
            "still within its deadline.",
        )
    identity = await session.get(Identity, student.id)
    assert identity is not None  # there are no drafts without linked applications
    description = draft.description
    if body.note.strip():
        description += f" The student adds: {body.note.strip()}"
    try:
        record = await CpgramsClient(http, settings).lodge(
            category=CATEGORY,
            subject=draft.subject,
            description=description,
            name=identity.name,
            mobile=student.phone,
            state=identity.state,
            district=identity.district,
        )
    except SourceUnavailable as error:
        raise HTTPException(
            status.HTTP_503_SERVICE_UNAVAILABLE,
            "CPGRAMS is not responding. Nothing was filed; try again later.",
        ) from error
    grievance = Grievance(
        student_id=student.id,
        subject_key=draft.key,
        kind=draft.kind,
        registration_number=record["registration_number"],
        subject=draft.subject,
        description=description,
        status=record["status"],
    )
    session.add(grievance)
    session.add(
        Consent(
            student_id=student.id,
            source="cpgrams",
            scope="name, mobile number, state and district, and the grievance text",
            purpose=f"File grievance: {draft.subject}",
        )
    )
    await session.flush()
    session.add(
        AuditEvent(
            actor_type="student",
            actor_id=student.id,
            action="grievance.file",
            subject_type="grievance",
            subject_id=grievance.id,
            detail={"registration_number": grievance.registration_number, "key": draft.key},
        )
    )
    await session.commit()
    return _out(grievance)
