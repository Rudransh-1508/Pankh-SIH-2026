from datetime import date
from typing import Literal

from fastapi import APIRouter
from pydantic import BaseModel

import pankh_rules
from app.applications.service import track
from app.applications.tracker import Application, Problem, exclusivity_warning
from app.auth.deps import CurrentStudent, SessionDep, SettingsDep
from app.sources.http import SourceHttp
from app.sources.scholarship_systems import ScholarshipSystemsClient

router = APIRouter(prefix="/me", tags=["applications"])


class ProblemOut(BaseModel):
    reason: str
    fix: str
    letter: str | None = None


class InstalmentOut(BaseModel):
    number: int
    amount: int
    status: Literal["credited", "pending", "on_hold", "failed"]
    initiated_on: date | None
    credited_on: date | None
    reference: str | None
    problem: ProblemOut | None


class TimelineOut(BaseModel):
    label: str
    on: date


class ApplicationOut(BaseModel):
    source_system: str
    external_id: str
    scheme_id: str
    scheme_name: str
    academic_year: str
    stage: Literal[
        "submitted", "under_verification", "sanctioned", "disbursing", "closed", "rejected"
    ]
    status_text: str
    waiting_on: str | None
    days_waiting: int | None
    stalled: bool
    deficiency: ProblemOut | None
    sanctioned_amount: int | None
    received: int
    timeline: list[TimelineOut]
    instalments: list[InstalmentOut]


class ApplicationsOut(BaseModel):
    linked: bool
    stale_sources: list[str]
    warning: str | None
    applications: list[ApplicationOut]


def _problem(problem: Problem | None) -> ProblemOut | None:
    return (
        None
        if problem is None
        else ProblemOut(reason=problem.reason, fix=problem.fix, letter=problem.letter)
    )


def _out(application: Application, today: date) -> ApplicationOut:
    scheme = pankh_rules.SCHEMES[application.scheme_id]
    return ApplicationOut(
        source_system=application.source_system,
        external_id=application.external_id,
        scheme_id=application.scheme_id,
        scheme_name=scheme.name,
        academic_year=application.academic_year,
        stage=application.stage.value,
        status_text=application.status_text,
        waiting_on=application.waiting_on,
        days_waiting=application.days_waiting(today),
        stalled=application.is_stalled(today),
        deficiency=_problem(application.deficiency),
        sanctioned_amount=application.sanctioned_amount,
        received=application.received,
        timeline=[TimelineOut(label=t.label, on=t.on) for t in application.timeline],
        instalments=[
            InstalmentOut(
                number=i.number,
                amount=i.amount,
                status=i.status.value,
                initiated_on=i.initiated_on,
                credited_on=i.credited_on,
                reference=i.reference,
                problem=_problem(i.problem),
            )
            for i in application.instalments
        ],
    )


@router.get("/applications")
async def my_applications(
    student: CurrentStudent, session: SessionDep, settings: SettingsDep, http: SourceHttp
) -> ApplicationsOut:
    """Every Application across NSP, SFMP and the NOS Portal, with every payment traced."""
    tracked = await track(session, student, ScholarshipSystemsClient(http, settings))
    await session.commit()
    today = date.today()
    return ApplicationsOut(
        linked=tracked.linked,
        stale_sources=tracked.stale_sources,
        warning=exclusivity_warning(tracked.applications),
        applications=[_out(a, today) for a in tracked.applications],
    )
