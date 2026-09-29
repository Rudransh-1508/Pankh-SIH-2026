"""Confirming Facts with Data Sources, issuing Proofs and raising Exceptions.

Nothing here ever blocks a Student. A Fact that cannot be confirmed is still recorded as
given, and an Exception explains what is wrong, how to fix it, and goes to a Reviewer.
"""

import hashlib
import uuid
from dataclasses import dataclass, field
from datetime import UTC, date, datetime, timedelta
from typing import Any

from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.academic_year import current_academic_year, label
from app.config import Settings
from app.facts.service import FactSource, fact_statuses, record_facts
from app.models import (
    Consent,
    DigiLockerRequest,
    Identity,
    Proof,
    ReferencedDocument,
    Student,
    VerificationException,
)
from app.sources.digilocker import DigiLockerAccount, DigiLockerClient
from app.sources.registers import RegistersClient
from app.verification import proofs
from app.verification.certificates import (
    CertificateError,
    facts_from_certificate,
    parse_certificate,
)
from app.verification.names import match_names
from pankh_rules.engine import format_inr

DIGILOCKER_REQUEST_TTL = timedelta(minutes=15)
READ_DOCTYPES = ("ADHAR", "CSCER", "INCER", "SSCER", "NETSC")


class VerificationError(Exception):
    """The request cannot be carried out; the message says what the Student can do."""


class IdentityRequired(VerificationError):
    def __init__(self) -> None:
        super().__init__("Link DigiLocker first, so we know whose records to check.")


@dataclass
class LinkResult:
    documents: list[ReferencedDocument] = field(default_factory=list)
    proofs: list[Proof] = field(default_factory=list)
    exceptions: list[VerificationException] = field(default_factory=list)


def _session_end(academic_year: int) -> datetime:
    """Proofs that depend on the academic year (like income) last until it ends."""
    return datetime(academic_year + 1, 6, 30, 23, 59, tzinfo=UTC)


