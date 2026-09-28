"""DigiLocker simulator, shaped like DigiLocker's Authorized Partner API.

Implements the OAuth 2.0 authorisation-code flow with PKCE, the issued-documents list and
issuer certificate XML. A Student "signs in" by choosing one of the synthetic people, then
consents to share their documents, exactly where the real flow would ask for an Aadhaar OTP.
"""

import base64
import hashlib
import html
import secrets
import time
import xml.etree.ElementTree as ET
from dataclasses import dataclass
from datetime import date
from pathlib import Path
from string import Template
from typing import Annotated
from urllib.parse import urlencode
from xml.sax.saxutils import quoteattr

from fastapi import APIRouter, Depends, Form, Header, HTTPException, status
from fastapi.responses import HTMLResponse, RedirectResponse, Response

from pankh_simulators.population import Person, population

router = APIRouter(prefix="/digilocker", tags=["DigiLocker"])

CLIENT_ID = "PANKH-SIM"
CLIENT_SECRET = "pankh-simulator-secret"
TOKEN_TTL = 3600
_SIGN_IN_PAGE = Template(
    (Path(__file__).parent / "templates" / "digilocker_sign_in.html").read_text()
)


@dataclass
class _Grant:
    person_id: str
    redirect_uri: str
    code_challenge: str
    expires_at: float


_codes: dict[str, _Grant] = {}
_tokens: dict[str, tuple[str, float]] = {}


def _doc_types(person: Person) -> list[tuple[str, str, str, str]]:
    """(doctype, name, issuer id, issuer name) for every document this person holds."""
    state = person.state.name.lower().replace(" ", "")
    docs = [("ADHAR", "Aadhaar Card", "in.gov.uidai", "Unique Identification Authority of India")]
    if person.has_caste_certificate:
        docs.append(
            (
                "CSCER",
                "Caste Certificate",
                f"in.gov.{state}.edistrict",
                f"e-District, {person.state.name}",
            )
        )
    if person.has_income_certificate:
        docs.append(
            (
                "INCER",
                "Income Certificate",
                f"in.gov.{state}.edistrict",
                f"e-District, {person.state.name}",
            )
        )
    if person.education_level not in ("class_9", "class_10"):
        docs.append(
            (
                "SSCER",
                "Class X Marksheet",
                f"in.gov.{state}.board",
                f"{person.state.name} Board of Secondary Education",
            )
        )
    if person.net_result:
        docs.append(("NETSC", "UGC NET Scorecard", "in.gov.nta", "National Testing Agency"))
    if person.disability_percent:
        docs.append(
            (
                "UDIDC",
                "Disability Certificate (UDID)",
                "in.gov.swavlambancard",
                "Department of Empowerment of Persons with Disabilities",
            )
        )
    return docs


def _uri(person: Person, doctype: str, issuer_id: str) -> str:
    number = hashlib.sha256(f"{person.id}:{doctype}".encode()).hexdigest()[:10].upper()
    return f"{issuer_id}-{doctype}-{number}"


def _person_for_token(authorization: Annotated[str | None, Header()] = None) -> Person:
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "invalid_token")
    entry = _tokens.get(authorization.removeprefix("Bearer "))
    if entry is None or entry[1] < time.time():
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "invalid_token")
    person = population().by_id(entry[0])
    assert person is not None
    return person


PersonFromToken = Annotated[Person, Depends(_person_for_token)]


