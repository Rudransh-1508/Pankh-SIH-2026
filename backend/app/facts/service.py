import uuid
from enum import StrEnum
from typing import Any

from sqlalchemy import select
from sqlalchemy.dialects.postgresql import distinct_on
from sqlalchemy.ext.asyncio import AsyncSession

import pankh_rules
from app.models import FactRecord


class FactSource(StrEnum):
    SELF_DECLARED = "self_declared"


async def current_facts(session: AsyncSession, student_id: uuid.UUID) -> dict[str, Any]:
    """The newest value of every Fact recorded for the Student, dropping withdrawn ones."""
    rows = (
        await session.execute(
            select(FactRecord.name, FactRecord.value)
            .where(FactRecord.student_id == student_id)
            .ext(distinct_on(FactRecord.name))
            .order_by(FactRecord.name, FactRecord.recorded_at.desc(), FactRecord.id.desc())
        )
    ).all()
    return {name: value for name, value in rows if value is not None}


async def record_facts(
    session: AsyncSession,
    student_id: uuid.UUID,
    updates: dict[str, Any],
    source: FactSource,
) -> None:
    """Record new values. A None value withdraws the Fact. Values are validated first."""
    known = {name: value for name, value in updates.items() if value is not None}
    clean = pankh_rules.validate_facts(known)
    for name in updates:
        if name not in pankh_rules.fact_specs():
            raise pankh_rules.FactError(f"Unknown fact: {name}")
        value = clean.get(name)
        session.add(
            FactRecord(
                student_id=student_id,
                name=name,
                value=value.isoformat() if hasattr(value, "isoformat") else value,
                source=source.value,
            )
        )
    await session.flush()
