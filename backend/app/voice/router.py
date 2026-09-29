"""In-app voice with JAGO: a LiveKit room per conversation, and JAGO's replies for the voice
agent service that listens and speaks in it.
"""

import json
import secrets
import uuid
from typing import Annotated, Literal

from fastapi import APIRouter, Header, HTTPException, status
from livekit import api
from pydantic import BaseModel, Field

from app.auth.deps import CurrentStudent, SessionDep, SettingsDep
from app.jago.agent import Jago
from app.jago.router import ModelDep
from app.jago.tools import ToolContext
from app.models import Student
from app.phone.ivr import spoken
from app.sources.http import SourceHttp

router = APIRouter(tags=["voice"])

AGENT_NAME = "jago"


class SessionIn(BaseModel):
    language: Literal["en", "hi"] = "en"


class SessionOut(BaseModel):
    url: str
    token: str
    room: str


class ReplyIn(BaseModel):
    student_id: uuid.UUID
    language: Literal["en", "hi"] = "en"
    text: Annotated[str, Field(min_length=1, max_length=1000)]


class ReplyOut(BaseModel):
    text: str
    """The reply as it should be spoken: no symbols or links."""


@router.post("/me/voice/session")
async def start_session(
    body: SessionIn, student: CurrentStudent, settings: SettingsDep
) -> SessionOut:
    """A LiveKit room to talk to JAGO in. The token asks LiveKit to send the JAGO voice agent,
    and tells it, in a form only Pankh can sign, whose conversation this is."""
    if not (settings.livekit_url and settings.livekit_api_key and settings.livekit_api_secret):
        raise HTTPException(status.HTTP_503_SERVICE_UNAVAILABLE, "Voice is not set up yet.")
    room = f"jago-{student.id.hex[:12]}-{secrets.token_hex(4)}"
    dispatch = api.RoomAgentDispatch(
        agent_name=AGENT_NAME,
        metadata=json.dumps({"student_id": str(student.id), "language": body.language}),
    )
    token = (
        api.AccessToken(settings.livekit_api_key, settings.livekit_api_secret)
        .with_identity(f"student-{student.id}")
        .with_name("Student")
        .with_ttl(settings.voice_session_ttl)
        .with_grants(api.VideoGrants(room_join=True, room=room, can_publish_data=True))
        .with_room_config(api.RoomConfiguration(agents=[dispatch]))
        .to_jwt()
    )
    return SessionOut(url=settings.livekit_url, token=token, room=room)


@router.post("/voice/reply")
async def voice_reply(
    body: ReplyIn,
    session: SessionDep,
    settings: SettingsDep,
    http: SourceHttp,
    model: ModelDep,
    x_voice_token: Annotated[str | None, Header()] = None,
) -> ReplyOut:
    """For the voice agent service only: JAGO's reply to what the Student said."""
    if x_voice_token is None or not secrets.compare_digest(
        x_voice_token, settings.voice_service_token
    ):
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Unknown voice service")
    student = await session.get(Student, body.student_id)
    if student is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "No such student")
    ctx = ToolContext(
        session=session, settings=settings, http=http, student=student, language=body.language
    )
    reply = await Jago(ctx, model).reply(body.text.strip())
    await session.commit()
    return ReplyOut(text=spoken(reply.text, body.language))
