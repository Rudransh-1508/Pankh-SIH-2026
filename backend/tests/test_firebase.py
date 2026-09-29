import time

import jwt
import pytest
from cryptography.hazmat.primitives.asymmetric import rsa

from app.auth import firebase
from app.config import get_settings
from app.main import app

PROJECT = "pankh-sih"
GOOGLE_KEY = rsa.generate_private_key(public_exponent=65537, key_size=2048)
OTHER_KEY = rsa.generate_private_key(public_exponent=65537, key_size=2048)


def token(key=GOOGLE_KEY, **changes) -> str:
    now = int(time.time())
    claims = {
        "iss": f"https://securetoken.google.com/{PROJECT}",
        "aud": PROJECT,
        "sub": "firebase-uid-1",
        "iat": now,
        "exp": now + 3600,
        "auth_time": now,
        "phone_number": "+919812345678",
    } | changes
    return jwt.encode({k: v for k, v in claims.items() if v is not None}, key, algorithm="RS256")


@pytest.fixture
def firebase_project(monkeypatch):
    # Google's published key, as far as the API can tell.
    monkeypatch.setattr(firebase, "_signing_key", lambda _: GOOGLE_KEY.public_key())
    settings = get_settings().model_copy(update={"firebase_project_id": PROJECT})
    app.dependency_overrides[get_settings] = lambda: settings
    yield
    app.dependency_overrides.pop(get_settings, None)


async def test_a_number_firebase_verified_signs_in(client, firebase_project):
    response = await client.post("/v1/auth/firebase", json={"id_token": token()})
    assert response.status_code == 200, response.text
    body = response.json()
    assert body["is_new_student"] is True
    facts = await client.get(
        "/v1/me/facts", headers={"Authorization": f"Bearer {body['access_token']}"}
    )
    assert facts.json()["phone"] == "+919812345678"
    again = (await client.post("/v1/auth/firebase", json={"id_token": token()})).json()
    assert again["is_new_student"] is False


@pytest.mark.parametrize(
    "bad",
    [
        {"key": OTHER_KEY},
        {"aud": "someone-elses-project"},
        {"iss": "https://securetoken.google.com/someone-elses-project"},
        {"exp": int(time.time()) - 10},
        {"phone_number": None},
    ],
)
async def test_tokens_not_from_google_for_this_project_are_refused(client, firebase_project, bad):
    key = bad.pop("key", GOOGLE_KEY)
    response = await client.post("/v1/auth/firebase", json={"id_token": token(key, **bad)})
    assert response.status_code == 401


async def test_officials_must_be_registered(client, firebase_project):
    response = await client.post(
        "/v1/auth/firebase", json={"id_token": token(), "role": "official"}
    )
    assert response.status_code == 403


async def test_without_a_firebase_project_sms_sign_in_is_off(client):
    response = await client.post("/v1/auth/firebase", json={"id_token": token()})
    assert response.status_code == 503
