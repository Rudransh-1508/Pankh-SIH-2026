"""Checking a Firebase Authentication ID token: Google sent the SMS and confirmed the number.

The token is a JWT signed by Google. It is trusted only if its signature matches one of
Google's published keys, it was issued for this Firebase project, and it names a phone number.
"""

import asyncio
from datetime import UTC, datetime
from functools import cache

import jwt

JWKS_URL = (
    "https://www.googleapis.com/service_accounts/v1/jwk/securetoken@system.gserviceaccount.com"
)


class InvalidFirebaseToken(Exception):
    pass


@cache
def _keys() -> jwt.PyJWKClient:
    # Google rotates these keys; the client caches them and refetches on an unknown key id.
    return jwt.PyJWKClient(JWKS_URL, cache_keys=True, lifespan=3600)


def _signing_key(token: str):
    return _keys().get_signing_key_from_jwt(token).key


async def verified_phone(token: str, project_id: str) -> str:
    """The phone number a valid Firebase ID token was issued for, in E.164 form."""
    try:
        key = await asyncio.to_thread(_signing_key, token)
        claims = jwt.decode(
            token,
            key,
            algorithms=["RS256"],
            audience=project_id,
            issuer=f"https://securetoken.google.com/{project_id}",
            options={"require": ["exp", "iat", "aud", "iss", "sub"]},
        )
    except (jwt.PyJWTError, OSError) as error:
        raise InvalidFirebaseToken("Sign-in could not be confirmed. Try again.") from error
    if not claims.get("sub") or claims.get("auth_time", 0) > datetime.now(UTC).timestamp() + 60:
        raise InvalidFirebaseToken("Sign-in could not be confirmed. Try again.")
    phone = claims.get("phone_number")
    if not phone:
        raise InvalidFirebaseToken("This sign-in did not confirm a phone number.")
    return phone
