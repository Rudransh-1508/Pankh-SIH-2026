"""Facilitators: teachers and field workers who help Students apply, each with the Student's
consent given on the Student's own phone.
"""

import hashlib
import hmac
import secrets
import uuid
from datetime import UTC, datetime, timedelta
from typing import Annotated, Any

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy import func, select

import pankh_rules
from app.academic_year import current_academic_year
from app.auth.deps import CurrentOfficial, CurrentStudent, SessionDep, SettingsDep
from app.auth.phone import InvalidPhoneNumber, normalise_indian_mobile
from app.auth.router import is_demo_number
from app.auth.sms import SmsSender, get_sms_sender
from app.config import Settings
from app.facts.service import FactSource, current_facts, record_facts
from app.models import (
    AuditEvent,
    Consent,
    FacilitationRequest,
    Facilitator,
    FacilitatorLink,
    Identity,
    Official,
    Student,
    VerificationException,
)

router = APIRouter(tags=["facilitators"])
SmsDep = Annotated[SmsSender, Depends(get_sms_sender)]

CODE_TTL = timedelta(minutes=10)
MAX_ATTEMPTS = 5
MAX_REQUESTS_PER_HOUR = 3


class RegisterIn(BaseModel):
    name: Annotated[str, Field(min_length=2, max_length=120)]
    organisation: Annotated[str, Field(min_length=2, max_length=200)]
    state: Annotated[str, Field(min_length=2, max_length=64)]
    district: Annotated[str, Field(min_length=2, max_length=64)]


class FacilitatorOut(BaseModel):
    id: uuid.UUID
    name: str
    organisation: str
    state: str
    district: str
    status: str
    phone: str | None = None


class AddIn(BaseModel):
    phone: str


class ConfirmIn(BaseModel):
    phone: str
    code: Annotated[str, Field(pattern=r"^\d{6}$")]


class HelpedStudentOut(BaseModel):
    student_id: uuid.UUID
    link_id: uuid.UUID
    name: str
    phone: str
    eligible: list[str]
    answers_needed: int
    next_question: dict[str, Any] | None
    issues: int


class AnswersIn(BaseModel):
    facts: dict[str, Any]


class HelperOut(BaseModel):
    link_id: uuid.UUID
    name: str
    organisation: str


class DecisionIn(BaseModel):
    decision: str = Field(pattern="^(approve|reject)$")


def _out(f: Facilitator, phone: str | None = None) -> FacilitatorOut:
    return FacilitatorOut(
        id=f.id,
        name=f.name,
        organisation=f.organisation,
        state=f.state,
        district=f.district,
        status=f.status,
        phone=phone,
    )


def _hash(settings: Settings, request_for: str, code: str) -> str:
    message = f"facilitation:{request_for}:{code}".encode()
    return hmac.new(settings.secret_key.encode(), message, hashlib.sha256).hexdigest()


async def _mine(session, account: Student) -> Facilitator | None:
    return await session.scalar(select(Facilitator).where(Facilitator.account_id == account.id))


async def _approved(session, account: Student) -> Facilitator:
    facilitator = await _mine(session, account)
    if facilitator is None or facilitator.status != "approved":
        raise HTTPException(
            status.HTTP_403_FORBIDDEN,
            "Your district office has not approved you as a facilitator yet.",
        )
    return facilitator


def _phone(raw: str) -> str:
    try:
        return normalise_indian_mobile(raw)
    except InvalidPhoneNumber as error:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_CONTENT, str(error)) from error


def _audit(session, facilitator: Facilitator, action: str, student_id: uuid.UUID, **detail):
    session.add(
        AuditEvent(
            actor_type="facilitator",
            actor_id=facilitator.id,
            action=action,
            subject_type="student",
            subject_id=student_id,
            detail=detail,
        )
    )


# Becoming a facilitator


@router.post("/me/facilitator", status_code=status.HTTP_201_CREATED)
async def register(
    body: RegisterIn, account: CurrentStudent, session: SessionDep
) -> FacilitatorOut:
    if await _mine(session, account) is not None:
        raise HTTPException(status.HTTP_409_CONFLICT, "You have already registered.")
    facilitator = Facilitator(
        account_id=account.id,
        name=body.name.strip(),
        organisation=body.organisation.strip(),
        state=body.state.strip(),
        district=body.district.strip(),
        status="pending",
    )
    session.add(facilitator)
    await session.commit()
    return _out(facilitator)


@router.get("/me/facilitator")
async def me(account: CurrentStudent, session: SessionDep) -> FacilitatorOut | None:
    facilitator = await _mine(session, account)
    return _out(facilitator) if facilitator else None


# Adding a Student, with their consent


