"""Student entity with field-level encryption, blind indexes, and APAAR verification status."""

from datetime import date
from typing import Any, Dict, List, Optional
import uuid
from sqlalchemy import CheckConstraint, Date, Index, String
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.crypto import EncryptedDate, EncryptedJSON, EncryptedString
from app.models.base import Base, SoftDeleteMixin, TimestampMixin


class Student(Base, TimestampMixin, SoftDeleteMixin):
    __tablename__ = "students"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    # Stored plaintext-indexable since it is the unique identifier, but masked on API serialization
    apaar_id: Mapped[Optional[str]] = mapped_column(
        String(12), nullable=True, index=True
    )
    apaar_status: Mapped[str] = mapped_column(
        String(30), nullable=False, default="UNVERIFIED", index=True
    )  # UNVERIFIED, VERIFIED, NOT_FOUND, MISMATCH, PENDING

    # Encrypted PII Fields (AES-256-GCM)
    name_enc: Mapped[str] = mapped_column(EncryptedString, nullable=False)
    dob_enc: Mapped[date] = mapped_column(EncryptedDate, nullable=False)
    parent_name_enc: Mapped[Optional[str]] = mapped_column(EncryptedString, nullable=True)
    contact_enc: Mapped[Optional[Dict[str, Any]]] = mapped_column(EncryptedJSON, nullable=True)
    gender: Mapped[str] = mapped_column(String(10), nullable=False)  # MALE, FEMALE, OTHER

    # Deterministic Blind Indexes (HMAC-SHA256) for equality lookups
    name_bidx: Mapped[Optional[str]] = mapped_column(String(64), nullable=True, index=True)
    dob_bidx: Mapped[Optional[str]] = mapped_column(String(64), nullable=True, index=True)
    parent_bidx: Mapped[Optional[str]] = mapped_column(String(64), nullable=True, index=True)

    # Relationships
    enrolments = relationship("Enrolment", back_populates="student", cascade="all, delete-orphan")
    consent_requests = relationship("ConsentRequest", back_populates="student", cascade="all, delete-orphan")

    __table_args__ = (
        CheckConstraint(
            "length(apaar_id) = 12 OR apaar_id IS NULL",
            name="ck_students_apaar_id_format"
        ),
    )
