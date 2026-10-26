"""Institution entity representing AICTE affiliated colleges and universities."""

from typing import List, Optional
import uuid
from sqlalchemy import Boolean, ForeignKey, Integer, String
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, SoftDeleteMixin, TimestampMixin


class Institution(Base, TimestampMixin, SoftDeleteMixin):
    __tablename__ = "institutions"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    aicte_id: Mapped[str] = mapped_column(String(64), unique=True, index=True, nullable=False)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    state_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("states.id", ondelete="RESTRICT"), nullable=False, index=True
    )
    district: Mapped[str] = mapped_column(String(100), nullable=False)
    institution_type: Mapped[str] = mapped_column(
        String(50), nullable=False, default="AFFILIATED"
    )  # UNIVERSITY, AUTONOMOUS, AFFILIATED, STANDALONE_PGDM, OTHER
    status: Mapped[str] = mapped_column(String(30), nullable=False, default="ACTIVE")
    email: Mapped[str] = mapped_column(String(255), nullable=False)
    approved_total_intake: Mapped[int] = mapped_column(Integer, nullable=False, default=0)

    # Relationships
    state_rel = relationship("State", back_populates="institutions")
    programs = relationship("Program", back_populates="institution", cascade="all, delete-orphan")
    enrolments = relationship("Enrolment", back_populates="institution", cascade="all, delete-orphan")
    upload_batches = relationship("UploadBatch", back_populates="institution", cascade="all, delete-orphan")
    validation_issues = relationship("ValidationIssue", back_populates="institution", cascade="all, delete-orphan")
    user_associations = relationship("UserInstitution", back_populates="institution", cascade="all, delete-orphan")
    users = relationship("User", secondary="user_institutions", back_populates="institutions", overlaps="user_associations")
