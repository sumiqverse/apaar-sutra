"""Tamper-evident audit service with SHA-256 cryptographic hash chaining and advisory locking."""

import asyncio
from datetime import datetime, timezone
import hashlib
import json
from typing import Any, Dict, List, Optional, Tuple
import uuid
from sqlalchemy import desc, func, select, text
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import Session

from app.models.audit import AuditLog

GENESIS_HASH = "0" * 64
AUDIT_ADVISORY_LOCK_ID = 84729103  # Consistent 64-bit integer lock identifier
_memory_lock = asyncio.Lock()


def canonical_json(data: Any) -> str:
    """Format JSON with sorted keys and tight separators for deterministic hashing."""
    if data is None:
        return "{}"
    return json.dumps(data, sort_keys=True, separators=(",", ":"), default=str)


def compute_audit_hash(
    seq: int,
    actor_id: str,
    actor_role: str,
    action: str,
    entity_type: str,
    entity_id: str,
    ip: str,
    request_id: str,
    payload: Optional[Dict[str, Any]],
    prev_hash: str,
    timestamp_iso: str,
) -> str:
    """Compute deterministic SHA-256 hash over canonical audit block."""
    block = (
        f"{prev_hash}:"
        f"{seq}:"
        f"{actor_id}:"
        f"{actor_role}:"
        f"{action}:"
        f"{entity_type}:"
        f"{entity_id}:"
        f"{ip}:"
        f"{request_id}:"
        f"{canonical_json(payload)}:"
        f"{timestamp_iso}"
    )
    return hashlib.sha256(block.encode("utf-8")).hexdigest()


class AuditService:
    """Enterprise append-only audit trail service."""

    @classmethod
    async def log_event(
        cls,
        session: AsyncSession,
        actor_id: str,
        actor_role: str,
        action: str,
        entity_type: str,
        entity_id: str,
        ip: str = "127.0.0.1",
        request_id: str = "sys-internal",
        payload: Optional[Dict[str, Any]] = None,
    ) -> AuditLog:
        """Write a tamper-evident audit record serialized by database advisory lock."""
        # 1. Acquire transaction advisory lock on PostgreSQL to guarantee strict sequence ordering
        try:
            await session.execute(
                text(f"SELECT pg_advisory_xact_lock({AUDIT_ADVISORY_LOCK_ID})")
            )
        except Exception:
            pass  # Non-PostgreSQL dialects (e.g. SQLite tests) handle locking at DB engine level

        # 2. Fetch the latest record in the chain to read prev_hash and determine seq
        latest_stmt = (
            select(AuditLog)
            .order_by(desc(AuditLog.seq))
            .limit(1)
        )
        latest_res = await session.execute(latest_stmt)
        latest_entry = latest_res.scalar_one_or_none()

        if latest_entry:
            seq = latest_entry.seq + 1
            prev_hash = latest_entry.hash
        else:
            seq = 1
            prev_hash = GENESIS_HASH

        now_utc = datetime.now(timezone.utc)
        timestamp_iso = now_utc.isoformat()

        entry_hash = compute_audit_hash(
            seq=seq,
            actor_id=actor_id,
            actor_role=actor_role,
            action=action,
            entity_type=entity_type,
            entity_id=entity_id,
            ip=ip,
            request_id=request_id,
            payload=payload,
            prev_hash=prev_hash,
            timestamp_iso=timestamp_iso,
        )

        audit_entry = AuditLog(
            id=uuid.uuid4(),
            seq=seq,
            actor_id=actor_id,
            actor_role=actor_role,
            action=action,
            entity_type=entity_type,
            entity_id=entity_id,
            ip=ip,
            request_id=request_id,
            payload=payload or {},
            prev_hash=prev_hash,
            hash=entry_hash,
            timestamp=now_utc,
        )

        session.add(audit_entry)
        await session.flush()
        return audit_entry

    @classmethod
    async def verify_chain(
        cls,
        session: AsyncSession,
        start_seq: int = 1,
        limit: int = 10000,
    ) -> Dict[str, Any]:
        """Verify the cryptographic integrity of the audit hash chain.
        
        Returns:
            { "valid": bool, "checked": int, "first_broken_seq": Optional[int] }
        """
        stmt = (
            select(AuditLog)
            .where(AuditLog.seq >= start_seq)
            .order_by(AuditLog.seq.asc())
            .limit(limit)
        )
        res = await session.execute(stmt)
        entries: List[AuditLog] = list(res.scalars().all())

        if not entries:
            return {"valid": True, "checked": 0, "first_broken_seq": None}

        # If starting after seq 1, look up the preceding record to obtain its hash
        if start_seq > 1:
            prev_stmt = select(AuditLog.hash).where(AuditLog.seq == start_seq - 1)
            prev_res = await session.execute(prev_stmt)
            expected_prev_hash = prev_res.scalar_one_or_none() or GENESIS_HASH
        else:
            expected_prev_hash = GENESIS_HASH

        checked_count = 0
        for entry in entries:
            checked_count += 1

            # 1. Verify prev_hash matches the previous record's hash
            if entry.prev_hash != expected_prev_hash:
                return {
                    "valid": False,
                    "checked": checked_count,
                    "first_broken_seq": entry.seq,
                    "reason": f"Mismatched prev_hash at seq {entry.seq}",
                }

            # 2. Recompute hash
            recomputed = compute_audit_hash(
                seq=entry.seq,
                actor_id=entry.actor_id,
                actor_role=entry.actor_role,
                action=entry.action,
                entity_type=entry.entity_type,
                entity_id=entry.entity_id,
                ip=entry.ip,
                request_id=entry.request_id,
                payload=entry.payload,
                prev_hash=entry.prev_hash,
                timestamp_iso=entry.timestamp.isoformat(),
            )

            if entry.hash != recomputed:
                return {
                    "valid": False,
                    "checked": checked_count,
                    "first_broken_seq": entry.seq,
                    "reason": f"Corrupted hash at seq {entry.seq}",
                }

            expected_prev_hash = entry.hash

        return {
            "valid": True,
            "checked": checked_count,
            "first_broken_seq": None,
        }
