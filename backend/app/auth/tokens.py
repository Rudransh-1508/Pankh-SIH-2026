import hashlib
import secrets
import uuid
from dataclasses import dataclass
from datetime import UTC, datetime

import jwt
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import Settings
from app.models import RefreshToken

ALGORITHM = "HS256"
AUDIENCE = "pankh-api"


@dataclass(frozen=True)
class TokenPair:
    access_token: str
    refresh_token: str
    expires_in: int


class InvalidToken(Exception):
    pass


def create_access_token(settings: Settings, student_id: uuid.UUID) -> str:
    now = datetime.now(UTC)
    claims = {
        "sub": str(student_id),
        "aud": AUDIENCE,
        "iat": now,
        "exp": now + settings.access_token_ttl,
    }
    return jwt.encode(claims, settings.secret_key, algorithm=ALGORITHM)


def read_access_token(settings: Settings, token: str) -> uuid.UUID:
    try:
        claims = jwt.decode(token, settings.secret_key, algorithms=[ALGORITHM], audience=AUDIENCE)
        return uuid.UUID(claims["sub"])
    except (jwt.PyJWTError, KeyError, ValueError) as error:
        raise InvalidToken("Sign in again") from error


async def issue_tokens(
    session: AsyncSession, settings: Settings, student_id: uuid.UUID
) -> TokenPair:
    refresh = secrets.token_urlsafe(32)
    session.add(
        RefreshToken(
            student_id=student_id,
            token_hash=_hash(refresh),
            expires_at=datetime.now(UTC) + settings.refresh_token_ttl,
        )
    )
    await session.flush()
    return TokenPair(
        access_token=create_access_token(settings, student_id),
        refresh_token=refresh,
        expires_in=int(settings.access_token_ttl.total_seconds()),
    )


async def rotate_refresh_token(session: AsyncSession, settings: Settings, token: str) -> TokenPair:
    """Exchange a refresh token for a new pair. Reusing an old token ends every session.

    A used token being presented again means it was copied, so all of that Student's sessions
    are revoked and they must sign in again.
    """
    now = datetime.now(UTC)
    record = (
        await session.scalars(
            select(RefreshToken).where(RefreshToken.token_hash == _hash(token)).with_for_update()
        )
    ).first()
    if record is None or record.revoked_at is not None or record.expires_at <= now:
        raise InvalidToken("Sign in again")
    if record.used_at is not None:
        await revoke_all(session, record.student_id)
        raise InvalidToken("Sign in again")
    record.used_at = now
    return await issue_tokens(session, settings, record.student_id)


async def revoke_refresh_token(session: AsyncSession, token: str) -> None:
    await session.execute(
        update(RefreshToken)
        .where(RefreshToken.token_hash == _hash(token))
        .where(RefreshToken.revoked_at.is_(None))
        .values(revoked_at=datetime.now(UTC))
    )


async def revoke_all(session: AsyncSession, student_id: uuid.UUID) -> None:
    await session.execute(
        update(RefreshToken)
        .where(RefreshToken.student_id == student_id)
        .where(RefreshToken.revoked_at.is_(None))
        .values(revoked_at=datetime.now(UTC))
    )


def _hash(token: str) -> str:
    return hashlib.sha256(token.encode()).hexdigest()
