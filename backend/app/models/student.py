"""Student and AcademicRecord models keyed by APAAR ID."""

import uuid
from datetime import date
from typing import List, Optional
from sqlalchemy import Date, Float, ForeignKey, Integer, String
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin


class Student(Base, TimestampMixin):
    __tablename__ = "students"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    apaar_id: Mapped[str] = mapped_column(String(12), unique=True, index=True, nullable=False)
    institution_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("institutions.id", ondelete="CASCADE"), nullable=False, index=True
    )
    first_name: Mapped[str] = mapped_column(String(100), nullable=False)
    last_name: Mapped[str] = mapped_column(String(100), nullable=False)
    dob: Mapped[date] = mapped_column(Date, nullable=False)
    gender: Mapped[str] = mapped_column(String(10), nullable=False)
    aadhaar_hash: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    enrollment_number: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    program_name: Mapped[str] = mapped_column(String(150), nullable=False)
    admission_year: Mapped[int] = mapped_column(Integer, nullable=False)
    status: Mapped[str] = mapped_column(String(30), default="ACTIVE", nullable=False)
    verification_status: Mapped[str] = mapped_column(String(30), default="PENDING", nullable=False, index=True)

    # Relationships
    institution = relationship("Institution", back_populates="students")
    academic_records: Mapped[List["AcademicRecord"]] = relationship(
        "AcademicRecord", back_populates="student", cascade="all, delete-orphan"
    )


class AcademicRecord(Base, TimestampMixin):
    __tablename__ = "academic_records"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    student_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("students.id", ondelete="CASCADE"), nullable=False, index=True
    )
    semester: Mapped[int] = mapped_column(Integer, nullable=False)
    course_code: Mapped[str] = mapped_column(String(32), nullable=False)
    course_name: Mapped[str] = mapped_column(String(150), nullable=False)
    credits: Mapped[float] = mapped_column(Float, nullable=False)
    grade_point: Mapped[float] = mapped_column(Float, nullable=False)
    result_status: Mapped[str] = mapped_column(String(20), default="PASS", nullable=False)

    student: Mapped["Student"] = relationship("Student", back_populates="academic_records")
