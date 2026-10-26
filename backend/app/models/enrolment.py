"""Enrolment and EnrolmentHistory entities."""

from datetime import date, datetime, timezone
from typing import Any, Dict, List, Optional
import uuid
from sqlalchemy import (
    Boolean,
    Date,
    DateTime,
    Float,
    ForeignKey,
    Index,
    String,
    UniqueConstraint,
)
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.crypto import EncryptedJSON
from app.models.base import Base, SoftDeleteMixin, TimestampMixin


class Enrolment(Base, TimestampMixin, SoftDeleteMixin):
    __tablename__ = "enrolments"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    student_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("students.id", ondelete="CASCADE"), nullable=False, index=True
    )
    program_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("programs.id", ondelete="CASCADE"), nullable=False, index=True
    )
    institution_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("institutions.id", ondelete="CASCADE"), nullable=False, index=True
    )
    academic_year: Mapped[str] = mapped_column(String(20), nullable=False, index=True)
    student_ref_id: Mapped[str] = mapped_column(String(100), nullable=False)  # College roll number

    # Categorization and quotas
    admission_category: Mapped[str] = mapped_column(
        String(30), nullable=False, default="GEN"
    )  # GEN, EWS, OBC, SC, ST, PWD, OTHER
    quota_type: Mapped[str] = mapped_column(
        String(30), nullable=False, default="REGULAR"
    )  # REGULAR, SUPERNUMERARY, NRI, OCI, FN, TFW, OTHER

    is_nri: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    oci_status: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    is_foreign_national: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    nationality: Mapped[str] = mapped_column(String(100), default="INDIAN", nullable=False)

    sponsor_details_enc: Mapped[Optional[Dict[str, Any]]] = mapped_column(EncryptedJSON, nullable=True)
    admission_date: Mapped[date] = mapped_column(Date, nullable=False)
    status: Mapped[str] = mapped_column(
        String(30), nullable=False, default="ACTIVE"
    )  # ACTIVE, WITHDRAWN, COMPLETED
    validation_status: Mapped[str] = mapped_column(
        String(30), nullable=False, default="PENDING"
    )  # PENDING, CLEAN, WARNING, ERROR
    risk_score: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)

    source_batch_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True), ForeignKey("upload_batches.id", ondelete="SET NULL"), nullable=True, index=True
    )

    # Relationships
    student = relationship("Student", back_populates="enrolments")
    program = relationship("Program", back_populates="enrolments")
    institution = relationship("Institution", back_populates="enrolments")
    upload_batch = relationship("UploadBatch", back_populates="enrolments")
    validation_issues = relationship("ValidationIssue", back_populates="enrolment", cascade="all, delete-orphan")
    issued_records = relationship("IssuedRecord", back_populates="enrolment", cascade="all, delete-orphan")
    history_entries = relationship("EnrolmentHistory", back_populates="enrolment", cascade="all, delete-orphan")

    __table_args__ = (
        # Uniqueness strictly scoped per-institution & per-program:
        # Cross-institution duplicates are left unblocked so they can be stored and flagged by the rule engine!
        UniqueConstraint(
            "student_id", "institution_id", "program_id", "academic_year",
            name="uq_enrolments_student_inst_prog_ay"
        ),
        # Composite Indexes requested in Section B:
        Index("ix_enrolments_inst_ay", "institution_id", "academic_year"),
        Index("ix_enrolments_ay_status", "academic_year", "status"),
    )


class EnrolmentHistory(Base):
    __tablename__ = "enrolment_history"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    enrolment_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("enrolments.id", ondelete="CASCADE"), nullable=False, index=True
    )
    changed_by: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True), nullable=True
    )
    action: Mapped[str] = mapped_column(String(50), nullable=False)  # CREATE, UPDATE, STATUS_CHANGE
    diff: Mapped[Optional[Dict[str, Any]]] = mapped_column(JSONB, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
        index=True,
    )

    enrolment = relationship("Enrolment", back_populates="history_entries")
