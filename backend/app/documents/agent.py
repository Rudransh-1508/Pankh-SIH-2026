"""The document agent: reads an Uploaded Document, checks it with its issuer, and either issues a
Proof or hands it to a Reviewer.

Like every Agent, it never decides against a Student. A photo it cannot read is not kept and the
Student is told how to take a better one; anything it cannot confirm goes to a person.
"""

import hashlib
import uuid
from dataclasses import dataclass, field
from datetime import UTC, datetime, timedelta
from typing import Any

from sqlalchemy import func, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.academic_year import current_academic_year
from app.config import Settings
from app.documents import crypto
from app.documents.reading import KIND_NAMES, STATES, Kind, Reading, read_document, state_code
from app.documents.storage import ObjectStore
from app.facts.service import FactSource, record_facts
from app.models import (
    AuditEvent,
    Consent,
    Identity,
    Proof,
    Student,
    UploadedDocument,
    VerificationException,
)
from app.sources.http import SourceUnavailable
from app.sources.registers import RegistersClient
from app.verification.names import match_names
from app.verification.service import issue_proof, level_for

# What a photo must start with to be accepted, by the type it claims to be.
_SIGNATURES = {
    "image/jpeg": (b"\xff\xd8\xff",),
    "image/png": (b"\x89PNG\r\n\x1a\n",),
    "application/pdf": (b"%PDF-",),
}

RETAKE_TIPS = (
    "Take the photo again in daylight, with the whole page flat and filling the frame, and "
    "no shadow or glare on the text."
)


class UploadError(Exception):
    """The upload cannot be accepted; the message says what the Student can do."""


@dataclass
class UploadResult:
    reading: Reading
    document: UploadedDocument | None = None
    """None when nothing could be read: the photo is then not kept at all."""
    proofs: list[Proof] = field(default_factory=list)
    exception: VerificationException | None = None
    message: str = ""


def _session_end(academic_year: int) -> datetime:
    return datetime(academic_year + 1, 6, 30, 23, 59, tzinfo=UTC)


def _check_content(data: bytes, content_type: str, max_bytes: int) -> None:
    if not data:
        raise UploadError("The photo is empty. Take it again.")
    if len(data) > max_bytes:
        raise UploadError(
            f"The photo is larger than {max_bytes // (1024 * 1024)} MB. Take it again at a "
            "lower resolution."
        )
    signatures = _SIGNATURES.get(content_type)
    if signatures is None:
        raise UploadError("Upload a JPEG or PNG photo, or a PDF.")
    if not data.startswith(signatures):
        raise UploadError("That file is not the kind of image it says it is.")


