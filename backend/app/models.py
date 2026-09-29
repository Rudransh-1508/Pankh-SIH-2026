import uuid
from datetime import date, datetime
from typing import Any

from sqlalchemy import JSON, Date, DateTime, Float, ForeignKey, Index, Integer, String, Text, func
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.db import Base, CreatedAt


class Student(CreatedAt, Base):
    __tablename__ = "students"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    phone: Mapped[str] = mapped_column(String(16), unique=True, nullable=False)


class OtpChallenge(CreatedAt, Base):
    """A one-time code sent to a phone number. Only a keyed hash of the code is stored."""

    __tablename__ = "otp_challenges"
    __table_args__ = (Index("ix_otp_challenges_phone_created_at", "phone", "created_at"),)

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    phone: Mapped[str] = mapped_column(String(16), nullable=False)
    code_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    attempts: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    consumed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class RefreshToken(CreatedAt, Base):
    """A long-lived sign-in session. Tokens rotate on every use; only their hash is stored."""

    __tablename__ = "refresh_tokens"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    student_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("students.id", ondelete="CASCADE"), index=True, nullable=False
    )
    token_hash: Mapped[str] = mapped_column(String(64), unique=True, nullable=False)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    used_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    revoked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class FactRecord(Base):
    """One recorded value of one Fact about a Student. The newest record for a Fact wins.

    Records are never updated or deleted, so the history of what was known, and from where,
    is kept. A null value records that the Fact was withdrawn.
    """

    __tablename__ = "fact_records"
    __table_args__ = (
        Index("ix_fact_records_student_name_recorded", "student_id", "name", "recorded_at"),
    )

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    student_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("students.id", ondelete="CASCADE"), nullable=False
    )
    name: Mapped[str] = mapped_column(String(64), nullable=False)
    value: Mapped[Any | None] = mapped_column(
        JSON(none_as_null=True).with_variant(JSONB(none_as_null=True), "postgresql"), nullable=True
    )
    source: Mapped[str] = mapped_column(String(32), nullable=False)
    proof_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("proofs.id", ondelete="SET NULL"))
    recorded_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )


def _json():
    return JSON(none_as_null=True).with_variant(JSONB(none_as_null=True), "postgresql")


class Identity(Base):
    """Who a Student is, as confirmed by DigiLocker (from their Aadhaar record)."""

    __tablename__ = "identities"

    student_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("students.id", ondelete="CASCADE"), primary_key=True
    )
    digilocker_id: Mapped[str] = mapped_column(String(64), unique=True, nullable=False)
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    date_of_birth: Mapped[date | None] = mapped_column(Date)
    gender: Mapped[str | None] = mapped_column(String(8))
    reference_key: Mapped[str] = mapped_column(String(128), nullable=False)
    """DigiLocker's reference for the Aadhaar record. The Aadhaar number itself is never held."""
    state: Mapped[str | None] = mapped_column(String(64), index=True)
    district: Mapped[str | None] = mapped_column(String(64), index=True)
    linked_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )


class DigiLockerRequest(CreatedAt, Base):
    """An authorisation started on the phone, waiting for DigiLocker to send the Student back."""

    __tablename__ = "digilocker_requests"

    state: Mapped[str] = mapped_column(String(64), primary_key=True)
    student_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("students.id", ondelete="CASCADE"), nullable=False
    )
    code_verifier: Mapped[str] = mapped_column(String(128), nullable=False)


class ReferencedDocument(Base):
    """A Document held by DigiLocker. Only its reference and a fingerprint are kept."""

    __tablename__ = "referenced_documents"
    __table_args__ = (
        Index("uq_referenced_documents_student_uri", "student_id", "uri", unique=True),
    )

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    student_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("students.id", ondelete="CASCADE"), nullable=False
    )
    uri: Mapped[str] = mapped_column(String(255), nullable=False)
    doctype: Mapped[str] = mapped_column(String(16), nullable=False)
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    issuer: Mapped[str] = mapped_column(String(200), nullable=False)
    sha256: Mapped[str] = mapped_column(String(64), nullable=False)
    fetched_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


class Proof(Base):
    """A signed record that a Fact was confirmed by a named source at a stated time."""

    __tablename__ = "proofs"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    student_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("students.id", ondelete="CASCADE"), index=True, nullable=False
    )
    fact_name: Mapped[str] = mapped_column(String(64), nullable=False)
    payload: Mapped[dict[str, Any]] = mapped_column(_json(), nullable=False)
    signature: Mapped[str] = mapped_column(String(128), nullable=False)
    key_id: Mapped[str] = mapped_column(String(32), nullable=False)
    issued_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