@router.get("/public/oauth2/1/authorize", response_class=HTMLResponse)
async def authorize(
    client_id: str,
    redirect_uri: str,
    state: str,
    code_challenge: str,
    response_type: str = "code",
    code_challenge_method: str = "S256",
    q: str = "",
) -> str:
    """The sign-in page. Real DigiLocker asks for Aadhaar and an OTP here."""
    if client_id != CLIENT_ID or response_type != "code" or code_challenge_method != "S256":
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "invalid_request")
    words = q.lower().split()
    people = [
        p
        for p in population().people
        if p.is_scheduled_tribe and all(w in f"{p.name} {p.district} {p.id}".lower() for w in words)
    ][:25]
    hidden = "".join(
        f'<input type="hidden" name="{name}" value={quoteattr(value)}>'
        for name, value in (
            ("client_id", client_id),
            ("redirect_uri", redirect_uri),
            ("state", state),
            ("code_challenge", code_challenge),
        )
    )
    rows = "".join(
        f'<button name="person_id" value="{p.id}"><b>{html.escape(p.name)}</b><span>'
        f"{html.escape(p.district)}, {html.escape(p.state.name)}"
        f" · born {p.date_of_birth:%d %b %Y} · {len(_doc_types(p))} documents</span></button>"
        for p in people
    )
    return _SIGN_IN_PAGE.substitute(
        hidden=hidden,
        query=quoteattr(q),
        rows=rows or "<p>No one matches.</p>",
    )


@router.post("/public/oauth2/1/authorize")
async def consent(
    client_id: Annotated[str, Form()],
    redirect_uri: Annotated[str, Form()],
    state: Annotated[str, Form()],
    code_challenge: Annotated[str, Form()],
    person_id: Annotated[str, Form()],
) -> RedirectResponse:
    if client_id != CLIENT_ID or population().by_id(person_id) is None:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "invalid_request")
    code = secrets.token_urlsafe(24)
    _codes[code] = _Grant(person_id, redirect_uri, code_challenge, time.time() + 300)
    separator = "&" if "?" in redirect_uri else "?"
    return RedirectResponse(
        f"{redirect_uri}{separator}{urlencode({'code': code, 'state': state})}",
        status.HTTP_302_FOUND,
    )


@router.post("/public/oauth2/1/token")
async def token(
    grant_type: Annotated[str, Form()],
    code: Annotated[str, Form()],
    client_id: Annotated[str, Form()],
    client_secret: Annotated[str, Form()],
    redirect_uri: Annotated[str, Form()],
    code_verifier: Annotated[str, Form()],
) -> dict:
    grant = _codes.pop(code, None)
    if client_id != CLIENT_ID or client_secret != CLIENT_SECRET:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "invalid_client")
    if grant_type != "authorization_code" or grant is None or grant.expires_at < time.time():
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "invalid_grant")
    challenge = base64.urlsafe_b64encode(hashlib.sha256(code_verifier.encode()).digest()).rstrip(
        b"="
    )
    if grant.redirect_uri != redirect_uri or challenge.decode() != grant.code_challenge:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "invalid_grant")
    access_token = secrets.token_urlsafe(32)
    _tokens[access_token] = (grant.person_id, time.time() + TOKEN_TTL)
    person = population().by_id(grant.person_id)
    assert person is not None
    return {
        "access_token": access_token,
        "token_type": "Bearer",
        "expires_in": TOKEN_TTL,
        "scope": "files.issueddocs userdetails",
        "digilockerid": person.digilocker_id,
        "name": person.name,
        "dob": f"{person.date_of_birth:%d%m%Y}",
        "gender": person.gender,
        "eaadhaar": "Y",
        "reference_key": person.uid_token,
    }


@router.get("/public/oauth2/1/user")
async def user(person: PersonFromToken) -> dict:
    return {
        "digilockerid": person.digilocker_id,
        "name": person.name,
        "dob": f"{person.date_of_birth:%d%m%Y}",
        "gender": person.gender,
        "eaadhaar": "Y",
        "reference_key": person.uid_token,
    }


@router.get("/public/oauth2/2/files/issued")
async def issued(person: PersonFromToken) -> dict:
    return {
        "items": [
            {
                "name": name,
                "type": "file",
                "size": "",
                "date": "",
                "parent": "",
                "mime": ["application/xml", "application/pdf"],
                "uri": _uri(person, doctype, issuer_id),
                "doctype": doctype,
                "description": name,
                "issuerid": issuer_id,
                "issuer": issuer,
            }
            for doctype, name, issuer_id, issuer in _doc_types(person)
        ],
        "resource": "issued",
    }


