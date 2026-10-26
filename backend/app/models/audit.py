"""Immutable append-only audit log with cryptographic SHA-256 hash chaining."""

from datetime import datetime, timezone
import hashlib
import json
from typing import Any, Dict, Optional
import uuid
from sqlalchemy import BigInteger, DateTime, Index, Integer, Sequence, String
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base

audit_seq = Sequence("audit_logs_seq", start=1, increment=1)


class AuditLog(Base):
    __tablename__ = "audit_logs"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    # Monotonically increasing sequence number
    seq: Mapped[int] = mapped_column(
        BigInteger, audit_seq, server_default=audit_seq.next_value(), unique=True, index=True
    )
    actor_id: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    actor_role: Mapped[str] = mapped_column(String(50), nullable=False)
    action: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    entity_type: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    entity_id: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    ip: Mapped[str] = mapped_column(String(50), nullable=False)
    request_id: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    payload: Mapped[Optional[Dict[str, Any]]] = mapped_column(JSONB, nullable=True)

    # Cryptographic SHA-256 Hash Chaining
    prev_hash: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    hash: Mapped[str] = mapped_column(String(64), nullable=False)

    timestamp: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
        index=True,
    )

    __table_args__ = (
        Index("ix_audit_logs_payload_gin", "payload", postgresql_using="gin"),
    )

    @staticmethod
    def compute_entry_hash(
        seq: int,
        actor_id: str,
        action: str,
        entity_id: str,
        payload: Optional[Dict[str, Any]],
        prev_hash: Optional[str],
        timestamp_iso: str,
    ) -> str:
        """Compute tamper-evident SHA-256 hash over log entry components."""
        serialized_payload = json.dumps(payload or {}, sort_keys=True)
        block = f"{seq}:{actor_id}:{action}:{entity_id}:{serialized_payload}:{prev_hash or ''}:{timestamp_iso}"
        return hashlib.sha256(block.encode("utf-8")).hexdigest()
