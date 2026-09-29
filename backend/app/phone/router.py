"""Webhooks for the phone line: a provider-neutral one, and Exotel's dynamic Gather."""

import secrets
from typing import Annotated, Any

from fastapi import APIRouter, Header, HTTPException, Query, status
from pydantic import BaseModel, Field

from app.auth.deps import SessionDep, SettingsDep
from app.config import Settings
from app.phone.ivr import Prompt, end, handle
from app.sources.http import SourceHttp

router = APIRouter(prefix="/phone", tags=["phone"])


class StepIn(BaseModel):
    call_sid: Annotated[str, Field(min_length=1, max_length=64)]
    caller: Annotated[str, Field(min_length=1, max_length=20)]
    digits: Annotated[str | None, Field(max_length=8)] = None


class PromptOut(BaseModel):
    say: str
    language: str
    gather: bool
    hangup: bool


def _check(settings: Settings, token: str | None) -> None:
    if token is None or not secrets.compare_digest(token, settings.phone_webhook_token):
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Unknown caller system")


def _out(prompt: Prompt) -> PromptOut:
    return PromptOut(**prompt.__dict__)


@router.post("/ivr")
async def ivr_step(
    body: StepIn,
    session: SessionDep,
    settings: SettingsDep,
    http: SourceHttp,
    x_phone_token: Annotated[str | None, Header()] = None,
) -> PromptOut:
    """One step of a call: what to say, and whether to wait for a key."""
    _check(settings, x_phone_token)
    prompt = await handle(session, settings, http, body.call_sid, body.caller, body.digits)
    await session.commit()
    return _out(prompt)


@router.post("/ivr/{call_sid}/end", status_code=status.HTTP_204_NO_CONTENT)
async def ivr_end(
    call_sid: str,
    session: SessionDep,
    settings: SettingsDep,
    x_phone_token: Annotated[str | None, Header()] = None,
) -> None:
    _check(settings, x_phone_token)
    await end(session, call_sid)
    await session.commit()


@router.get("/exotel/{token}/gather")
async def exotel_gather(
    token: str,
    session: SessionDep,
    settings: SettingsDep,
    http: SourceHttp,
    call_sid: Annotated[str, Query(alias="CallSid", max_length=64)],
    caller: Annotated[str, Query(alias="From", max_length=20)],
    digits: Annotated[str | None, Query(max_length=8)] = None,
) -> dict[str, Any]:
    """Exotel's Gather applet with a dynamic URL. Exotel does not sign requests, so the token is
    part of the URL configured in the Exotel flow. Route the flow's no-input branch to Hangup."""
    _check(settings, token)
    prompt = await handle(session, settings, http, call_sid, caller, (digits or "").strip('"'))
    await session.commit()
    return {
        "gather_prompt": {"text": prompt.say},
        "max_input_digits": 1,
        "finish_on_key": "#",
        "input_timeout": 8,
        "repeat_menu": 2,
        "repeat_gather_prompt": {"text": prompt.say},
    }
