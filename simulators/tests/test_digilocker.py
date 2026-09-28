import base64
import hashlib
import secrets
import xml.etree.ElementTree as ET
from urllib.parse import parse_qs, urlparse

import pytest
from httpx import ASGITransport, AsyncClient
from pankh_simulators.app import app
from pankh_simulators.digilocker import CLIENT_ID, CLIENT_SECRET
from pankh_simulators.population import population

REDIRECT = "pankh://digilocker/callback"


@pytest.fixture
async def client():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://sim") as client:
        yield client


def _pkce() -> tuple[str, str]:
    verifier = secrets.token_urlsafe(48)
    challenge = base64.urlsafe_b64encode(hashlib.sha256(verifier.encode()).digest())
    return verifier, challenge.rstrip(b"=").decode()


async def _sign_in(client: AsyncClient, person_id: str) -> str:
    verifier, challenge = _pkce()
    params = {
        "client_id": CLIENT_ID,
        "redirect_uri": REDIRECT,
        "state": "s1",
        "code_challenge": challenge,
        "response_type": "code",
        "code_challenge_method": "S256",
    }
    page = await client.get("/digilocker/public/oauth2/1/authorize", params=params)
    assert page.status_code == 200 and "synthetic people only" in page.text
    consent = await client.post(
        "/digilocker/public/oauth2/1/authorize",
        data={k: params[k] for k in ("client_id", "redirect_uri", "state", "code_challenge")}
        | {"person_id": person_id},
    )
    assert consent.status_code == 302
    query = parse_qs(urlparse(consent.headers["location"]).query)
    assert query["state"] == ["s1"]
    token = await client.post(
        "/digilocker/public/oauth2/1/token",
        data={
            "grant_type": "authorization_code",
            "code": query["code"][0],
            "client_id": CLIENT_ID,
            "client_secret": CLIENT_SECRET,
            "redirect_uri": REDIRECT,
            "code_verifier": verifier,
        },
    )
    assert token.status_code == 200, token.text
    return token.json()["access_token"]


def _person_with_caste_certificate():
    return next(
        p for p in population().people if p.has_caste_certificate and p.has_income_certificate
    )


async def test_full_oauth_flow_and_certificate_xml(client):
    person = _person_with_caste_certificate()
    token = await _sign_in(client, person.id)
    headers = {"Authorization": f"Bearer {token}"}

    user = (await client.get("/digilocker/public/oauth2/1/user", headers=headers)).json()
    assert user["digilockerid"] == person.digilocker_id

    items = (await client.get("/digilocker/public/oauth2/2/files/issued", headers=headers)).json()[
        "items"
    ]
    caste = next(item for item in items if item["doctype"] == "CSCER")
    xml = await client.get(f"/digilocker/public/oauth2/3/xml/{caste['uri']}", headers=headers)
    root = ET.fromstring(xml.text)
    assert root.get("type") == "CSCER"
    assert root.find("IssuedTo/Person").get("name") == person.caste_certificate_spelling
    assert root.find("CertificateData/Caste").get("category") == "ST"


async def test_a_code_works_once_and_needs_the_right_verifier(client):
    person = _person_with_caste_certificate()
    verifier, challenge = _pkce()
    consent = await client.post(
        "/digilocker/public/oauth2/1/authorize",
        data={
            "client_id": CLIENT_ID,
            "redirect_uri": REDIRECT,
            "state": "s",
            "code_challenge": challenge,
            "person_id": person.id,
        },
    )
    code = parse_qs(urlparse(consent.headers["location"]).query)["code"][0]
    form = {
        "grant_type": "authorization_code",
        "code": code,
        "client_id": CLIENT_ID,
        "client_secret": CLIENT_SECRET,
        "redirect_uri": REDIRECT,
        "code_verifier": "wrong",
    }
    assert (await client.post("/digilocker/public/oauth2/1/token", data=form)).status_code == 400
    # The failed attempt used up the code.
    form["code_verifier"] = verifier
    assert (await client.post("/digilocker/public/oauth2/1/token", data=form)).status_code == 400


async def test_documents_need_a_valid_token(client):
    response = await client.get("/digilocker/public/oauth2/2/files/issued")
    assert response.status_code == 401
    bad = {"Authorization": "Bearer nope"}
    assert (await client.get("/digilocker/public/oauth2/1/user", headers=bad)).status_code == 401
