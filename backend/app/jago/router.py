from functools import cache
from typing import Annotated, Any, Literal

from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field
from sqlalchemy import select

from app.auth.deps import CurrentStudent, SessionDep, SettingsDep
from app.config import Settings
from app.jago.agent import Jago
from app.jago.llm import BedrockModel, ChatModel, OpenAICompatibleModel
from app.jago.tools import ToolContext
from app.models import JagoMessage
from app.sources.http import SourceHttp

router = APIRouter(prefix="/me/jago", tags=["jago"])


def get_model(settings: SettingsDep, http: SourceHttp) -> ChatModel | None:
    """The configured language model, or None to answer without one."""
    if settings.bedrock_model_id:
        return _bedrock(settings.bedrock_model_id, settings.aws_profile, settings.aws_region)
    if settings.llm_base_url and settings.llm_model:
        return OpenAICompatibleModel(settings, http)
    return None


@cache
def _bedrock(model_id: str, profile: str | None, region: str) -> BedrockModel:
    # One client for the process: creating a boto3 session reads credentials from disk.
    return BedrockModel(Settings(bedrock_model_id=model_id, aws_profile=profile, aws_region=region))


ModelDep = Annotated[ChatModel | None, Depends(get_model)]


class MessageIn(BaseModel):
    message: str = Field(min_length=1, max_length=1000)
    language: Literal["en", "hi"] = "en"


class Source(BaseModel):
    title: str
    url: str


class MessageOut(BaseModel):
    role: Literal["user", "assistant"]
    text: str
    sources: list[Source] = []
    suggestions: list[str] = []
    asking: str | None = None


@router.post("")
async def talk(
    body: MessageIn,
    student: CurrentStudent,
    session: SessionDep,
    settings: SettingsDep,
    http: SourceHttp,
    model: ModelDep,
) -> MessageOut:
    """Say something to JAGO. Replies are grounded in the Student's own records and the Rules."""
    ctx = ToolContext(
        session=session, settings=settings, http=http, student=student, language=body.language
    )
    reply = await Jago(ctx, model).reply(body.message.strip())
    await session.commit()
    return MessageOut(
        role="assistant",
        text=reply.text,
        sources=[Source(**s) for s in reply.sources],
        suggestions=reply.suggestions,
        asking=reply.asking,
    )


@router.get("")
async def conversation(student: CurrentStudent, session: SessionDep) -> list[MessageOut]:
    rows = (
        await session.scalars(
            select(JagoMessage)
            .where(JagoMessage.student_id == student.id)
            .order_by(JagoMessage.created_at, JagoMessage.id)
            .limit(200)
        )
    ).all()
    return [_out(row) for row in rows]


def _out(row: JagoMessage) -> MessageOut:
    meta: dict[str, Any] = row.meta or {}
    return MessageOut(
        role=row.role,  # type: ignore[arg-type]
        text=row.content,
        sources=[Source(**s) for s in meta.get("sources", [])],
        suggestions=meta.get("suggestions", []),
        asking=meta.get("asking"),
    )
