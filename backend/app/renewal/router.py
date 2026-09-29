"""Next year's applications for Schemes the Student holds."""

from typing import Any

from fastapi import APIRouter
from pydantic import BaseModel

from app.applications.service import track
from app.auth.deps import CurrentStudent, SessionDep, SettingsDep
from app.facts.service import fact_statuses
from app.renewal.service import plans
from app.sources.http import SourceHttp, SourceUnavailable
from app.sources.scholarship_systems import ScholarshipSystemsClient

router = APIRouter(tags=["renewal"])


class CheckOut(BaseModel):
    id: str
    text: str
    done: bool
    fact: str | None


class PlanOut(BaseModel):
    scheme_id: str
    scheme: str
    held_year: str
    next_year: str
    next_level: str | None
    continuing: bool
    instead: str | None
    status: str
    unmet: list[str]
    checks: list[CheckOut]
    apply_on: str
    apply_url: str
    window: str | None
    carried: list[str]


@router.get("/me/renewals")
async def my_renewals(
    student: CurrentStudent, session: SessionDep, settings: SettingsDep, http: SourceHttp
) -> list[PlanOut]:
    """For each Scheme held this year: next year's application, and what to get ready."""
    try:
        tracked = await track(session, student, ScholarshipSystemsClient(http, settings))
        applications = tracked.applications
    except SourceUnavailable:
        applications = []
    await session.commit()
    statuses = await fact_statuses(session, student.id)
    result: list[dict[str, Any]] = []
    for p in plans(applications, statuses):
        result.append(p.__dict__ | {"checks": [c.__dict__ for c in p.checks]})
    return [PlanOut(**r) for r in result]
