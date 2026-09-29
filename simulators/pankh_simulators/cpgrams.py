"""CPGRAMS, the government's public grievance portal: file a grievance, then follow it.

The real portal has no public API; this follows its lifecycle (registration number, "Under
process", then closed with the office's reply). A grievance is closed by a ministry officer,
which the simulator lets anyone do, for trying the flow end to end.
"""

import itertools
from datetime import UTC, datetime
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field

from pankh_simulators.registers import require_api_key

router = APIRouter(prefix="/cpgrams", tags=["CPGRAMS"], dependencies=[Depends(require_api_key)])

_counter = itertools.count(1)
_grievances: dict[str, dict] = {}


class GrievanceIn(BaseModel):
    ministry: str
    category: str
    subject: Annotated[str, Field(max_length=200)]
    description: Annotated[str, Field(max_length=4000)]
    name: str
    mobile: str
    state: str | None = None
    district: str | None = None


class ReplyIn(BaseModel):
    reply: str


def _public(grievance: dict) -> dict:
    return {k: v for k, v in grievance.items() if k not in ("mobile", "name")}


@router.post("/grievances", status_code=status.HTTP_201_CREATED)
async def lodge(body: GrievanceIn) -> dict:
    now = datetime.now(UTC)
    number = f"MOTRA/E/{now.year}/{next(_counter):07d}"
    _grievances[number] = body.model_dump() | {
        "registration_number": number,
        "status": "Under process",
        "received_on": now.isoformat(),
        "reply": None,
        "closed_on": None,
    }
    return _public(_grievances[number])


@router.get("/grievances/{year}/{serial}")
async def track(year: str, serial: str) -> dict:
    grievance = _grievances.get(f"MOTRA/E/{year}/{serial}")
    if grievance is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "No grievance with that registration number")
    return _public(grievance)


@router.post("/grievances/{year}/{serial}/close")
async def close(year: str, serial: str, body: ReplyIn) -> dict:
    grievance = _grievances.get(f"MOTRA/E/{year}/{serial}")
    if grievance is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "No grievance with that registration number")
    grievance |= {
        "status": "Case closed",
        "reply": body.reply,
        "closed_on": datetime.now(UTC).isoformat(),
    }
    return _public(grievance)