class DocumentAgent:
    def __init__(
        self,
        session: AsyncSession,
        settings: Settings,
        registers: RegistersClient,
        store: ObjectStore,
    ) -> None:
        self.session = session
        self.settings = settings
        self.registers = registers
        self.store = store
        self.academic_year = current_academic_year()

    async def upload(
        self, student: Student, kind: Kind, data: bytes, content_type: str, text: str
    ) -> UploadResult:
        _check_content(data, content_type, self.settings.document_max_bytes)
        await self._check_daily_limit(student)
        reading = read_document(kind, text)
        if not reading.readable:
            return UploadResult(reading, message=" ".join([*reading.problems, RETAKE_TIPS]))

        document = UploadedDocument(
            id=uuid.uuid4(),
            student_id=student.id,
            kind=kind.value,
            content_type=content_type,
            size=len(data),
            sha256=hashlib.sha256(data).hexdigest(),
            key_id=crypto.key_id(self.settings),
            fields=reading.fields,
            status="with_reviewer",
            delete_after=_session_end(self.academic_year) + self.settings.document_retention,
        )
        document.object_key = f"students/{student.id}/{document.id}"
        await self.store.put(
            document.object_key, crypto.encrypt(self.settings, str(document.id), data)
        )
        self.session.add(document)
        self.session.add(
            Consent(
                student_id=student.id,
                source="upload",
                scope=KIND_NAMES[kind],
                purpose="Confirm eligibility Facts for Ministry of Tribal Affairs scholarships",
            )
        )
        self.session.add(
            AuditEvent(
                actor_type="student",
                actor_id=student.id,
                action="document.upload",
                subject_type="uploaded_document",
                subject_id=document.id,
                detail={"kind": kind.value},
            )
        )
        await self.session.flush()
        await self._withdraw_earlier(student, kind, document.id)

        result = UploadResult(reading, document)
        identity = await self.session.get(Identity, student.id)
        if kind in (Kind.CASTE_CERTIFICATE, Kind.INCOME_CERTIFICATE):
            await self._check_with_edistrict(student, identity, document, reading, result)
        else:
            await self._to_reviewer(
                student,
                identity,
                document,
                reading,
                result,
                "uploaded_document",
                f"Your {KIND_NAMES[kind]} is with your institute to confirm the percentage.",
                "No action needed from you.",
            )
        await self.session.flush()
        return result

    async def _check_daily_limit(self, student: Student) -> None:
        since = datetime.now(UTC) - timedelta(days=1)
        count = await self.session.scalar(
            select(func.count())
            .select_from(UploadedDocument)
            .where(UploadedDocument.student_id == student.id)
            .where(UploadedDocument.created_at >= since)
        )
        if (count or 0) >= self.settings.document_uploads_per_day:
            raise UploadError("You have uploaded many photos today. Try again tomorrow.")

    async def _withdraw_earlier(self, student: Student, kind: Kind, keep: uuid.UUID) -> None:
        """A new photo of the same kind replaces the one a Reviewer has not yet looked at."""
        earlier = select(UploadedDocument.id).where(
            UploadedDocument.student_id == student.id,
            UploadedDocument.kind == kind.value,
            UploadedDocument.id != keep,
        )
        await self.session.execute(
            update(VerificationException)
            .where(VerificationException.uploaded_document_id.in_(earlier))
            .where(VerificationException.status == "open")
            .values(
                status="withdrawn",
                resolution="Replaced by a newer photo",
                resolved_at=datetime.now(UTC),
            )
        )
        await self.session.execute(
            update(UploadedDocument)
            .where(UploadedDocument.id.in_(earlier))
            .where(UploadedDocument.status == "with_reviewer")
            .values(status="replaced")
        )

    async def _check_with_edistrict(
        self,
        student: Student,
        identity: Identity | None,
        document: UploadedDocument,
        reading: Reading,
        result: UploadResult,
    ) -> None:
        kind = Kind(document.kind)
        name = KIND_NAMES[kind]
        number = reading.fields.get("certificate_number")
        state = state_code(reading.fields.get("state")) or state_code(
            identity.state if identity else None
        )
        record = None
        unreachable = False
        if number and state:
            try:
                record = await self.registers.edistrict_certificate(state, number)
            except SourceUnavailable:
                unreachable = True
        expected_type = (
            "Caste Certificate" if kind is Kind.CASTE_CERTIFICATE else "Income Certificate"
        )

        if record is None or record.get("status") != "VALID" or record.get("type") != expected_type:
            if unreachable:
                why = "The e-District register did not respond"
            elif not number:
                why = "We could not read the certificate number"
            elif not state:
                why = "We could not tell which state issued it"
            else:
                why = (
                    f"It is not in the {STATES[state][0]} e-District register (older paper "
                    "certificates often are not)"
                )
            message = f"{why}, so an officer will check the photo of your {name}."
            await self._to_reviewer(
                student,
                identity,
                document,
                reading,
                result,
                "paper_certificate",
                message,
                "No action needed from you. A certificate issued through e-District can be "
                "confirmed at once, so ask for one when you next renew it.",
            )
            return

        facts: dict[str, Any]
        if kind is Kind.CASTE_CERTIFICATE:
            if record.get("category") != "ST":
                await self._to_reviewer(
                    student,
                    identity,
                    document,
                    reading,
                    result,
                    "not_scheduled_tribe",
                    "The e-District register lists this certificate, but not for a Scheduled "
                    "Tribe.",
                    "An officer will check it. You need an ST certificate for these scholarships.",
                )
                return
            facts = {"is_scheduled_tribe": True}
        else:
            facts = {"family_income": float(record["annual_income"])}
            document.fields = document.fields | {
                "annual_income": float(record["annual_income"]),
                "financial_year": record.get("financial_year"),
            }

        evidence_names: dict[str, Any] = {"name_in_register": record.get("holder_name")}
        if identity is None:
            await self._to_reviewer(
                student,
                identity,
                document,
                reading,
                result,
                "unlinked_identity",
                f"Your {name} is genuine, but we cannot yet check that it is yours.",
                "Link DigiLocker so we can match it with your Aadhaar name, or wait for an "
                "officer to confirm it.",
                facts=facts,
                extra=evidence_names,
            )
            return
        match = match_names(record["holder_name"], identity.name)
        if not match.is_match:
            await self._to_reviewer(
                student,
                identity,
                document,
                reading,
                result,
                "name_mismatch",
                f'The name on your {name} ("{record["holder_name"]}") does not clearly match your '
                f'Aadhaar name ("{identity.name}").',
                "If both are you, no action is needed: an officer will confirm it. If the "
                "certificate has a spelling mistake, ask the issuing office to correct it.",
                facts=facts,
                extra={"name_on_document": record["holder_name"], "name_on_aadhaar": identity.name},
                score=match.score,
            )
            return

        if kind is Kind.INCOME_CERTIFICATE:
            expected = f"{self.academic_year - 1}-{self.academic_year % 100:02d}"
            if record.get("financial_year") != expected:
                await self._to_reviewer(
                    student,
                    identity,
                    document,
                    reading,
                    result,
                    "stale_document",
                    f"Your income certificate is for {record.get('financial_year')}; this year's "
                    f"scholarships need one for {expected}.",
                    "Apply for a new income certificate from your tehsil or e-District portal, "
                    "then photograph it here.",
                    facts=facts,
                )
                return

        expires_at = (
            _session_end(self.academic_year)
            if kind is Kind.INCOME_CERTIFICATE
            else datetime.now(UTC) + self.settings.proof_ttl
        )
        for fact_name, value in facts.items():
            proof = issue_proof(
                self.session,
                self.settings,
                student.id,
                fact_name,
                value,
                source="edistrict",
                issuer=f"e-District {record.get('state') or STATES[state][0]}",
                evidence=f"{state}/{number}",
                match={"name_score": match.score, "uploaded_document": str(document.id)},
                expires_at=expires_at,
                academic_year=self.academic_year,
            )
            await self.session.flush()
            await record_facts(
                self.session, student.id, {fact_name: value}, FactSource.EDISTRICT, proof.id
            )
            result.proofs.append(proof)
        document.status = "verified"
        result.message = (
            f"Your {name} is confirmed with the {STATES[state][0]} e-District register."
        )

    async def _to_reviewer(
        self,
        student: Student,
        identity: Identity | None,
        document: UploadedDocument,
        reading: Reading,
        result: UploadResult,
        kind: str,
        message: str,
        remedy: str,
        *,
        facts: dict[str, Any] | None = None,
        extra: dict[str, Any] | None = None,
        score: float | None = None,
    ) -> None:
        facts = facts or reading.facts
        await record_facts(self.session, student.id, facts, FactSource.UPLOADED)
        evidence: dict[str, Any] = {
            "uploaded_document": str(document.id),
            "document": KIND_NAMES[Kind(document.kind)],
            "read": document.fields,
        }
        holder = reading.fields.get("holder_name")
        if holder and identity is not None:
            evidence |= {"name_on_document": holder, "name_on_aadhaar": identity.name}
        evidence |= extra or {}
        fact_name = next(iter(facts))
        exception = VerificationException(
            state=reading.fields.get("state"),
            district=reading.fields.get("district"),
            student_id=student.id,
            fact_name=fact_name,
            kind=kind,
            message=message,
            remedy=remedy,
            evidence=evidence,
            match_score=score,
            level=level_for(fact_name),
            uploaded_document_id=document.id,
        )
        self.session.add(exception)
        document.status = "with_reviewer"
        result.exception = exception
        result.message = message


async def delete_document(
    session: AsyncSession, store: ObjectStore, document: UploadedDocument, reason: str
) -> None:
    """Delete the photo. The record stays, with its fingerprint, for the audit trail."""
    if document.object_key:
        await store.delete(document.object_key)
    document.object_key = None
    document.status = "deleted"
    document.deleted_at = datetime.now(UTC)
    await session.execute(
        update(VerificationException)
        .where(VerificationException.uploaded_document_id == document.id)
        .where(VerificationException.status == "open")
        .values(status="withdrawn", resolution=reason, resolved_at=datetime.now(UTC))
    )


async def purge_expired(
    session: AsyncSession, store: ObjectStore, now: datetime | None = None
) -> int:
    """Delete every photo past its retention date. Returns how many were deleted."""
    expired = (
        await session.scalars(
            select(UploadedDocument)
            .where(UploadedDocument.delete_after <= (now or datetime.now(UTC)))
            .where(UploadedDocument.object_key.is_not(None))
        )
    ).all()
    for document in expired:
        await delete_document(
            session, store, document, "Deleted at the end of its retention period"
        )
    await session.flush()
    return len(expired)
