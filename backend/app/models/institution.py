"""Institution entity representing AICTE affiliated colleges/universities."""

import uuid
from sqlalchemy import Boolean, String
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin


class Institution(Base, TimestampMixin):
    __tablename__ = "institutions"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    aicte_id: Mapped[str] = mapped_column(String(64), unique=True, index=True, nullable=False)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    state: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    district: Mapped[str] = mapped_column(String(100), nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    contact_email: Mapped[str] = mapped_column(String(255), nullable=False)

    # Relationship to students
    students = relationship("Student", back_populates="institution", cascade="all, delete-orphan")
