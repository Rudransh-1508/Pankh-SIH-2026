import uuid
from typing import Annotated, Literal

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert

from app.auth.deps import SessionDep, SettingsDep
from app.auth.otp import OtpInvalid, OtpRateLimited, issue_otp, verify_otp
from app.auth.phone import InvalidPhoneNumber, normalise_indian_mobile
from app.auth.sms import SmsSender, get_sms_sender
from app.auth.tokens import (
    InvalidToken,
    TokenPair,
    create_access_token,
    issue_tokens,
    revoke_refresh_token,
    rotate_refresh_token,
)
from app.models import Official, Student

router = APIRouter(prefix="/auth", tags=["auth"])


class OtpRequest(BaseModel):
    phone: str = Field(examples=["9876543210"])


class OtpRequested(BaseModel):
    phone: str
    expires_in: int
    resend_after: int
    demo_code: str | None = None
    """Only on a demo deployment, and only for the synthetic demo numbers."""


class OtpVerification(BaseModel):
    phone: str
    code: str = Field(pattern=r"^\d{6}$")
    role: Literal["student", "official"] = "student"


class Tokens(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    expires_in: int
    is_new_student: bool = False

    @classmethod
    def of(cls, pair: TokenPair, is_new_student: bool = False) -> "Tokens":
        return cls(
            access_token=pair.access_token,
            refresh_token=pair.refresh_token,
            expires_in=pair.expires_in,
            is_new_student=is_new_student,
        )


class RefreshRequest(BaseModel):
    refresh_token: str


def _phone(raw: str) -> str:
    try:
        return normalise_indian_mobile(raw)
    except InvalidPhoneNumber as error:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_CONTENT, str(error)) from error


@router.post("/otp/request", status_code=status.HTTP_202_ACCEPTED, response_model_exclude_none=True)
async def request_otp(
    body: OtpRequest,
    session: SessionDep,
    settings: SettingsDep,
    sms: Annotated[SmsSender, Depends(get_sms_sender)],
) -> OtpRequested:
    phone = _phone(body.phone)
    try:
        code = await issue_otp(session, settings, phone)
    except OtpRateLimited as error:
        raise HTTPException(
            status.HTTP_429_TOO_MANY_REQUESTS,
            str(error),
            {"Retry-After": str(error.retry_after_seconds)},
        ) from error
    await session.commit()
    await sms.send_otp(phone, code)
    return OtpRequested(
        phone=phone,
        expires_in=int(settings.otp_ttl.total_seconds()),
        resend_after=int(settings.otp_resend_cooldown.total_seconds()),
        demo_code=code if is_demo_number(settings, phone) else None,
    )


def is_demo_number(settings, phone: str) -> bool:
    return settings.demo_sign_in and phone.startswith(settings.demo_phone_prefix)


@router.post("/otp/verify")
async def verify(body: OtpVerification, session: SessionDep, settings: SettingsDep) -> Tokens:
    phone = _phone(body.phone)
    try:
        await verify_otp(session, settings, phone, body.code)
    except OtpInvalid as error:
        await session.commit()  # keep the attempt count
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, str(error)) from error
    if body.role == "official":
        official = await session.scalar(select(Official).where(Official.phone == phone))
        await session.commit()
        if official is None:
            raise HTTPException(
                status.HTTP_403_FORBIDDEN, "This number is not registered as an official."
            )
        return Tokens(
            access_token=create_access_token(
                settings, official.id, role="official", ttl=settings.official_session_ttl
            ),
            refresh_token="",
            expires_in=int(settings.official_session_ttl.total_seconds()),
        )
    created_id = await session.scalar(
        insert(Student)
        .values(id=uuid.uuid4(), phone=phone)
        .on_conflict_do_nothing(index_elements=[Student.phone])
        .returning(Student.id)
    )
    student_id = created_id or await session.scalar(
        select(Student.id).where(Student.phone == phone)
    )
    pair = await issue_tokens(session, settings, student_id)
    await session.commit()
    return Tokens.of(pair, is_new_student=created_id is not None)


@router.post("/refresh")
async def refresh(body: RefreshRequest, session: SessionDep, settings: SettingsDep) -> Tokens:
    try:
        pair = await rotate_refresh_token(session, settings, body.refresh_token)
    except InvalidToken as error:
        await session.commit()  # keep any revocation caused by token reuse
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, str(error)) from error
    await session.commit()
    return Tokens.of(pair)


@router.post("/sign-out", status_code=status.HTTP_204_NO_CONTENT)
async def sign_out(body: RefreshRequest, session: SessionDep) -> None:
    await revoke_refresh_token(session, body.refresh_token)
    await session.commit()
