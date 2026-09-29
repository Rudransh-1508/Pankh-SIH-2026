from datetime import UTC, datetime, timedelta

from sqlalchemy import func, select, update

from app.db import get_sessionmaker
from app.models import OtpChallenge, RefreshToken


async def test_otp_request_normalises_the_phone_number(client, sms, phone):
    response = await client.post("/v1/auth/otp/request", json={"phone": "098765 43210"})
    assert response.status_code == 202
    assert response.json() == {"phone": phone, "expires_in": 300, "resend_after": 30}
    assert len(sms.sent[phone]) == 6


async def test_only_indian_mobile_numbers_are_accepted(client, sms):
    for phone in ["12345", "+14155552671", "01123456789"]:
        response = await client.post("/v1/auth/otp/request", json={"phone": phone})
        assert response.status_code == 422, phone
    assert sms.sent == {}


async def test_resending_too_soon_is_refused(client, phone):
    await client.post("/v1/auth/otp/request", json={"phone": phone})
    response = await client.post("/v1/auth/otp/request", json={"phone": phone})
    assert response.status_code == 429
    assert 1 <= int(response.headers["Retry-After"]) <= 30


async def test_hourly_limit(client, phone):
    for _ in range(5):
        await client.post("/v1/auth/otp/request", json={"phone": phone})
        await _age_otps(timedelta(seconds=31))
    response = await client.post("/v1/auth/otp/request", json={"phone": phone})
    assert response.status_code == 429


async def test_sign_in_creates_the_student_once(sign_in):
    first = await sign_in()
    assert first["is_new_student"] is True
    await _age_otps(timedelta(seconds=31))
    second = await sign_in()
    assert second["is_new_student"] is False


async def test_wrong_code_is_refused_and_attempts_are_capped(client, sms, phone):
    await client.post("/v1/auth/otp/request", json={"phone": phone})
    right = sms.sent[phone]
    wrong = f"{(int(right) + 1) % 1_000_000:06d}"
    for _ in range(5):
        response = await client.post("/v1/auth/otp/verify", json={"phone": phone, "code": wrong})
        assert response.status_code == 401
    response = await client.post("/v1/auth/otp/verify", json={"phone": phone, "code": right})
    assert response.status_code == 401
    assert "expired" in response.json()["detail"]


async def test_expired_code_is_refused(client, sms, phone):
    await client.post("/v1/auth/otp/request", json={"phone": phone})
    async with get_sessionmaker()() as session:
        await session.execute(
            update(OtpChallenge).values(expires_at=datetime.now(UTC) - timedelta(seconds=1))
        )
        await session.commit()
    response = await client.post(
        "/v1/auth/otp/verify", json={"phone": phone, "code": sms.sent[phone]}
    )
    assert response.status_code == 401


async def test_a_code_works_only_once(client, sms, phone, sign_in):
    await sign_in()
    response = await client.post(
        "/v1/auth/otp/verify", json={"phone": phone, "code": sms.sent[phone]}
    )
    assert response.status_code == 401


async def test_codes_are_not_stored_in_plain_text(client, sms, phone):
    await client.post("/v1/auth/otp/request", json={"phone": phone})
    async with get_sessionmaker()() as session:
        stored = await session.scalar(select(OtpChallenge.code_hash))
    assert sms.sent[phone] not in stored


async def test_refresh_rotates_and_reuse_ends_every_session(client, sign_in):
    tokens = await sign_in()
    response = await client.post(
        "/v1/auth/refresh", json={"refresh_token": tokens["refresh_token"]}
    )
    assert response.status_code == 200
    rotated = response.json()
    assert rotated["refresh_token"] != tokens["refresh_token"]

    reused = await client.post("/v1/auth/refresh", json={"refresh_token": tokens["refresh_token"]})
    assert reused.status_code == 401
    after_reuse = await client.post(
        "/v1/auth/refresh", json={"refresh_token": rotated["refresh_token"]}
    )
    assert after_reuse.status_code == 401
    async with get_sessionmaker()() as session:
        live = await session.scalar(
            select(func.count()).select_from(RefreshToken).where(RefreshToken.revoked_at.is_(None))
        )
    assert live == 0


async def test_sign_out_revokes_the_session(client, sign_in):
    tokens = await sign_in()
    response = await client.post(
        "/v1/auth/sign-out", json={"refresh_token": tokens["refresh_token"]}
    )
    assert response.status_code == 204
    response = await client.post(
        "/v1/auth/refresh", json={"refresh_token": tokens["refresh_token"]}
    )
    assert response.status_code == 401


async def test_personal_endpoints_need_a_valid_token(client):
    assert (await client.get("/v1/me/facts")).status_code == 401
    bad = {"Authorization": "Bearer not-a-token"}
    assert (await client.get("/v1/me/facts", headers=bad)).status_code == 401


async def _age_otps(by: timedelta) -> None:
    async with get_sessionmaker()() as session:
        await session.execute(update(OtpChallenge).values(created_at=OtpChallenge.created_at - by))
        await session.commit()


async def test_a_demo_deployment_shows_codes_only_for_demo_numbers(client, sms):
    from app.config import get_settings
    from app.main import app

    settings = get_settings().model_copy(update={"demo_sign_in": True})
    app.dependency_overrides[get_settings] = lambda: settings
    try:
        demo = (await client.post("/v1/auth/otp/request", json={"phone": "9000000011"})).json()
        assert demo["demo_code"] == sms.sent["+919000000011"]
        real = (await client.post("/v1/auth/otp/request", json={"phone": "9876543210"})).json()
        assert "demo_code" not in real
    finally:
        app.dependency_overrides.pop(get_settings, None)
    normal = (await client.post("/v1/auth/otp/request", json={"phone": "9000000012"})).json()
    assert "demo_code" not in normal
