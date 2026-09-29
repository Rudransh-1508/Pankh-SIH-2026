"""The phone line's keypad menu: one step per keypress, answered from the caller's records.

Answers come from JAGO's grounded handlers, so the phone and the app always say the same thing.
"""

import re
from dataclasses import dataclass
from datetime import UTC, datetime

import httpx
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.phone import InvalidPhoneNumber, normalise_indian_mobile
from app.config import Settings
from app.jago.agent import Jago
from app.jago.texts import TEXT as JAGO_TEXT
from app.jago.tools import ToolContext
from app.models import AuditEvent, Identity, Nudge, PhoneCall, Student
from app.phone.texts import OUTBOUND_WELCOME, TEXT, WELCOME

TOPIC_KEYS = {"applications": "1", "payments": "2", "documents": "3"}

_MENU_INTENTS = {
    "1": "applications",
    "2": "payments",
    "3": "documents",
    "4": "renewal",
    "5": "eligibility",
}


@dataclass(frozen=True)
class Prompt:
    say: str
    language: str  # the language to speak it in: "hi", "en", or "hi,en" for the welcome
    gather: bool = True
    hangup: bool = False


def spoken(text: str, language: str) -> str:
    """Text as it should be read aloud: no symbols a voice would stumble on."""
    text = re.sub(r"https?://\S+", "", text)
    text = text.replace("₹", TEXT[language]["rupees"])
    text = re.sub(r"\s*\n+\s*", ". ", text)
    return re.sub(r"\s{2,}", " ", text).strip()


async def _student(session: AsyncSession, phone: str) -> Student | None:
    return await session.scalar(select(Student).where(Student.phone == phone))


async def handle(
    session: AsyncSession,
    settings: Settings,
    http: httpx.AsyncClient,
    call_sid: str,
    caller: str,
    digits: str | None,
) -> Prompt:
    call = await session.get(PhoneCall, call_sid)
    if call is not None and call.stage == "placed":
        call.stage = "language"
        return Prompt(OUTBOUND_WELCOME, "hi,en")
    if call is None:
        try:
            phone = normalise_indian_mobile(caller)
        except InvalidPhoneNumber:
            phone = caller[:16]
        student = await _student(session, phone)
        call = PhoneCall(
            call_sid=call_sid,
            phone=phone,
            student_id=student.id if student else None,
            stage="language",
            keys=[],
        )
        session.add(call)
        await session.flush()
        return Prompt(WELCOME, "hi,en")

    key = (digits or "").strip()[:1]
    call.keys = [*call.keys, key]
    if call.stage == "language":
        if key not in ("1", "2"):
            return Prompt(OUTBOUND_WELCOME if call.direction == "outbound" else WELCOME, "hi,en")
        call.language = "hi" if key == "1" else "en"
        call.stage = "menu"
        if call.topic is None:
            return _menu(call)
        # A call Pankh placed goes straight to what it is about.
        key, call.topic = TOPIC_KEYS[call.topic], None

    language = call.language or "en"
    text = TEXT[language]
    if key == "0" or not key:
        return _menu(call)
    if call.student_id is None:
        if key == "5":
            return Prompt(f"{text['general']} {text['after']}", language)
        return Prompt(f"{text['invalid']} {text['menu_unregistered']}", language)
    student = await session.get(Student, call.student_id)
    assert student is not None
    if key == "9":
        return Prompt(f"{await _callback(session, student, call)} {text['after']}", language)
    intent = _MENU_INTENTS.get(key)
    if intent is None:
        return Prompt(f"{text['invalid']} {text['menu']}", language)
    ctx = ToolContext(
        session=session, settings=settings, http=http, student=student, language=language
    )
    reply = await Jago(ctx, None).answer(intent)
    # Lines written for chat that point somewhere else on the phone.
    for key in ("renewal_none",):
        if reply.text == JAGO_TEXT[language][key]:
            reply.text = text[key]
    session.add(
        AuditEvent(
            actor_type="student",
            actor_id=student.id,
            action="phone.answer",
            subject_type="student",
            subject_id=student.id,
            detail={"call_sid": call.call_sid, "intent": intent},
        )
    )
    return Prompt(f"{spoken(reply.text, language)} {text['after']}", language)


def _menu(call: PhoneCall) -> Prompt:
    language = call.language or "en"
    key = "menu" if call.student_id else "menu_unregistered"
    return Prompt(TEXT[language][key], language)


async def _callback(session: AsyncSession, student: Student, call: PhoneCall) -> str:
    text = TEXT[call.language or "en"]
    identity = await session.get(Identity, student.id)
    if identity is None or identity.district is None:
        return text["callback_unavailable"]
    today = datetime.now(UTC).date().isoformat()
    key = f"callback:{student.id}:{today}"
    if await session.scalar(select(Nudge.id).where(Nudge.dedupe_key == key)):
        return text["callback_repeat"]
    session.add(
        Nudge(
            student_id=student.id,
            audience="office",
            kind="callback_request",
            message=f"{identity.name} called the Pankh phone line and asked for a call back "
            f"about their scholarship, on {student.phone}.",
            level="district",
            state=identity.state,
            district=identity.district,
            status="proposed",
            dedupe_key=key,
        )
    )
    return text["callback"]


async def end(session: AsyncSession, call_sid: str) -> None:
    call = await session.get(PhoneCall, call_sid)
    if call is not None:
        call.stage = "ended"


async def place_call(
    session: AsyncSession, settings: Settings, http: httpx.AsyncClient, student: Student, topic: str
) -> PhoneCall:
    """Call a Student about one topic. The call runs the same menu once they choose a language."""
    from app.sources.exotel import ExotelClient

    sid = await ExotelClient(http, settings).connect(student.phone, settings.exotel_flow_url, topic)
    call = PhoneCall(
        call_sid=sid,
        phone=student.phone,
        student_id=student.id,
        stage="placed",
        keys=[],
        direction="outbound",
        topic=topic,
    )
    session.add(call)
    return call