class Verifier:
    def __init__(
        self,
        session: AsyncSession,
        settings: Settings,
        digilocker: DigiLockerClient,
        registers: RegistersClient,
    ) -> None:
        self.session = session
        self.settings = settings
        self.digilocker = digilocker
        self.registers = registers
        self.academic_year = current_academic_year()

    # DigiLocker

    async def start_digilocker(self, student: Student) -> str:
        request = self.digilocker.authorisation_request()
        await self.session.execute(
            delete(DigiLockerRequest).where(DigiLockerRequest.student_id == student.id)
        )
        self.session.add(
            DigiLockerRequest(
                state=request.state, student_id=student.id, code_verifier=request.code_verifier
            )
        )
        await self.session.flush()
        return request.url

    async def complete_digilocker(self, student: Student, code: str, state: str) -> LinkResult:
        request = await self.session.get(DigiLockerRequest, state)
        if request is None or request.student_id != student.id:
            raise VerificationError("That DigiLocker sign-in has expired. Start again.")
        await self.session.delete(request)
        if request.created_at < datetime.now(UTC) - DIGILOCKER_REQUEST_TTL:
            raise VerificationError("That DigiLocker sign-in has expired. Start again.")

        account = await self.digilocker.exchange_code(code, request.code_verifier)
        await self._link_identity(student, account)
        self.session.add(
            Consent(
                student_id=student.id,
                source="digilocker",
                scope="issued documents; name, date of birth and gender",
                purpose="Confirm eligibility Facts for Ministry of Tribal Affairs scholarships",
            )
        )
        result = LinkResult()
        for document in await self.digilocker.issued_documents(account.access_token):
            if document.doctype not in READ_DOCTYPES:
                continue
            xml = await self.digilocker.document_xml(account.access_token, document.uri)
            result.documents.append(await self._remember_document(student, document, xml))
            await self._verify_certificate(student, account, document.uri, xml, result)
        await self.session.flush()
        return result

    async def _link_identity(self, student: Student, account: DigiLockerAccount) -> None:
        taken = await self.session.scalar(
            select(Identity.student_id).where(Identity.digilocker_id == account.digilocker_id)
        )
        if taken is not None and taken != student.id:
            raise VerificationError(
                "This DigiLocker account is already linked to another mobile number."
            )
        identity = await self.session.get(Identity, student.id)
        if identity is None:
            identity = Identity(student_id=student.id)
            self.session.add(identity)
        identity.digilocker_id = account.digilocker_id
        identity.name = account.name
        identity.date_of_birth = account.date_of_birth
        identity.gender = account.gender
        identity.reference_key = account.reference_key
        await self.session.flush()

    async def _remember_document(self, student: Student, document, xml: str) -> ReferencedDocument:
        existing = await self.session.scalar(
            select(ReferencedDocument)
            .where(ReferencedDocument.student_id == student.id)
            .where(ReferencedDocument.uri == document.uri)
        )
        record = existing or ReferencedDocument(student_id=student.id, uri=document.uri)
        record.doctype = document.doctype
        record.name = document.name
        record.issuer = document.issuer
        record.sha256 = hashlib.sha256(xml.encode()).hexdigest()
        record.fetched_at = datetime.now(UTC)
        if existing is None:
            self.session.add(record)
        return record

    async def _verify_certificate(
        self, student: Student, account: DigiLockerAccount, uri: str, xml: str, result: LinkResult
    ) -> None:
        try:
            certificate = parse_certificate(xml)
        except CertificateError:
            result.exceptions.append(
                self._exception(
                    student,
                    None,
                    "unreadable_document",
                    f"We could not read the document {uri}.",
                    "No action needed from you. A Reviewer will look at it.",
                    {"uri": uri},
                )
            )
            return
        identity = await self.session.get(Identity, student.id)
        if identity is not None and certificate.holder_state and identity.state is None:
            identity.state = certificate.holder_state
            identity.district = certificate.holder_district
        found = facts_from_certificate(certificate, self.academic_year)
        if not found.facts:
            return
        name_match = match_names(certificate.holder_name, account.name)
        dob_ok = (
            certificate.holder_dob is None
            or account.date_of_birth is None
            or certificate.holder_dob == account.date_of_birth
        )
        evidence = {
            "uri": uri,
            "doctype": certificate.doctype,
            "issuer": certificate.issuer,
            "name_on_document": certificate.holder_name,
            "name_on_aadhaar": account.name,
        }
        problem: tuple[str, str, str] | None = None
        if not name_match.is_match:
            problem = (
                "name_mismatch",
                f"The name on your {_document_name(certificate.doctype)} "
                f'("{certificate.holder_name}") does not clearly match your Aadhaar name '
                f'("{account.name}").',
                "If both are you, no action is needed: a Reviewer will confirm it. If the "
                "certificate has a spelling mistake, ask the issuing office to correct it.",
            )
        elif not dob_ok:
            problem = (
                "dob_mismatch",
                f"The date of birth on your {_document_name(certificate.doctype)} does not match "
                "your Aadhaar.",
                "A Reviewer will check which is correct. You may need a corrected certificate.",
            )
        elif found.stale_reason:
            problem = (
                "stale_document",
                found.stale_reason,
                "Apply for a new income certificate from your tehsil or e-District portal. "
                "It will appear in DigiLocker when issued.",
            )

        if problem:
            await record_facts(self.session, student.id, found.facts, FactSource.DIGILOCKER)
            for fact_name in found.facts:
                result.exceptions.append(
                    self._exception(student, fact_name, *problem, evidence, score=name_match.score)
                )
            return

        expires_at = (
            _session_end(self.academic_year)
            if certificate.doctype == "INCER"
            else datetime.now(UTC) + self.settings.proof_ttl
        )
        await self._flag_conflicts(student, found.facts, evidence)
        for fact_name, value in found.facts.items():
            proof = self._proof(
                student,
                fact_name,
                value,
                source=f"digilocker:{certificate.doctype}",
                issuer=certificate.issuer,
                evidence=uri,
                match={"name_score": name_match.score, "date_of_birth_matches": dob_ok},
                expires_at=expires_at,
            )
            result.proofs.append(proof)
            await self.session.flush()
            await record_facts(
                self.session, student.id, {fact_name: value}, FactSource.DIGILOCKER, proof.id
            )

    async def _flag_conflicts(
        self, student: Student, confirmed: dict[str, Any], evidence: dict[str, Any]
    ) -> None:
        """Note where a document disagrees with what the Student said. The document is used."""
        statuses = await fact_statuses(self.session, student.id)
        for fact_name, value in confirmed.items():
            given = statuses.get(fact_name)
            stored = value.isoformat() if isinstance(value, date) else value
            if given is None or given.verified or given.value == stored:
                continue
            self._exception(
                student,
                fact_name,
                "value_conflict",
                f"You told us {_display(fact_name, given.value)}, but your "
                f"{_document_name(evidence['doctype'])} says {_display(fact_name, stored)}. "
                "We are using the certificate.",
                "If the certificate is wrong, ask the issuing office to correct it.",
                evidence | {"given": given.value, "confirmed": stored},
                status="resolved",
            )

    # Registers

    async def verify_institution(self, student: Student, code: str) -> list[Proof]:
        code = code.strip().upper()
        record = await self.registers.aishe_institution(code)
        source, source_name = FactSource.AISHE, "aishe"
        if record is None:
            record = await self.registers.udise_school(code)
            source, source_name = FactSource.UDISE, "udise"
        if record is None:
            raise VerificationError(
                "No school or college has that code. Check the U-DISE or AISHE code with your "
                "institution."
            )
        facts: dict[str, Any] = {"institution_recognised": bool(record["recognised"])}
        if "ugc_2f_12b" in record:
            facts["institution_eligible_for_fellowship"] = bool(record["ugc_2f_12b"])
        issued = []
        for fact_name, value in facts.items():
            proof = self._proof(
                student,
                fact_name,
                value,
                source=source_name,
                issuer=record["name"],
                evidence=code,
                match={},
                expires_at=_session_end(self.academic_year),
            )
            await self.session.flush()
            await record_facts(self.session, student.id, {fact_name: value}, source, proof.id)
            issued.append(proof)
        return issued

    async def verify_net(self, student: Student, roll_number: str) -> list[Proof]:
        identity = await self._identity(student)
        result = await self.registers.net_result(roll_number.strip().upper())
        if result is None:
            raise VerificationError("No UGC NET result has that roll number.")
        name_match = match_names(result["candidate_name"], identity.name)
        evidence = {"roll_number": roll_number, "name_on_result": result["candidate_name"]}
        if not name_match.is_match:
            self._exception(
                student,
                "net_jrf_qualified",
                "name_mismatch",
                f'The name on that NET result ("{result["candidate_name"]}") does not clearly '
                f'match your Aadhaar name ("{identity.name}").',
                "Check the roll number. If it is yours, a Reviewer will confirm it.",
                evidence,
                score=name_match.score,
            )
            return []
        proof = self._proof(
            student,
            "net_jrf_qualified",
            bool(result["qualified"]),
            source="nta",
            issuer="National Testing Agency",
            evidence=roll_number,
            match={"name_score": name_match.score},
            expires_at=datetime.now(UTC) + self.settings.proof_ttl,
        )
        await self.session.flush()
        await record_facts(
            self.session,
            student.id,
            {"net_jrf_qualified": bool(result["qualified"])},
            FactSource.NTA,
            proof.id,
        )
        return [proof]

    async def verify_bank_seeding(self, student: Student) -> list[Proof]:
        identity = await self._identity(student)
        result = await self.registers.aadhaar_seeding(identity.reference_key)
        if result is None:
            raise VerificationError("The bank account register has no record for you yet.")
        seeded = bool(result["seeded"])
        proof = self._proof(
            student,
            "has_aadhaar_seeded_bank_account",
            seeded,
            source="npci",
            issuer="NPCI Aadhaar mapper",
            evidence=result.get("bank") or "none",
            match={},
            expires_at=datetime.now(UTC) + timedelta(days=90),
        )
        await self.session.flush()
        await record_facts(
            self.session,
            student.id,
            {"has_aadhaar_seeded_bank_account": seeded},
            FactSource.NPCI,
            proof.id,
        )
        return [proof]

    async def _identity(self, student: Student) -> Identity:
        identity = await self.session.get(Identity, student.id)
        if identity is None:
            raise IdentityRequired()
        return identity

    # Building blocks

    def _proof(
        self,
        student: Student,
        fact_name: str,
        value: Any,
        *,
        source: str,
        issuer: str,
        evidence: str,
        match: dict[str, Any],
        expires_at: datetime,
    ) -> Proof:
        return issue_proof(
            self.session,
            self.settings,
            student.id,
            fact_name,
            value,
            source=source,
            issuer=issuer,
            evidence=evidence,
            match=match,
            expires_at=expires_at,
            academic_year=self.academic_year,
        )

    def _exception(
        self,
        student: Student,
        fact_name: str | None,
        kind: str,
        message: str,
        remedy: str | None,
        evidence: dict[str, Any],
        score: float | None = None,
        status: str = "open",
    ) -> VerificationException:
        exception = VerificationException(
            student_id=student.id,
            fact_name=fact_name,
            kind=kind,
            message=message,
            remedy=remedy,
            evidence=evidence,
            match_score=score,
            status=status,
            level=level_for(fact_name),
        )
        self.session.add(exception)
        return exception