class VerificationException(CreatedAt, Base):
    """A Fact that could not be confirmed, sent to a Reviewer instead of blocking anything."""

    __tablename__ = "verification_exceptions"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    student_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("students.id", ondelete="CASCADE"), index=True, nullable=False
    )
    fact_name: Mapped[str | None] = mapped_column(String(64))
    kind: Mapped[str] = mapped_column(String(32), nullable=False)
    message: Mapped[str] = mapped_column(Text, nullable=False)
    remedy: Mapped[str | None] = mapped_column(Text)
    evidence: Mapped[dict[str, Any]] = mapped_column(_json(), nullable=False, default=dict)
    match_score: Mapped[float | None] = mapped_column(Float)
    level: Mapped[str] = mapped_column(String(16), nullable=False, default="institute")
    status: Mapped[str] = mapped_column(String(16), nullable=False, default="open", index=True)
    resolved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    resolution: Mapped[str | None] = mapped_column(Text)
    state: Mapped[str | None] = mapped_column(String(64))
    district: Mapped[str | None] = mapped_column(String(64))
    """Where the Student lives, when it is known from a Document but not from their Identity."""
    uploaded_document_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("uploaded_documents.id", ondelete="SET NULL"), index=True
    )


class UploadedDocument(CreatedAt, Base):
    """A Document the Student photographed. The photo is encrypted in object storage; only the
    fields read from it are kept here, never its full text."""

    __tablename__ = "uploaded_documents"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    student_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("students.id", ondelete="CASCADE"), index=True, nullable=False
    )
    kind: Mapped[str] = mapped_column(String(32), nullable=False)
    content_type: Mapped[str] = mapped_column(String(64), nullable=False)
    size: Mapped[int] = mapped_column(Integer, nullable=False)
    sha256: Mapped[str] = mapped_column(String(64), nullable=False)
    object_key: Mapped[str | None] = mapped_column(String(200))
    """Where the encrypted photo is stored; None once it has been deleted."""
    key_id: Mapped[str] = mapped_column(String(32), nullable=False)
    fields: Mapped[dict[str, Any]] = mapped_column(_json(), nullable=False, default=dict)
    status: Mapped[str] = mapped_column(
        String(16), nullable=False
    )  # verified | with_reviewer | accepted | rejected | deleted
    delete_after: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), index=True, nullable=False
    )
    deleted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class Consent(Base):
    """A Student's recorded permission for one pull of Facts or one action on their behalf."""

    __tablename__ = "consents"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    student_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("students.id", ondelete="CASCADE"), index=True, nullable=False
    )
    source: Mapped[str] = mapped_column(String(32), nullable=False)
    scope: Mapped[str] = mapped_column(String(200), nullable=False)
    purpose: Mapped[str] = mapped_column(Text, nullable=False)
    granted_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    withdrawn_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class ApplicationSnapshot(Base):
    """The latest record of an Application from its system of record.

    Kept so the Student sees their applications when a system of record is down, and so
    stages can be counted across Students to see where applications stall.
    """

    __tablename__ = "application_snapshots"
    __table_args__ = (
        Index(
            "uq_application_snapshots_student_source_external",
            "student_id",
            "source_system",
            "external_id",
            unique=True,
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    student_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("students.id", ondelete="CASCADE"), nullable=False
    )
    source_system: Mapped[str] = mapped_column(String(16), nullable=False)
    external_id: Mapped[str] = mapped_column(String(64), nullable=False)
    scheme_id: Mapped[str] = mapped_column(String(32), nullable=False)
    stage: Mapped[str] = mapped_column(String(32), nullable=False, index=True)
    waiting_on: Mapped[str | None] = mapped_column(String(32))
    since: Mapped[date | None] = mapped_column(Date)
    record: Mapped[dict[str, Any]] = mapped_column(_json(), nullable=False)
    fetched_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


class Official(CreatedAt, Base):
    """A Reviewer or ministry user, working at one Verification Level within a jurisdiction."""

    __tablename__ = "officials"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    phone: Mapped[str] = mapped_column(String(16), unique=True, nullable=False)
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    level: Mapped[str] = mapped_column(
        String(16), nullable=False
    )  # institute | district | state | ministry
    state: Mapped[str | None] = mapped_column(String(64))
    district: Mapped[str | None] = mapped_column(String(64))


class AuditEvent(Base):
    """Something an official or an Agent did, and on what. Never updated or deleted."""

    __tablename__ = "audit_events"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    actor_type: Mapped[str] = mapped_column(String(16), nullable=False)
    actor_id: Mapped[uuid.UUID] = mapped_column(nullable=False, index=True)
    action: Mapped[str] = mapped_column(String(48), nullable=False)
    subject_type: Mapped[str] = mapped_column(String(32), nullable=False)
    subject_id: Mapped[uuid.UUID] = mapped_column(nullable=False, index=True)
    detail: Mapped[dict[str, Any]] = mapped_column(_json(), nullable=False, default=dict)
    at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )


class CoverageRun(CreatedAt, Base):
    """One linkage of education registers against scholarship registrations."""

    __tablename__ = "coverage_runs"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    summary: Mapped[dict[str, Any]] = mapped_column(_json(), nullable=False)
    unreached: Mapped[list[dict[str, Any]]] = mapped_column(_json(), nullable=False)


class JagoMessage(Base):
    """One turn of a Student's conversation with JAGO, with the tools it used to answer."""

    __tablename__ = "jago_messages"
    __table_args__ = (Index("ix_jago_messages_student_created", "student_id", "created_at"),)

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    student_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("students.id", ondelete="CASCADE"), nullable=False
    )
    role: Mapped[str] = mapped_column(String(16), nullable=False)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    language: Mapped[str] = mapped_column(String(8), nullable=False)
    meta: Mapped[dict[str, Any]] = mapped_column(_json(), nullable=False, default=dict)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.clock_timestamp(), nullable=False
    )


class Nudge(CreatedAt, Base):
    """A reminder an Agent sends, or proposes, to a Student or an office.

    Nudges to a Student about their own case go out at once. Nudges to an office are proposed,
    and go out only when an official approves them.
    """

    __tablename__ = "nudges"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    student_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("students.id", ondelete="CASCADE"), index=True, nullable=False
    )
    audience: Mapped[str] = mapped_column(String(16), nullable=False)  # student | office
    kind: Mapped[str] = mapped_column(String(32), nullable=False)
    message: Mapped[str] = mapped_column(Text, nullable=False)
    level: Mapped[str | None] = mapped_column(String(16))
    state: Mapped[str | None] = mapped_column(String(64))
    district: Mapped[str | None] = mapped_column(String(64))
    status: Mapped[str] = mapped_column(
        String(16), nullable=False, index=True
    )  # proposed | sent | dismissed
    dedupe_key: Mapped[str] = mapped_column(String(200), unique=True, nullable=False)
    decided_by: Mapped[uuid.UUID | None] = mapped_column()
    sent_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class FamilyInvite(CreatedAt, Base):
    """A short-lived code a Student gives a Guardian to let them follow the Student's progress."""

    __tablename__ = "family_invites"

    code_hash: Mapped[str] = mapped_column(String(64), primary_key=True)
    student_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("students.id", ondelete="CASCADE"), nullable=False
    )
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


