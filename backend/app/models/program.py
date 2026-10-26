"""Program entity representing academic degree offerings within institutions."""

import uuid
from sqlalchemy import Float, ForeignKey, Integer, String, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, SoftDeleteMixin, TimestampMixin


class Program(Base, TimestampMixin, SoftDeleteMixin):
    __tablename__ = "programs"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    institution_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("institutions.id", ondelete="CASCADE"), nullable=False, index=True
    )
    name: Mapped[str] = mapped_column(String(150), nullable=False)
    level: Mapped[str] = mapped_column(String(30), nullable=False)  # DIPLOMA, UG, PG, PGDM, PHD
    branch: Mapped[str] = mapped_column(String(100), nullable=False)
    academic_year: Mapped[str] = mapped_column(String(20), nullable=False, index=True)  # e.g. "2025-26"
    approved_intake: Mapped[int] = mapped_column(Integer, nullable=False)
    supernumerary_cap_pct: Mapped[float] = mapped_column(Float, nullable=False, default=15.0)
    duration_years: Mapped[int] = mapped_column(Integer, nullable=False, default=4)

    # Relationships
    institution = relationship("Institution", back_populates="programs")
    enrolments = relationship("Enrolment", back_populates="program", cascade="all, delete-orphan")
    validation_issues = relationship("ValidationIssue", back_populates="program", cascade="all, delete-orphan")

    __table_args__ = (
        UniqueConstraint("institution_id", "name", "branch", "academic_year", name="uq_programs_inst_name_branch_ay"),
    )