def level_for(fact_name: str | None) -> str:
    """Caste, income and identity certificates are issued by district offices, so their
    District verifies them; academic and institutional Facts go to the institute."""
    if fact_name in (
        "net_jrf_qualified",
        "institution_recognised",
        "institution_eligible_for_fellowship",
        "bachelors_marks_percent",
        "masters_marks_percent",
    ):
        return "institute"
    return "district"


def issue_proof(
    session: AsyncSession,
    settings: Settings,
    student_id: uuid.UUID,
    fact_name: str,
    value: Any,
    *,
    source: str,
    issuer: str,
    evidence: str,
    match: dict[str, Any],
    expires_at: datetime,
    academic_year: int,
) -> Proof:
    """Sign and store a Proof that a Fact was confirmed by `source`."""
    now = datetime.now(UTC).replace(microsecond=0)
    proof_id = uuid.uuid4()
    payload = {
        "id": str(proof_id),
        "subject": str(student_id),
        "fact": fact_name,
        "value": value.isoformat() if isinstance(value, date) else value,
        "source": source,
        "issuer": issuer,
        "evidence": evidence,
        "match": match,
        "academic_year": label(academic_year),
        "issued_at": now.isoformat(),
        "expires_at": expires_at.replace(microsecond=0).isoformat(),
        "key_id": proofs.key_id(settings),
    }
    proof = Proof(
        id=proof_id,
        student_id=student_id,
        fact_name=fact_name,
        payload=payload,
        signature=proofs.sign(settings, payload),
        key_id=payload["key_id"],
        issued_at=now,
        expires_at=expires_at,
    )
    session.add(proof)
    return proof


_DOCUMENT_NAMES = {
    "ADHAR": "Aadhaar",
    "CSCER": "caste certificate",
    "INCER": "income certificate",
    "SSCER": "Class X marksheet",
    "NETSC": "NET scorecard",
}


def _document_name(doctype: str) -> str:
    return _DOCUMENT_NAMES.get(doctype, "document")


def _display(fact_name: str, value: Any) -> str:
    if fact_name == "family_income" and isinstance(value, int | float):
        return format_inr(value)
    if isinstance(value, bool):
        return "yes" if value else "no"
    return str(value)
