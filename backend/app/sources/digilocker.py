"""Client for DigiLocker's Authorized Partner API (or its simulator)."""

import base64
import hashlib
import secrets
from dataclasses import dataclass
from datetime import date, datetime
from urllib.parse import urlencode

import httpx

from app.config import Settings
from app.sources.http import SourceUnavailable, raise_for_source


class DigiLockerError(Exception):
    """DigiLocker refused the request, for example an expired or reused code."""


@dataclass(frozen=True)
class AuthorisationRequest:
    url: str
    state: str
    code_verifier: str


@dataclass(frozen=True)
class DigiLockerAccount:
    access_token: str
    digilocker_id: str
    name: str
    date_of_birth: date | None
    gender: str | None
    reference_key: str


@dataclass(frozen=True)
class IssuedDocument:
    uri: str
    doctype: str
    name: str
    issuer_id: str
    issuer: str


class DigiLockerClient:
    def __init__(self, http: httpx.AsyncClient, settings: Settings) -> None:
        self.http = http
        self.settings = settings
        self.base = settings.digilocker_url.rstrip("/")

    def authorisation_request(self) -> AuthorisationRequest:
        verifier = secrets.token_urlsafe(48)
        challenge = base64.urlsafe_b64encode(hashlib.sha256(verifier.encode()).digest())
        state = secrets.token_urlsafe(16)
        query = urlencode(
            {
                "response_type": "code",
                "client_id": self.settings.digilocker_client_id,
                "redirect_uri": self.settings.digilocker_redirect_uri,
                "state": state,
                "code_challenge": challenge.rstrip(b"=").decode(),
                "code_challenge_method": "S256",
            }
        )
        return AuthorisationRequest(
            f"{self.base}/public/oauth2/1/authorize?{query}", state, verifier
        )

    async def exchange_code(self, code: str, code_verifier: str) -> DigiLockerAccount:
        response = await self._call(
            "POST",
            "/public/oauth2/1/token",
            data={
                "grant_type": "authorization_code",
                "code": code,
                "client_id": self.settings.digilocker_client_id,
                "client_secret": self.settings.digilocker_client_secret,
                "redirect_uri": self.settings.digilocker_redirect_uri,
                "code_verifier": code_verifier,
            },
        )
        body = response.json()
        return DigiLockerAccount(
            access_token=body["access_token"],
            digilocker_id=body["digilockerid"],
            name=body["name"],
            date_of_birth=_ddmmyyyy(body.get("dob")),
            gender=body.get("gender"),
            reference_key=body["reference_key"],
        )

    async def issued_documents(self, token: str) -> list[IssuedDocument]:
        response = await self._call("GET", "/public/oauth2/2/files/issued", token=token)
        return [
            IssuedDocument(
                uri=item["uri"],
                doctype=item["doctype"],
                name=item["name"],
                issuer_id=item["issuerid"],
                issuer=item["issuer"],
            )
            for item in response.json()["items"]
        ]

    async def document_xml(self, token: str, uri: str) -> str:
        response = await self._call("GET", f"/public/oauth2/3/xml/{uri}", token=token)
        return response.text

    async def _call(
        self, method: str, path: str, token: str | None = None, **kwargs
    ) -> httpx.Response:
        headers = {"Authorization": f"Bearer {token}"} if token else {}
        try:
            response = await self.http.request(
                method, f"{self.base}{path}", headers=headers, **kwargs
            )
        except httpx.HTTPError as error:
            raise SourceUnavailable(f"DigiLocker could not be reached: {error}") from error
        raise_for_source(response, "DigiLocker")
        if response.status_code >= 400:
            raise DigiLockerError(response.text)
        return response


def _ddmmyyyy(value: str | None) -> date | None:
    if not value:
        return None
    return datetime.strptime(value, "%d%m%Y").date()
