import hashlib
import hmac
import secrets
from datetime import UTC, datetime, timedelta

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import Settings
from app.models import OtpChallenge

CODE_LENGTH = 6
_HOUR = timedelta(hours=1)


class OtpRateLimited(Exception):
    def __init__(self, retry_after_seconds: int) -> None:
        super().__init__(f"Try again in {retry_after_seconds} seconds")
        self.retry_after_seconds = retry_after_seconds


class OtpInvalid(Exception):
    pass


def _hash(settings: Settings, phone: str, code: str) -> str:
    message = f"{phone}:{code}".encode()
    return hmac.new(settings.secret_key.encode(), message, hashlib.sha256).hexdigest()


async def issue_otp(session: AsyncSession, settings: Settings, phone: str) -> str:
    """Create a new code for the phone, enforcing the resend cooldown and hourly limit."""
    now = datetime.now(UTC)
    recent = (
        await session.scalars(
            select(OtpChallenge.created_at)
            .where(OtpChallenge.phone == phone)
            .where(OtpChallenge.created_at > now - settings.otp_resend_cooldown)
        )
    ).first()
    if recent is not None:
        wait = settings.otp_resend_cooldown - (now - recent)
        raise OtpRateLimited(max(1, int(wait.total_seconds())))
    sent_last_hour = await session.scalar(
        select(func.count())
        .select_from(OtpChallenge)
        .where(OtpChallenge.phone == phone)
        .where(OtpChallenge.created_at > now - _HOUR)
    )
    if sent_last_hour >= settings.otp_max_per_hour:
        raise OtpRateLimited(int(_HOUR.total_seconds()))

    code = f"{secrets.randbelow(10**CODE_LENGTH):0{CODE_LENGTH}d}"
    session.add(
        OtpChallenge(
            phone=phone,
            code_hash=_hash(settings, phone, code),
            expires_at=now + settings.otp_ttl,
        )
    )
    await session.flush()
    return code


async def verify_otp(session: AsyncSession, settings: Settings, phone: str, code: str) -> None:
    """Consume the latest live code for the phone if it matches, or raise OtpInvalid."""
    now = datetime.now(UTC)
    challenge = (
        await session.scalars(
            select(OtpChallenge)
            .where(OtpChallenge.phone == phone)
            .where(OtpChallenge.consumed_at.is_(None))
            .where(OtpChallenge.expires_at > now)
            .order_by(OtpChallenge.created_at.desc())
            .limit(1)
            .with_for_update()
        )
    ).first()
    if challenge is None or challenge.attempts >= settings.otp_max_attempts:
        raise OtpInvalid("The code has expired. Request a new one.")
    challenge.attempts += 1
    if not hmac.compare_digest(challenge.code_hash, _hash(settings, phone, code)):
        await session.flush()
        raise OtpInvalid("That code is not correct.")
    challenge.consumed_at = now
