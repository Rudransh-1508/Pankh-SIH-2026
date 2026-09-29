import base64
import uuid
from datetime import datetime
from typing import Annotated, Any

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy import select

from app.auth.deps import CurrentStudent, SessionDep, SettingsDep
from app.chasing.workflows import start_chasing
from app.facts.service import fact_statuses
from app.models import Identity, Proof, ReferencedDocument, VerificationException
from app.sources.digilocker import DigiLockerClient, DigiLockerError
from app.sources.http import SourceHttp, SourceUnavailable
from app.sources.registers import RegistersClient
from app.verification import proofs
from app.verification.service import VerificationError, Verifier

router = APIRouter(tags=["verification"])

# Issues a written request to the issuing office helps with.
ISSUE_LETTERS = {"stale_document": "income_certificate", "name_mismatch": "certificate_correction"}


def get_verifier(session: SessionDep, settings: SettingsDep, http: SourceHttp) -> Verifier:
    return Verifier(
        session, settings, DigiLockerClient(http, settings), RegistersClient(http, settings)
    )


VerifierDep = Annotated[Verifier, Depends(get_verifier)]


class DocumentOut(BaseModel):
    id: uuid.UUID
    doctype: str
    name: str
    issuer: str
    uri: str
    fetched_at: datetime


class ExceptionOut(BaseModel):
    id: uuid.UUID
    fact_name: str | None
    kind: str
    message: str
    remedy: str | None
    status: str
    reviewer_note: str | None = None
    created_at: datetime
    letter: str | None = None
    """A request letter that helps fix this (see app.letters), if one does."""


class ProofOut(BaseModel):
    id: uuid.UUID
    fact_name: str
    source: str
    issued_at: datetime
    expires_at: datetime


class LinkOut(BaseModel):
    documents: list[DocumentOut]
    proofs: list[ProofOut]
    exceptions: list[ExceptionOut]


class StartOut(BaseModel):
    authorization_url: str


class CompleteIn(BaseModel):
    code: str
    state: str


class InstitutionIn(BaseModel):
    code: str


class NetIn(BaseModel):
    roll_number: str


class FactStatusOut(BaseModel):
    value: Any
    source: str
    verified: bool
    proof_id: uuid.UUID | None


class IdentityOut(BaseModel):
    name: str
    date_of_birth: str | None
    gender: str | None
    linked_at: datetime


class VerificationOut(BaseModel):
    identity: IdentityOut | None
    facts: dict[str, FactStatusOut]
    documents: list[DocumentOut]
    exceptions: list[ExceptionOut]


class PublicKeyOut(BaseModel):
    kid: str
    kty: str = "OKP"
    crv: str = "Ed25519"
    x: str


class SignedProofOut(BaseModel):
    payload: dict[str, Any]
    signature: str
    key_id: str
    algorithm: str = "Ed25519"


def _document(d: ReferencedDocument) -> DocumentOut:
    return DocumentOut(
        id=d.id, doctype=d.doctype, name=d.name, issuer=d.issuer, uri=d.uri, fetched_at=d.fetched_at
    )


def _exception(e: VerificationException) -> ExceptionOut:
    return ExceptionOut(
        id=e.id,
        fact_name=e.fact_name,
        kind=e.kind,
        message=e.message,
        remedy=e.remedy,
        status=e.status,
        reviewer_note=e.resolution,
        created_at=e.created_at,
        letter=ISSUE_LETTERS.get(e.kind),
    )


def _proof(p: Proof) -> ProofOut:
    return ProofOut(
        id=p.id,
        fact_name=p.fact_name,
        source=p.payload["source"],
        issued_at=p.issued_at,
        expires_at=p.expires_at,
    )


async def _run(action):
    try:
        return await action
    except VerificationError as error:
        raise HTTPException(status.HTTP_409_CONFLICT, str(error)) from error
    except DigiLockerError as error:
        raise HTTPException(
            status.HTTP_400_BAD_REQUEST, "DigiLocker did not accept that sign-in. Start again."
        ) from error
    except SourceUnavailable as error:
        raise HTTPException(
            status.HTTP_503_SERVICE_UNAVAILABLE,
            "That record service is not responding. Try again in a few minutes.",
        ) from error


