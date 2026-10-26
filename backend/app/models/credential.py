"""Credential, Verification, Consent, Alert, and Webhook entities."""

from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
import uuid
from sqlalchemy import Boolean, DateTime, ForeignKey, Index, Integer, String, Text
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base


class ConsentRequest(Base):
    __tablename__ = "consent_requests"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    student_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("students.id", ondelete="CASCADE"), nullable=False, index=True
    )
    verifier_id: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    verifier_org_name: Mapped[str] = mapped_column(String(255), nullable=False, default="Authorized Verifier")
    purpose: Mapped[str] = mapped_column(String(255), nullable=False)
    purpose_category: Mapped[str] = mapped_column(
        String(50), nullable=False, default="EMPLOYMENT"
    )  # EMPLOYMENT, HIGHER_EDUCATION, SCHOLARSHIP, VISA, GENERAL
    fields_requested: Mapped[List[str]] = mapped_column(JSONB, default=list, nullable=False)
    approved_fields: Mapped[List[str]] = mapped_column(JSONB, default=list, nullable=False)
    retention_days: Mapped[int] = mapped_column(Integer, default=30, nullable=False)
    status: Mapped[str] = mapped_column(
        String(30), nullable=False, default="PENDING", index=True
    )  # PENDING, APPROVED, DENIED, REVOKED, EXPIRED
    token: Mapped[str] = mapped_column(String(128), unique=True, index=True, nullable=False)
    otp_hash: Mapped[Optional[str]] = mapped_column(String(128), nullable=True)
    receipt_signature: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    approved_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    revoked_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False
    )

    student = relationship("Student", back_populates="consent_requests")


class VerificationLog(Base):
    __tablename__ = "verification_logs"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    enrolment_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True), ForeignKey("enrolments.id", ondelete="SET NULL"), nullable=True, index=True
    )
    verifier_id: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    apaar_id: Mapped[str] = mapped_column(String(12), nullable=False, index=True)
    result: Mapped[str] = mapped_column(String(30), nullable=False)  # SUCCESS, FAILED
    details: Mapped[Dict[str, Any]] = mapped_column(JSONB, default=dict, nullable=False)
    ip: Mapped[str] = mapped_column(String(50), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False, index=True
    )


class IssuedRecord(Base):
    __tablename__ = "issued_records"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    enrolment_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("enrolments.id", ondelete="CASCADE"), nullable=False, index=True
    )
    token: Mapped[str] = mapped_column(String(128), unique=True, index=True, nullable=False)
    kid: Mapped[str] = mapped_column(String(64), nullable=False)  # Key identifier for verification signature
    payload: Mapped[Dict[str, Any]] = mapped_column(JSONB, nullable=False)
    signature: Mapped[str] = mapped_column(Text, nullable=False)
    status: Mapped[str] = mapped_column(
        String(30), nullable=False, default="VALID", index=True
    )  # VALID, REVOKED, SUPERSEDED, EXPIRED
    issued_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False
    )
    expires_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    revoked_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    revoke_reason: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    revoked_by: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)

    enrolment = relationship("Enrolment", back_populates="issued_records")


class VerifierOrg(Base):
    __tablename__ = "verifier_orgs"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    org_name: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    cin_gstin: Mapped[str] = mapped_column(String(50), unique=True, nullable=False)
    contact_email: Mapped[str] = mapped_column(String(255), unique=True, nullable=False)
    purpose_categories: Mapped[List[str]] = mapped_column(JSONB, default=list, nullable=False)
    status: Mapped[str] = mapped_column(
        String(30), nullable=False, default="APPROVED", index=True
    )  # PENDING_APPROVAL, APPROVED, REJECTED, SUSPENDED
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False
    )


class RegulatoryAccessLog(Base):
    __tablename__ = "regulatory_access_logs"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    student_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("students.id", ondelete="CASCADE"), nullable=False, index=True
    )
    actor_id: Mapped[str] = mapped_column(String(100), nullable=False)
    actor_name: Mapped[str] = mapped_column(String(150), nullable=False)
    agency_name: Mapped[str] = mapped_column(String(255), nullable=False)
    legal_basis: Mapped[str] = mapped_column(String(150), nullable=False)
    reference_number: Mapped[str] = mapped_column(String(100), nullable=False)
    justification: Mapped[str] = mapped_column(Text, nullable=False)
    accessed_fields: Mapped[List[str]] = mapped_column(JSONB, default=list, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False, index=True
    )


class CertificateTemplate(Base):
    __tablename__ = "certificate_templates"

    id: Mapped[str] = mapped_column(String(50), primary_key=True)  # e.g., "aicte_classic", "tech_modern", "honors_minimal"
    name: Mapped[str] = mapped_column(String(150), nullable=False)
    description: Mapped[str] = mapped_column(String(255), nullable=False)
    orientation: Mapped[str] = mapped_column(String(20), default="LANDSCAPE", nullable=False)  # LANDSCAPE, PORTRAIT
    layout_spec: Mapped[Dict[str, Any]] = mapped_column(JSONB, nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False
    )


class Alert(Base):
    __tablename__ = "alerts"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    type: Mapped[str] = mapped_column(String(50), nullable=False, index=True)
    severity: Mapped[str] = mapped_column(String(20), nullable=False, index=True)
    institution_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True), ForeignKey("institutions.id", ondelete="CASCADE"), nullable=True, index=True
    )
    message: Mapped[str] = mapped_column(Text, nullable=False)
    status: Mapped[str] = mapped_column(
        String(30), nullable=False, default="NEW", index=True
    )  # NEW, ASSIGNED, RESOLVED
    assigned_to: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False, index=True
    )


class WebhookSubscription(Base):
    __tablename__ = "webhook_subscriptions"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    institution_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("institutions.id", ondelete="CASCADE"), nullable=False, index=True
    )
    url: Mapped[str] = mapped_column(String(500), nullable=False)
    events: Mapped[List[str]] = mapped_column(JSONB, default=list, nullable=False)
    secret_enc: Mapped[str] = mapped_column(Text, nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False
    )
