"""Exotel's call API, far enough to place a call and see it was placed. No phone rings."""

import itertools
from typing import Annotated

from fastapi import APIRouter, Depends, Form

from pankh_simulators.registers import require_api_key

router = APIRouter(prefix="/exotel", tags=["Exotel"], dependencies=[Depends(require_api_key)])

_counter = itertools.count(1)
calls: list[dict] = []


@router.post("/Calls/connect")
async def connect(
    to: Annotated[str, Form(alias="From")],
    caller_id: Annotated[str, Form(alias="CallerId")],
    url: Annotated[str, Form(alias="Url")],
    custom_field: Annotated[str, Form(alias="CustomField")] = "",
) -> dict:
    sid = f"EXO{next(_counter):08d}"
    calls.append(
        {"Sid": sid, "To": to, "CallerId": caller_id, "Url": url, "CustomField": custom_field}
    )
    return {"Call": {"Sid": sid, "Status": "queued", "To": to}}


@router.get("/Calls")
async def placed() -> list[dict]:
    """Every call placed, for development and tests."""
    return calls