@router.post("/me/digilocker/start")
async def start_digilocker(
    student: CurrentStudent, verifier: VerifierDep, session: SessionDep
) -> StartOut:
    """Begin linking DigiLocker. Open the returned URL; DigiLocker sends the Student back."""
    url = await verifier.start_digilocker(student)
    await session.commit()
    return StartOut(authorization_url=url)


@router.post("/me/digilocker/complete")
async def complete_digilocker(
    body: CompleteIn, student: CurrentStudent, verifier: VerifierDep, session: SessionDep
) -> LinkOut:
    """Finish linking: read the Student's documents and confirm the Facts they prove."""
    result = await _run(verifier.complete_digilocker(student, body.code, body.state))
    await session.commit()
    await start_chasing(str(student.id))
    return LinkOut(
        documents=[_document(d) for d in result.documents],
        proofs=[_proof(p) for p in result.proofs],
        exceptions=[_exception(e) for e in result.exceptions if e.status == "open"],
    )


@router.post("/me/verifications/institution")
async def verify_institution(
    body: InstitutionIn, student: CurrentStudent, verifier: VerifierDep, session: SessionDep
) -> list[ProofOut]:
    issued = await _run(verifier.verify_institution(student, body.code))
    await session.commit()
    return [_proof(p) for p in issued]


@router.post("/me/verifications/net")
async def verify_net(
    body: NetIn, student: CurrentStudent, verifier: VerifierDep, session: SessionDep
) -> list[ProofOut]:
    issued = await _run(verifier.verify_net(student, body.roll_number))
    await session.commit()
    return [_proof(p) for p in issued]


@router.post("/me/verifications/bank")
async def verify_bank(
    student: CurrentStudent, verifier: VerifierDep, session: SessionDep
) -> list[ProofOut]:
    issued = await _run(verifier.verify_bank_seeding(student))
    await session.commit()
    return [_proof(p) for p in issued]


@router.get("/me/verification")
async def my_verification(student: CurrentStudent, session: SessionDep) -> VerificationOut:
    """What is confirmed, from where, and what still needs attention."""
    identity = await session.get(Identity, student.id)
    documents = (
        await session.scalars(
            select(ReferencedDocument)
            .where(ReferencedDocument.student_id == student.id)
            .order_by(ReferencedDocument.name)
        )
    ).all()
    exceptions = (
        await session.scalars(
            select(VerificationException)
            .where(VerificationException.student_id == student.id)
            .where(VerificationException.status.in_(("open", "rejected")))
            .order_by(VerificationException.created_at.desc())
        )
    ).all()
    statuses = await fact_statuses(session, student.id)
    return VerificationOut(
        identity=None
        if identity is None
        else IdentityOut(
            name=identity.name,
            date_of_birth=identity.date_of_birth.isoformat() if identity.date_of_birth else None,
            gender=identity.gender,
            linked_at=identity.linked_at,
        ),
        facts={
            name: FactStatusOut(
                value=s.value, source=s.source, verified=s.verified, proof_id=s.proof_id
            )
            for name, s in statuses.items()
        },
        documents=[_document(d) for d in documents],
        exceptions=[_exception(e) for e in exceptions],
    )


@router.get("/proofs/keys", tags=["proofs"])
async def proof_keys(settings: SettingsDep) -> list[PublicKeyOut]:
    """Public keys for checking Proof signatures, in JWK form."""
    raw = proofs.public_key_bytes(settings)
    return [
        PublicKeyOut(
            kid=proofs.key_id(settings), x=base64.urlsafe_b64encode(raw).rstrip(b"=").decode()
        )
    ]


@router.get("/proofs/{proof_id}", tags=["proofs"])
async def get_proof(proof_id: uuid.UUID, session: SessionDep) -> SignedProofOut:
    """A signed Proof, for a scholarship office to check against the published key."""
    proof = await session.get(Proof, proof_id)
    if proof is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "No such proof")
    return SignedProofOut(payload=proof.payload, signature=proof.signature, key_id=proof.key_id)