class GuardianLink(CreatedAt, Base):
    """A Guardian following a Student, with the Student's consent. Either can end it."""

    __tablename__ = "guardian_links"
    __table_args__ = (Index("uq_guardian_links_pair", "guardian_id", "student_id", unique=True),)

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    guardian_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("students.id", ondelete="CASCADE"), index=True, nullable=False
    )
    student_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("students.id", ondelete="CASCADE"), index=True, nullable=False
    )
    ended_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class Campaign(CreatedAt, Base):
    """An outreach campaign to Unreached Students in one state or district, from one coverage run.

    Drafted by an official, who sees every message before approving it; nothing is sent before.
    """

    __tablename__ = "campaigns"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    created_by: Mapped[uuid.UUID] = mapped_column(ForeignKey("officials.id"), nullable=False)
    coverage_run_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("coverage_runs.id", ondelete="CASCADE"), nullable=False
    )
    state: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    district: Mapped[str | None] = mapped_column(String(64))
    channel: Mapped[str] = mapped_column(String(16), nullable=False)  # school | family
    language: Mapped[str] = mapped_column(String(8), nullable=False)
    status: Mapped[str] = mapped_column(String(16), nullable=False)  # draft | sent | cancelled
    approved_by: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("officials.id"))
    sent_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class CampaignTarget(Base):
    """One Unreached Student in a campaign, and whether the message about them was delivered."""

    __tablename__ = "campaign_targets"
    __table_args__ = (
        Index("uq_campaign_targets_student", "campaign_id", "student_ref", unique=True),
    )

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    campaign_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("campaigns.id", ondelete="CASCADE"), index=True, nullable=False
    )
    student_ref: Mapped[str] = mapped_column(String(64), nullable=False)
    udise_code: Mapped[str] = mapped_column(String(32), nullable=False)
    district: Mapped[str] = mapped_column(String(64), nullable=False)
    status: Mapped[str] = mapped_column(
        String(16), nullable=False
    )  # pending | sent | no_contact | failed
    sent_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class OutreachLink(Base):
    """A short code for one school's list in one campaign, so the message stays one SMS long."""

    __tablename__ = "outreach_links"

    code: Mapped[str] = mapped_column(String(16), primary_key=True)
    campaign_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("campaigns.id", ondelete="CASCADE"), index=True, nullable=False
    )
    udise_code: Mapped[str] = mapped_column(String(32), nullable=False)


class Grievance(CreatedAt, Base):
    """A grievance filed on CPGRAMS for the Student, with their approval, and its progress."""

    __tablename__ = "grievances"
    __table_args__ = (Index("uq_grievances_subject", "student_id", "subject_key", unique=True),)

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    student_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("students.id", ondelete="CASCADE"), index=True, nullable=False
    )
    subject_key: Mapped[str] = mapped_column(String(200), nullable=False)
    """What the grievance is about, so the same problem is never filed twice."""
    kind: Mapped[str] = mapped_column(String(32), nullable=False)
    registration_number: Mapped[str] = mapped_column(String(40), unique=True, nullable=False)
    subject: Mapped[str] = mapped_column(String(200), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    status: Mapped[str] = mapped_column(String(32), nullable=False)
    reply: Mapped[str | None] = mapped_column(Text)
    closed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    checked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class PhoneCall(CreatedAt, Base):
    """A call to the phone line, and where in the menu the caller is."""

    __tablename__ = "phone_calls"

    call_sid: Mapped[str] = mapped_column(String(64), primary_key=True)
    phone: Mapped[str] = mapped_column(String(16), nullable=False)
    student_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("students.id", ondelete="SET NULL"), index=True
    )
    language: Mapped[str | None] = mapped_column(String(8))
    stage: Mapped[str] = mapped_column(
        String(16), nullable=False
    )  # placed | language | menu | ended
    keys: Mapped[list[str]] = mapped_column(_json(), nullable=False, default=list)
    direction: Mapped[str] = mapped_column(
        String(8), nullable=False, default="inbound", server_default="inbound"
    )
    topic: Mapped[str | None] = mapped_column(String(16))
    """For a call Pankh places: what it is about (payments, applications or documents)."""


class RuleDraft(CreatedAt, Base):
    """A figure found in a new Guideline, set against the Parameter it would change.

    Drafts change nothing: an approved draft yields the new Parameter file, which is reviewed
    and tested like any other code before it takes effect.
    """

    __tablename__ = "rule_drafts"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    created_by: Mapped[uuid.UUID] = mapped_column(ForeignKey("officials.id"), nullable=False)
    scheme_id: Mapped[str] = mapped_column(String(32), nullable=False)
    parameter: Mapped[str] = mapped_column(String(100), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    unit: Mapped[str] = mapped_column(String(32), nullable=False)
    current_value: Mapped[float] = mapped_column(Float, nullable=False)
    found_value: Mapped[float] = mapped_column(Float, nullable=False)
    source_title: Mapped[str] = mapped_column(String(200), nullable=False)
    source_sha256: Mapped[str] = mapped_column(String(64), nullable=False)
    page: Mapped[int] = mapped_column(Integer, nullable=False)
    excerpt: Mapped[str] = mapped_column(Text, nullable=False)
    status: Mapped[str] = mapped_column(
        String(16), nullable=False, index=True
    )  # proposed | matches | approved | rejected
    effective_from: Mapped[date | None] = mapped_column(Date)
    decided_by: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("officials.id"))
    note: Mapped[str | None] = mapped_column(Text)
    patch: Mapped[str | None] = mapped_column(Text)
