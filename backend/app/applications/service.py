from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.applications.tracker import Application, from_nos, from_nsp, from_sfmp
from app.models import ApplicationSnapshot, Identity, Student
from app.sources.http import SourceUnavailable
from app.sources.scholarship_systems import ScholarshipSystemsClient

_NORMALISE = {"NSP": from_nsp, "SFMP": from_sfmp, "NOS Portal": from_nos}
_ID_FIELD = {"NSP": "application_id", "SFMP": "fellow_id", "NOS Portal": "application_no"}


@dataclass(frozen=True)
class Tracked:
    linked: bool
    applications: list[Application]
    stale_sources: list[str]
    """Systems that could not be reached, whose applications are shown as last seen."""


async def track(
    session: AsyncSession, student: Student, systems: ScholarshipSystemsClient
) -> Tracked:
    identity = await session.get(Identity, student.id)
    if identity is None:
        return Tracked(linked=False, applications=[], stale_sources=[])
    fetchers = {
        "NSP": systems.nsp_applications,
        "SFMP": systems.sfmp_fellowships,
        "NOS Portal": systems.nos_applications,
    }
    snapshots = {
        (s.source_system, s.external_id): s
        for s in (
            await session.scalars(
                select(ApplicationSnapshot).where(ApplicationSnapshot.student_id == student.id)
            )
        ).all()
    }
    records: list[tuple[str, dict[str, Any]]] = []
    stale: list[str] = []
    now = datetime.now(UTC)
    for source, fetch in fetchers.items():
        try:
            fresh = await fetch(identity.reference_key)
        except SourceUnavailable:
            stale.append(source)
            records += [(source, s.record) for (src, _), s in snapshots.items() if src == source]
            continue
        for record in fresh:
            records.append((source, record))
            application = _NORMALISE[source](record)
            key = (source, record[_ID_FIELD[source]])
            snapshot = snapshots.get(key) or ApplicationSnapshot(
                student_id=student.id, source_system=source, external_id=key[1]
            )
            snapshot.scheme_id = application.scheme_id
            snapshot.stage = application.stage.value
            snapshot.waiting_on = application.waiting_on
            snapshot.since = application.since
            snapshot.record = record
            snapshot.fetched_at = now
            session.add(snapshot)
    await session.flush()
    applications = [_NORMALISE[source](record) for source, record in records]
    return Tracked(linked=True, applications=applications, stale_sources=stale)
