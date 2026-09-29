"""Checking one Student and acting on what the planner finds."""

import uuid
from dataclasses import dataclass
from datetime import UTC, date, datetime

import httpx
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.applications.service import track
from app.auth.sms import SmsSender
from app.chasing.planner import OpenIssue, plan
from app.config import Settings
from app.models import AuditEvent, Identity, Nudge, Official, Student, VerificationException
from app.sources.scholarship_systems import ScholarshipSystemsClient

AGENT_ID = uuid.UUID(int=1)  # the chasing agent, as an actor in the audit log


@dataclass(frozen=True)
class CheckResult:
    sent_to_student: int
    proposed_to_offices: int


async def check_student(
    session: AsyncSession,
    settings: Settings,
    http: httpx.AsyncClient,
    sms: SmsSender,
    student_id: uuid.UUID,
) -> CheckResult:
    student = await session.get(Student, student_id)
    identity = await session.get(Identity, student_id)
    if student is None or identity is None:
        return CheckResult(0, 0)
    tracked = await track(session, student, ScholarshipSystemsClient(http, settings))
    issues = (
        await session.scalars(
            select(VerificationException)
            .where(VerificationException.student_id == student_id)
            .where(VerificationException.status == "open")
        )
    ).all()
    proposals = plan(
        tracked.applications,
        [OpenIssue(str(e.id), e.kind, e.message, e.remedy) for e in issues],
        date.today(),
    )
    known = set(
        (
            await session.scalars(
                select(Nudge.dedupe_key).where(
                    Nudge.dedupe_key.in_([p.dedupe_key for p in proposals])
                )
            )
        ).all()
    )
    sent = proposed = 0
    for proposal in proposals:
        if proposal.dedupe_key in known:
            continue
        nudge = Nudge(
            student_id=student_id,
            audience=proposal.audience,
            kind=proposal.kind,
            message=proposal.message,
            level=proposal.level,
            state=identity.state,
            district=identity.district,
            dedupe_key=proposal.dedupe_key,
            status="proposed",
        )
        session.add(nudge)
        if proposal.audience == "student":
            await sms.send_text(student.phone, f"Pankh: {proposal.message}")
            nudge.status, nudge.sent_at = "sent", datetime.now(UTC)
            sent += 1
        else:
            proposed += 1
        await session.flush()
        session.add(
            AuditEvent(
                actor_type="agent",
                actor_id=AGENT_ID,
                action=f"nudge.{nudge.status}",
                subject_type="nudge",
                subject_id=nudge.id,
                detail={"kind": nudge.kind},
            )
        )
    await session.flush()
    return CheckResult(sent, proposed)


async def send_approved(
    session: AsyncSession, sms: SmsSender, nudge: Nudge, official: Official
) -> int:
    """Send an approved office Nudge to every official at that level in that jurisdiction."""
    query = (
        select(Official).where(Official.level == nudge.level).where(Official.state == nudge.state)
    )
    if nudge.level in ("district", "institute"):
        query = query.where(Official.district == nudge.district)
    recipients = (await session.scalars(query)).all()
    for recipient in recipients:
        await sms.send_text(recipient.phone, f"Pankh: {nudge.message}")
    nudge.status, nudge.sent_at, nudge.decided_by = "sent", datetime.now(UTC), official.id
    session.add(
        AuditEvent(
            actor_type="official",
            actor_id=official.id,
            action="nudge.approve",
            subject_type="nudge",
            subject_id=nudge.id,
            detail={"recipients": len(recipients)},
        )
    )
    return len(recipients)
