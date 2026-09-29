"""The Family view: a Guardian following each of their children's scholarships.

A Student shares a short code; the Guardian enters it. Nothing is shared without that step,
and either of them can end the link.
"""

import hashlib
import secrets
import uuid
from datetime import UTC, date, datetime, timedelta

from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy import select

import pankh_rules
from app.academic_year import current_academic_year
from app.applications.service import track
from app.auth.deps import CurrentStudent, SessionDep, SettingsDep
from app.facts.service import current_facts
from app.models import (
    AuditEvent,
    FamilyInvite,
    GuardianLink,
    Identity,
    Student,
    VerificationException,
)
from app.sources.http import SourceHttp, SourceUnavailable
from app.sources.scholarship_systems import ScholarshipSystemsClient

router = APIRouter(prefix="/me/family", tags=["family"])

INVITE_TTL = timedelta(hours=24)
_ALPHABET = "ABCDEFGHJKLMNPQRSTUVWXYZ23456789"  # no 0/O or 1/I, which are easy to misread


class InviteOut(BaseModel):
    code: str
    expires_in: int


class AcceptIn(BaseModel):
    code: str = Field(min_length=6, max_length=12)


class ChildApplication(BaseModel):
    scheme: str
    stage: str
    waiting_on: str | None
    received: int
    needs_action: bool


class ChildOut(BaseModel):
    link_id: uuid.UUID
    name: str
    eligible: list[str]
    answers_needed: bool
    applications: list[ChildApplication]
    issues: int
    applications_available: bool


class FamilyOut(BaseModel):
    children: list[ChildOut]
    guardians: list[dict[str, str]]


def _hash(code: str) -> str:
    return hashlib.sha256(code.strip().upper().replace(" ", "").encode()).hexdigest()


@router.post("/invite")
async def invite(student: CurrentStudent, session: SessionDep) -> InviteOut:
    """A code for a Guardian to enter. Valid for a day, and only once."""
    code = "".join(secrets.choice(_ALPHABET) for _ in range(8))
    session.add(
        FamilyInvite(
            code_hash=_hash(code), student_id=student.id, expires_at=datetime.now(UTC) + INVITE_TTL
        )
    )
    await session.commit()
    return InviteOut(code=f"{code[:4]} {code[4:]}", expires_in=int(INVITE_TTL.total_seconds()))


@router.post("/accept", status_code=status.HTTP_201_CREATED)
async def accept(body: AcceptIn, guardian: CurrentStudent, session: SessionDep) -> dict[str, str]:
    record = await session.get(FamilyInvite, _hash(body.code))
    if record is None or record.expires_at <= datetime.now(UTC):
        raise HTTPException(status.HTTP_404_NOT_FOUND, "That code is not valid. Ask for a new one.")
    if record.student_id == guardian.id:
        raise HTTPException(status.HTTP_409_CONFLICT, "This is your own code.")
    await session.delete(record)
    link = await session.scalar(
        select(GuardianLink)
        .where(GuardianLink.guardian_id == guardian.id)
        .where(GuardianLink.student_id == record.student_id)
    )
    if link is None:
        link = GuardianLink(guardian_id=guardian.id, student_id=record.student_id)
        session.add(link)
    link.ended_at = None
    await session.flush()
    session.add(
        AuditEvent(
            actor_type="student",
            actor_id=guardian.id,
            action="family.link",
            subject_type="student",
            subject_id=record.student_id,
            detail={},
        )
    )
    await session.commit()
    return {"link_id": str(link.id)}


async def _child(session, settings, http, link: GuardianLink) -> ChildOut:
    student = await session.get(Student, link.student_id)
    identity = await session.get(Identity, link.student_id)
    assert student is not None
    facts = await current_facts(session, student.id)
    results = pankh_rules.evaluate(facts, current_academic_year())
    applications: list[ChildApplication] = []
    available = True
    if identity is not None:
        try:
            tracked = await track(session, student, ScholarshipSystemsClient(http, settings))
            today = date.today()
            applications = [
                ChildApplication(
                    scheme=pankh_rules.SCHEMES[a.scheme_id].short_name,
                    stage=a.stage.value,
                    waiting_on=a.waiting_on,
                    received=a.received,
                    needs_action=bool(
                        a.deficiency or any(i.problem for i in a.instalments) or a.is_stalled(today)
                    ),
                )
                for a in tracked.applications
            ]
        except SourceUnavailable:
            available = False
    issues = len(
        (
            await session.scalars(
                select(VerificationException.id)
                .where(VerificationException.student_id == student.id)
                .where(VerificationException.status.in_(("open", "rejected")))
            )
        ).all()
    )
    return ChildOut(
        link_id=link.id,
        name=identity.name if identity else f"+91 ••••• {student.phone[-5:]}",
        eligible=[r.scheme.short_name for r in results if r.status is pankh_rules.Status.ELIGIBLE],
        answers_needed=any(r.status is pankh_rules.Status.NEEDS_INFORMATION for r in results),
        applications=applications,
        issues=issues,
        applications_available=available,
    )


@router.get("")
async def family(
    account: CurrentStudent, session: SessionDep, settings: SettingsDep, http: SourceHttp
) -> FamilyOut:
    """The children this account follows, and the Guardians following it."""
    links = (
        await session.scalars(
            select(GuardianLink)
            .where(GuardianLink.guardian_id == account.id)
            .where(GuardianLink.ended_at.is_(None))
            .order_by(GuardianLink.created_at)
        )
    ).all()
    children = [await _child(session, settings, http, link) for link in links]
    following_me = (
        await session.execute(
            select(GuardianLink.id, Student.phone)
            .join(Student, Student.id == GuardianLink.guardian_id)
            .where(GuardianLink.student_id == account.id)
            .where(GuardianLink.ended_at.is_(None))
        )
    ).all()
    await session.commit()
    return FamilyOut(
        children=children,
        guardians=[{"link_id": str(i), "phone": f"+91 ••••• {p[-5:]}"} for i, p in following_me],
    )


@router.delete("/{link_id}", status_code=status.HTTP_204_NO_CONTENT)
async def end_link(link_id: uuid.UUID, account: CurrentStudent, session: SessionDep) -> None:
    """Either the Guardian or the Student can stop the sharing."""
    link = await session.get(GuardianLink, link_id)
    if link is None or account.id not in (link.guardian_id, link.student_id):
        raise HTTPException(status.HTTP_404_NOT_FOUND, "No such family link")
    link.ended_at = datetime.now(UTC)
    session.add(
        AuditEvent(
            actor_type="student",
            actor_id=account.id,
            action="family.end",
            subject_type="guardian_link",
            subject_id=link.id,
            detail={},
        )
    )
    await session.commit()
