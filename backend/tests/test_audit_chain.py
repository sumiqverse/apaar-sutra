"""Unit tests for tamper-evident audit hash chaining and cryptographic verification."""

import uuid
import pytest
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker

from app.models.base import Base
from app.models.audit import AuditLog
from app.services.audit_service import AuditService


@pytest.fixture
async def async_db():
    engine = create_async_engine("sqlite+aiosqlite:///:memory:")
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    AsyncSessionLocal = sessionmaker(bind=engine, class_=AsyncSession, expire_on_commit=False)
    async with AsyncSessionLocal() as session:
        yield session


@pytest.mark.anyio
async def test_audit_hash_chain_and_tamper_detection(async_db: AsyncSession):
    # 1. Log 10 sequential audit events
    for i in range(1, 11):
        await AuditService.log_event(
            session=async_db,
            actor_id=f"user_{i}",
            actor_role="INSTITUTION_ADMIN",
            action=f"STUDENT_ENROL_{i}",
            entity_type="STUDENT",
            entity_id=str(uuid.uuid4()),
            ip="192.168.1.50",
            request_id=f"req-{i}",
            payload={"student_name": f"Student {i}", "step": i},
        )
    await async_db.commit()

    # 2. Verify complete chain when untampered
    verify_result = await AuditService.verify_chain(async_db)
    assert verify_result["valid"] is True
    assert verify_result["checked"] == 10
    assert verify_result["first_broken_seq"] is None

    # 3. Artificially tamper with sequence row 5 (simulate database compromise or unauthorized edit)
    tamper_stmt = (
        update(AuditLog)
        .where(AuditLog.seq == 5)
        .values(action="UNAUTHORIZED_TAMPERED_ACTION")
    )
    await async_db.execute(tamper_stmt)
    await async_db.commit()

    # 4. Re-verify chain - must detect corruption and pinpoint seq 5!
    tamper_result = await AuditService.verify_chain(async_db)
    assert tamper_result["valid"] is False
    assert tamper_result["first_broken_seq"] == 5
    assert "Corrupted hash at seq 5" in tamper_result["reason"]