@router.post("/me/facilitator/students", status_code=status.HTTP_202_ACCEPTED)
async def add_student(
    body: AddIn,
    account: CurrentStudent,
    session: SessionDep,
    settings: SettingsDep,
    sms: SmsDep,
) -> dict[str, int | str]:
    """Send a consent code to the Student's phone. They share it only if they agree."""
    facilitator = await _approved(session, account)
    phone = _phone(body.phone)
    if phone == account.phone:
        raise HTTPException(status.HTTP_409_CONFLICT, "This is your own number.")
    recent = await session.scalar(
        select(func.count())
        .select_from(FacilitationRequest)
        .where(FacilitationRequest.phone == phone)
        .where(FacilitationRequest.created_at > datetime.now(UTC) - timedelta(hours=1))
    )
    if (recent or 0) >= MAX_REQUESTS_PER_HOUR:
        raise HTTPException(
            status.HTTP_429_TOO_MANY_REQUESTS, "Too many codes sent to this number. Try later."
        )
    code = f"{secrets.randbelow(10**6):06d}"
    request = FacilitationRequest(
        facilitator_id=facilitator.id,
        phone=phone,
        code_hash="",
        expires_at=datetime.now(UTC) + CODE_TTL,
    )
    session.add(request)
    await session.flush()
    request.code_hash = _hash(settings, str(request.id), code)
    await sms.send_text(
        phone,
        f"Pankh: {facilitator.name} of {facilitator.organisation} wants to help you with your "
        f"scholarship. Share this code with them only if you agree: {code}. It does not let "
        "anyone sign in as you.",
    )
    await session.commit()
    result: dict[str, int | str] = {"expires_in": int(CODE_TTL.total_seconds())}
    if is_demo_number(settings, phone):
        result["demo_code"] = code
    return result


@router.post("/me/facilitator/students/confirm", status_code=status.HTTP_201_CREATED)
async def confirm_student(
    body: ConfirmIn, account: CurrentStudent, session: SessionDep, settings: SettingsDep
) -> dict[str, str]:
    facilitator = await _approved(session, account)
    phone = _phone(body.phone)
    request = await session.scalar(
        select(FacilitationRequest)
        .where(FacilitationRequest.facilitator_id == facilitator.id)
        .where(FacilitationRequest.phone == phone)
        .where(FacilitationRequest.consumed_at.is_(None))
        .order_by(FacilitationRequest.created_at.desc())
        .limit(1)
    )
    invalid = HTTPException(status.HTTP_400_BAD_REQUEST, "That code is not right. Ask again.")
    if request is None or request.expires_at <= datetime.now(UTC):
        raise invalid
    request.attempts += 1
    if request.attempts > MAX_ATTEMPTS:
        await session.commit()
        raise HTTPException(status.HTTP_429_TOO_MANY_REQUESTS, "Too many tries. Send a new code.")
    if not hmac.compare_digest(request.code_hash, _hash(settings, str(request.id), body.code)):
        await session.commit()
        raise invalid
    request.consumed_at = datetime.now(UTC)
    # Facilitator-led registration: a Student without the app gets an account here.
    student = await session.scalar(select(Student).where(Student.phone == phone))
    if student is None:
        student = Student(phone=phone)
        session.add(student)
        await session.flush()
    link = await session.scalar(
        select(FacilitatorLink)
        .where(FacilitatorLink.facilitator_id == facilitator.id)
        .where(FacilitatorLink.student_id == student.id)
    )
    if link is None:
        link = FacilitatorLink(facilitator_id=facilitator.id, student_id=student.id)
        session.add(link)
    link.ended_at = None
    session.add(
        Consent(
            student_id=student.id,
            source="facilitator",
            scope="answer eligibility questions and see eligibility and open issues",
            purpose=f"Help from {facilitator.name}, {facilitator.organisation}",
        )
    )
    await session.flush()
    _audit(session, facilitator, "facilitator.link", student.id)
    await session.commit()
    return {"student_id": str(student.id), "link_id": str(link.id)}


# Helping


async def _link(session, facilitator: Facilitator, student_id: uuid.UUID) -> FacilitatorLink:
    link = await session.scalar(
        select(FacilitatorLink)
        .where(FacilitatorLink.facilitator_id == facilitator.id)
        .where(FacilitatorLink.student_id == student_id)
        .where(FacilitatorLink.ended_at.is_(None))
    )
    if link is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "You are not helping this student.")
    return link


async def _helped(session, link: FacilitatorLink, language: str) -> HelpedStudentOut:
    student = await session.get(Student, link.student_id)
    identity = await session.get(Identity, link.student_id)
    assert student is not None
    facts = await current_facts(session, student.id)
    results = pankh_rules.evaluate(facts, current_academic_year())
    remaining = pankh_rules.next_facts(results)
    question = None
    if remaining:
        spec = pankh_rules.fact_specs()[remaining[0]]
        question = {
            "fact": spec.name,
            "question": spec.question.get(language, spec.question["en"]),
            "kind": spec.kind.value,
            "choices": [
                {"key": c.key, "label": c.labels.get(language, c.label)} for c in spec.choices
            ],
        }
    issues = await session.scalar(
        select(func.count())
        .select_from(VerificationException)
        .where(VerificationException.student_id == student.id)
        .where(VerificationException.status.in_(("open", "rejected")))
    )
    return HelpedStudentOut(
        student_id=student.id,
        link_id=link.id,
        name=identity.name if identity else f"…{student.phone[-4:]}",
        phone=f"…{student.phone[-4:]}",
        eligible=[r.scheme.short_name for r in results if r.status is pankh_rules.Status.ELIGIBLE],
        answers_needed=len(remaining),
        next_question=question,
        issues=issues or 0,
    )


