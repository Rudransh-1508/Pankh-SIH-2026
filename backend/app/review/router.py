"""The Reviewer's queue: Exceptions within their jurisdiction, and their decisions."""

import uuid
from datetime import UTC, date, datetime, timedelta
from typing import Any, Literal

from fastapi import APIRouter, HTTPException, Query, status
from pydantic import BaseModel
from sqlalchemy import Select, select

from app.academic_year import current_academic_year
from app.auth.deps import CurrentOfficial, SessionDep, SettingsDep
from app.facts.service import FactSource, fact_statuses, record_facts
from app.models import AuditEvent, Identity, Official, ReferencedDocument, VerificationException
from app.verification.names import match_names
from app.verification.service import issue_proof

router = APIRouter(prefix="/review", tags=["review"])

LEVELS = ("institute", "district", "state", "ministry")


class OfficialOut(BaseModel):
    id: uuid.UUID
    name: str
    level: str
    state: str | None
    district: str | None


class QueueItem(BaseModel):
    id: uuid.UUID
    student_name: str | None
    district: str | None
    state: str | None
    fact_name: str | None
    kind: str
    message: str
    match_score: float | None
    level: str
    status: str
    days_open: int


class NameComparison(BaseModel):
    on_document: str
    on_aadhaar: str
    keys: tuple[str, str]
    score: float


class CaseOut(QueueItem):
    remedy: str | None
    evidence: dict[str, Any]
    resolution: str | None
    facts: dict[str, Any]
    documents: list[str]
    name_comparison: NameComparison | None


class DecisionIn(BaseModel):
    decision: Literal["confirm", "reject", "escalate"]
    note: str


def _scoped(query: Select, official: Official) -> Select:
    """Only Exceptions within the official's jurisdiction and at their level."""
    query = query.join(
        Identity, Identity.student_id == VerificationException.student_id, isouter=True
    )
    if official.level == "ministry":
        return query
    query = query.where(VerificationException.level == official.level)
    query = query.where(Identity.state == official.state)
    if official.level in ("district", "institute"):
        query = query.where(Identity.district == official.district)
    return query


def _item(exception: VerificationException, identity: Identity | None) -> dict[str, Any]:
    return {
        "id": exception.id,
        "student_name": identity.name if identity else None,
        "district": identity.district if identity else None,
        "state": identity.state if identity else None,
        "fact_name": exception.fact_name,
        "kind": exception.kind,
        "message": exception.message,
        "match_score": exception.match_score,
        "level": exception.level,
        "status": exception.status,
        "days_open": (date.today() - exception.created_at.date()).days,
    }


@router.get("/me")
async def me(official: CurrentOfficial) -> OfficialOut:
    return OfficialOut(
        id=official.id,
        name=official.name,
        level=official.level,
        state=official.state,
        district=official.district,
    )


@router.get("/exceptions")
async def queue(
    official: CurrentOfficial,
    session: SessionDep,
    status_filter: Literal["open", "resolved", "rejected"] = Query("open", alias="status"),
) -> list[QueueItem]:
    """Oldest first: the Students who have waited longest come first."""
    query = _scoped(select(VerificationException, Identity), official)
    query = query.where(VerificationException.status == status_filter)
    rows = (await session.execute(query.order_by(VerificationException.created_at))).all()
    return [QueueItem(**_item(exception, identity)) for exception, identity in rows]


async def _case(session, official: Official, exception_id: uuid.UUID):
    query = _scoped(select(VerificationException, Identity), official)
    row = (await session.execute(query.where(VerificationException.id == exception_id))).first()
    if row is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "No such case in your queue")
    return row


@router.get("/exceptions/{exception_id}")
async def case(exception_id: uuid.UUID, official: CurrentOfficial, session: SessionDep) -> CaseOut:
    exception, identity = await _case(session, official, exception_id)
    statuses = await fact_statuses(session, exception.student_id)
    documents = (
        await session.scalars(
            select(ReferencedDocument.name).where(
                ReferencedDocument.student_id == exception.student_id
            )
        )
    ).all()
    comparison = None
    evidence = exception.evidence or {}
    if "name_on_document" in evidence and "name_on_aadhaar" in evidence:
        result = match_names(evidence["name_on_document"], evidence["name_on_aadhaar"])
        comparison = NameComparison(
            on_document=evidence["name_on_document"],
            on_aadhaar=evidence["name_on_aadhaar"],
            keys=(result.left_key, result.right_key),
            score=result.score,
        )
    return CaseOut(
        **_item(exception, identity),
        remedy=exception.remedy,
        evidence=evidence,
        resolution=exception.resolution,
        facts={
            name: {"value": s.value, "source": s.source, "verified": s.verified}
            for name, s in statuses.items()
        },
        documents=list(documents),
        name_comparison=comparison,
    )


@router.post("/exceptions/{exception_id}/decision")
async def decide(
    exception_id: uuid.UUID,
    body: DecisionIn,
    official: CurrentOfficial,
    session: SessionDep,
    settings: SettingsDep,
) -> CaseOut:
    exception, _ = await _case(session, official, exception_id)
    if exception.status != "open":
        raise HTTPException(status.HTTP_409_CONFLICT, "This case has already been decided.")
    note = body.note.strip()
    if not note:
        raise HTTPException(
            status.HTTP_422_UNPROCESSABLE_CONTENT, "Write a short note for the record."
        )
    detail: dict[str, Any] = {"note": note, "level": exception.level}
    if body.decision == "confirm":
        if exception.fact_name is None:
            raise HTTPException(
                status.HTTP_409_CONFLICT, "There is no Fact to confirm on this case."
            )
        statuses = await fact_statuses(session, exception.student_id)
        current = statuses.get(exception.fact_name)
        if current is None:
            raise HTTPException(status.HTTP_409_CONFLICT, "The Student no longer has this Fact.")
        year = current_academic_year()
        proof = issue_proof(
            session,
            settings,
            exception.student_id,
            exception.fact_name,
            current.value,
            source="reviewer",
            issuer=f"{official.name} ({official.level}"
            f"{', ' + official.district if official.district else ''})",
            evidence=f"case:{exception.id}",
            match={"reviewed_by": str(official.id), "note": note},
            expires_at=datetime(year + 1, 6, 30, tzinfo=UTC)
            if exception.fact_name == "family_income"
            else datetime.now(UTC) + timedelta(days=365),
            academic_year=year,
        )
        await session.flush()
        await record_facts(
            session,
            exception.student_id,
            {exception.fact_name: current.value},
            FactSource.REVIEWER,
            proof.id,
        )
        exception.status = "resolved"
        detail["proof_id"] = str(proof.id)
    elif body.decision == "reject":
        exception.status = "rejected"
    else:
        position = LEVELS.index(exception.level)
        if position == len(LEVELS) - 1:
            raise HTTPException(status.HTTP_409_CONFLICT, "The ministry is the last level.")
        exception.level = LEVELS[position + 1]
        detail["escalated_to"] = exception.level
    if body.decision != "escalate":
        exception.resolution = note
        exception.resolved_at = datetime.now(UTC)
    session.add(
        AuditEvent(
            actor_type="official",
            actor_id=official.id,
            action=f"case.{body.decision}",
            subject_type="verification_exception",
            subject_id=exception.id,
            detail=detail,
        )
    )
    await session.commit()
    if body.decision == "escalate" and official.level != "ministry":
        return CaseOut(
            **_item(exception, None),
            remedy=exception.remedy,
            evidence=exception.evidence,
            resolution=None,
            facts={},
            documents=[],
            name_comparison=None,
        )
    return await case(exception_id, official, session)
