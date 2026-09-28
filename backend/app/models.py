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