@router.get("/me/facilitator/students")
async def helped_students(
    account: CurrentStudent, session: SessionDep, language: str = "en"
) -> list[HelpedStudentOut]:
    facilitator = await _approved(session, account)
    links = (
        await session.scalars(
            select(FacilitatorLink)
            .where(FacilitatorLink.facilitator_id == facilitator.id)
            .where(FacilitatorLink.ended_at.is_(None))
            .order_by(FacilitatorLink.created_at)
        )
    ).all()
    return [await _helped(session, link, language) for link in links]


@router.post("/me/facilitator/students/{student_id}/answers")
async def answer_for(
    student_id: uuid.UUID,
    body: AnswersIn,
    account: CurrentStudent,
    session: SessionDep,
    language: str = "en",
) -> HelpedStudentOut:
    """Record the Student's answers, as they tell them to the facilitator."""
    facilitator = await _approved(session, account)
    link = await _link(session, facilitator, student_id)
    try:
        await record_facts(session, student_id, body.facts, FactSource.FACILITATOR)
    except pankh_rules.FactError as error:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_CONTENT, str(error)) from error
    _audit(session, facilitator, "facilitator.answer", student_id, facts=sorted(body.facts))
    await session.commit()
    return await _helped(session, link, language)


@router.delete("/me/facilitator/students/{student_id}", status_code=status.HTTP_204_NO_CONTENT)
async def stop_helping(student_id: uuid.UUID, account: CurrentStudent, session: SessionDep) -> None:
    facilitator = await _approved(session, account)
    link = await _link(session, facilitator, student_id)
    link.ended_at = datetime.now(UTC)
    _audit(session, facilitator, "facilitator.unlink", student_id)
    await session.commit()


# The Student's side


@router.get("/me/helpers")
async def my_helpers(student: CurrentStudent, session: SessionDep) -> list[HelperOut]:
    """Facilitators helping this Student, who can stop them at any time."""
    rows = (
        await session.execute(
            select(FacilitatorLink, Facilitator)
            .join(Facilitator, Facilitator.id == FacilitatorLink.facilitator_id)
            .where(FacilitatorLink.student_id == student.id)
            .where(FacilitatorLink.ended_at.is_(None))
        )
    ).all()
    return [
        HelperOut(link_id=link.id, name=f.name, organisation=f.organisation) for link, f in rows
    ]


@router.delete("/me/helpers/{link_id}", status_code=status.HTTP_204_NO_CONTENT)
async def remove_helper(link_id: uuid.UUID, student: CurrentStudent, session: SessionDep) -> None:
    link = await session.get(FacilitatorLink, link_id)
    if link is None or link.student_id != student.id or link.ended_at is not None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "No such helper")
    link.ended_at = datetime.now(UTC)
    session.add(
        AuditEvent(
            actor_type="student",
            actor_id=student.id,
            action="facilitator.revoke",
            subject_type="facilitator_link",
            subject_id=link.id,
            detail={},
        )
    )
    await session.commit()


# Approval by the district office


def _jurisdiction(official: Official, facilitator: Facilitator) -> bool:
    if official.level == "ministry":
        return True
    if official.level == "state":
        return facilitator.state == official.state
    return (
        official.level == "district"
        and facilitator.state == official.state
        and facilitator.district == official.district
    )


@router.get("/review/facilitators")
async def pending_facilitators(
    official: CurrentOfficial, session: SessionDep
) -> list[FacilitatorOut]:
    rows = (
        await session.execute(
            select(Facilitator, Student.phone)
            .join(Student, Student.id == Facilitator.account_id)
            .where(Facilitator.status == "pending")
            .order_by(Facilitator.created_at)
        )
    ).all()
    return [_out(f, phone) for f, phone in rows if _jurisdiction(official, f)]


@router.post("/review/facilitators/{facilitator_id}/decision")
async def decide_facilitator(
    facilitator_id: uuid.UUID, body: DecisionIn, official: CurrentOfficial, session: SessionDep
) -> FacilitatorOut:
    facilitator = await session.get(Facilitator, facilitator_id)
    if facilitator is None or not _jurisdiction(official, facilitator):
        raise HTTPException(status.HTTP_404_NOT_FOUND, "No such facilitator in your area")
    if facilitator.status != "pending":
        raise HTTPException(status.HTTP_409_CONFLICT, "Already decided.")
    facilitator.status = "approved" if body.decision == "approve" else "rejected"
    facilitator.decided_by = official.id
    session.add(
        AuditEvent(
            actor_type="official",
            actor_id=official.id,
            action=f"facilitator.{body.decision}",
            subject_type="facilitator",
            subject_id=facilitator.id,
            detail={},
        )
    )
    await session.commit()
    return _out(facilitator)