@router.get("/public/oauth2/3/xml/{uri}")
async def document_xml(uri: str, person: PersonFromToken) -> Response:
    for doctype, name, issuer_id, issuer in _doc_types(person):
        if _uri(person, doctype, issuer_id) == uri:
            xml = _certificate(person, doctype, name, issuer_id, issuer, uri)
            return Response(xml, media_type="application/xml")
    raise HTTPException(status.HTTP_404_NOT_FOUND, "document not found")


def _certificate(
    person: Person, doctype: str, name: str, issuer_id: str, issuer: str, uri: str
) -> str:
    """Issuer certificate XML, following the structure DigiLocker issuers publish."""
    number = uri.rsplit("-", 1)[-1]
    holder_name = person.name
    issued_on = date(2025, 6, 12)
    data: tuple[str, dict[str, str]] | None = None
    if doctype == "ADHAR":
        data = ("Aadhaar", {"uidLast4": person.uid_last4})
    elif doctype == "CSCER":
        assert person.tribe is not None
        holder_name = person.caste_certificate_spelling
        issued_on = date(2019, 3, 4)
        data = (
            "Caste",
            {
                "category": "ST",
                "name": person.tribe.name,
                "pvtg": "Y" if person.tribe.pvtg else "N",
                "state": person.state.name,
                "district": person.district,
            },
        )
    elif doctype == "INCER":
        # A current certificate is for the financial year before the academic session;
        # a stale one is two years older.
        today = date.today()
        session = today.year if today.month >= 4 else today.year - 1
        stale = person.stale_income_certificate
        start = session - (3 if stale else 1)
        issued_on = date(start + 1, 5, 2)
        data = (
            "Income",
            {
                "annualIncome": str(int(person.family_income * (0.8 if stale else 1))),
                "currency": "INR",
                "financialYear": f"{start}-{(start + 1) % 100:02d}",
            },
        )
    elif doctype == "SSCER":
        year = str(person.date_of_birth.year + 16)
        data = (
            "Examination",
            {"name": "Secondary School Examination", "year": year, "result": "PASS"},
        )
    elif doctype == "NETSC":
        jrf = person.net_result == "JRF"
        data = (
            "Examination",
            {
                "name": "UGC NET",
                "rollNumber": person.net_roll_number or "",
                "result": "Qualified for JRF and Assistant Professor"
                if jrf
                else "Qualified for Assistant Professor",
                "category": person.net_result or "",
            },
        )
    elif doctype == "UDIDC":
        data = ("Disability", {"percentage": str(person.disability_percent), "udid": number})

    certificate = ET.Element(
        "Certificate",
        {
            "language": "99",
            "name": name,
            "type": doctype,
            "number": number,
            "issuedAt": person.district,
            "issueDate": f"{issued_on:%d-%m-%Y}",
            "status": "A",
        },
    )
    issued_by = ET.SubElement(certificate, "IssuedBy")
    ET.SubElement(issued_by, "Organization", {"name": issuer, "code": issuer_id, "type": "SG"})
    issued_to = ET.SubElement(certificate, "IssuedTo")
    holder = ET.SubElement(
        issued_to,
        "Person",
        {
            "name": holder_name,
            "dob": f"{person.date_of_birth:%d-%m-%Y}",
            "gender": person.gender,
            "uidLast4": person.uid_last4,
        },
    )
    ET.SubElement(
        holder,
        "Address",
        {
            "district": person.district,
            "state": person.state.name,
            "country": "IN",
        },
    )
    certificate_data = ET.SubElement(certificate, "CertificateData")
    if data:
        ET.SubElement(certificate_data, data[0], data[1])
    ET.indent(certificate)
    return ET.tostring(certificate, encoding="unicode", xml_declaration=True)


def authorize_url(base: str, redirect_uri: str, state: str, code_challenge: str) -> str:
    """For tests and tools: the authorisation URL a client would open."""
    query = urlencode(
        {
            "response_type": "code",
            "client_id": CLIENT_ID,
            "redirect_uri": redirect_uri,
            "state": state,
            "code_challenge": code_challenge,
            "code_challenge_method": "S256",
        }
    )
    return f"{base}/digilocker/public/oauth2/1/authorize?{query}"
