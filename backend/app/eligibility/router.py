from typing import Annotated, Any

from fastapi import APIRouter, HTTPException, Query, status
from pydantic import BaseModel, Field

import pankh_rules
from app.academic_year import current_academic_year, label
from app.auth.deps import CurrentStudent, SessionDep
from app.facts.service import current_facts
from app.schemes.schemas import EligibilityOut, SchemeResultOut

router = APIRouter(tags=["eligibility"])

_STATUS_ORDER = {"eligible": 0, "needs_information": 1, "not_eligible": 2}

AcademicYear = Annotated[
    int | None,
    Query(description="Start year of the academic session, e.g. 2026 for 2026-27"),
]


class EligibilityRequest(BaseModel):
    facts: dict[str, Any] = Field(examples=[{"is_scheduled_tribe": True}])


def _judge(facts: dict[str, Any], academic_year: int | None) -> EligibilityOut:
    year = academic_year or current_academic_year()
    try:
        results = pankh_rules.evaluate(facts, year)
    except (pankh_rules.FactError, pankh_rules.UnsupportedAcademicYear) as error:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_CONTENT, str(error)) from error
    schemes = sorted(
        (SchemeResultOut.of(result) for result in results),
        key=lambda result: _STATUS_ORDER[result.status],
    )
    return EligibilityOut(
        academic_year=year,
        academic_year_label=label(year),
        schemes=schemes,
        next_facts=pankh_rules.next_facts(results),
    )


@router.post("/eligibility")
async def check_eligibility(
    body: EligibilityRequest, academic_year: AcademicYear = None
) -> EligibilityOut:
    """Check eligibility without signing in. Nothing is stored."""
    return _judge(body.facts, academic_year)


@router.get("/me/eligibility")
async def my_eligibility(
    student: CurrentStudent, session: SessionDep, academic_year: AcademicYear = None
) -> EligibilityOut:
    return _judge(await current_facts(session, student.id), academic_year)
