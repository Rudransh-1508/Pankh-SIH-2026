import uuid
from dataclasses import dataclass
from datetime import UTC, date, datetime
from enum import StrEnum
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

import pankh_rules
from app.models import FactRecord, Proof


class FactSource(StrEnum):
    SELF_DECLARED = "self_declared"
    DIGILOCKER = "digilocker"
    AISHE = "aishe"
    UDISE = "udise"
    NTA = "nta"
    NPCI = "npci"
    REVIEWER = "reviewer"
    EDISTRICT = "edistrict"
    UPLOADED = "uploaded"
    """Read from a photo the Student uploaded, not yet checked with the issuer."""


@dataclass(frozen=True)
class FactStatus:
    """The value Pankh uses for a Fact, and why it trusts it."""

    value: Any
    source: str
    verified: bool
    proof_id: uuid.UUID | None
    recorded_at: datetime
    expires_at: datetime | None = None
    """When the Proof behind a verified value expires."""


def _stored(value: Any) -> Any:
    return value.isoformat() if isinstance(value, date) else value


async def fact_statuses(session: AsyncSession, student_id: uuid.UUID) -> dict[str, FactStatus]:
    """The value used for every Fact: the newest verified one if any, else the newest given.

    A value confirmed by a source outranks anything the Student types later, until its Proof
    expires. A newer answer that disagrees is kept in the history and raised for review.
    """
    now = datetime.now(UTC)
    rows = (
        await session.execute(
            select(FactRecord, Proof.expires_at)
            .outerjoin(Proof, Proof.id == FactRecord.proof_id)
            .where(FactRecord.student_id == student_id)
            .order_by(FactRecord.recorded_at.desc(), FactRecord.id.desc())
        )
    ).all()
    chosen: dict[str, FactStatus] = {}
    newest: dict[str, FactStatus] = {}
    for record, expires_at in rows:
        verified = record.proof_id is not None and expires_at is not None and expires_at > now
        status = FactStatus(
            record.value,
            record.source,
            verified,
            record.proof_id,
            record.recorded_at,
            expires_at if verified else None,
        )
        newest.setdefault(record.name, status)
        if verified:
            chosen.setdefault(record.name, status)
    result = {name: chosen.get(name, status) for name, status in newest.items()}
    return {name: status for name, status in result.items() if status.value is not None}


async def current_facts(session: AsyncSession, student_id: uuid.UUID) -> dict[str, Any]:
    return {name: s.value for name, s in (await fact_statuses(session, student_id)).items()}


async def record_facts(
    session: AsyncSession,
    student_id: uuid.UUID,
    updates: dict[str, Any],
    source: FactSource,
    proof_id: uuid.UUID | None = None,
) -> None:
    """Record new values. A None value withdraws the Fact. Values are validated first."""
    for name in updates:
        if name not in pankh_rules.fact_specs():
            raise pankh_rules.FactError(f"Unknown fact: {name}")
    known = {name: value for name, value in updates.items() if value is not None}
    clean = pankh_rules.validate_facts(known)
    for name in updates:
        session.add(
            FactRecord(
                student_id=student_id,
                name=name,
                value=_stored(clean.get(name)),
                source=source.value,
                proof_id=proof_id,
            )
        )
    await session.flush()
