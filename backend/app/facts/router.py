from typing import Any

from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel, Field

import pankh_rules
from app.auth.deps import CurrentStudent, SessionDep
from app.facts.service import FactSource, current_facts, record_facts

router = APIRouter(prefix="/me", tags=["me"])


class FactsOut(BaseModel):
    phone: str
    facts: dict[str, Any]


class FactsUpdate(BaseModel):
    facts: dict[str, Any] = Field(
        description="Fact values to record. Use null to withdraw a Fact.",
        examples=[{"is_scheduled_tribe": True, "family_income": 180000}],
    )


@router.get("/facts")
async def get_facts(student: CurrentStudent, session: SessionDep) -> FactsOut:
    return FactsOut(phone=student.phone, facts=await current_facts(session, student.id))


@router.patch("/facts")
async def update_facts(body: FactsUpdate, student: CurrentStudent, session: SessionDep) -> FactsOut:
    try:
        await record_facts(session, student.id, body.facts, FactSource.SELF_DECLARED)
    except pankh_rules.FactError as error:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_CONTENT, str(error)) from error
    await session.commit()
    return FactsOut(phone=student.phone, facts=await current_facts(session, student.id))
