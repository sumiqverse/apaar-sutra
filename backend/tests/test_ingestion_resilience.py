"""Resilience and fault-tolerance tests for APAAR provider outages, circuit breaker, and retry reconciliation."""

import asyncio
from datetime import date
from unittest.mock import AsyncMock, patch
import uuid
import httpx
import pytest
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker

from app.integrations.apaar.circuit_breaker import CircuitBreaker, CircuitBreakerOpenException, CircuitState
from app.integrations.apaar.mock_provider import MockApaarProvider
from app.models.base import Base
from app.models.student import Student
from app.workers.tasks import retry_pending_apaar_verifications


def test_circuit_breaker_transitions():
    """Circuit breaker trips to OPEN on threshold failures and recovers on success."""
    cb = CircuitBreaker(failure_threshold=3, recovery_timeout=0.1)
    assert cb.state == CircuitState.CLOSED
    assert cb.can_execute() is True

    # Record 2 failures -> remains CLOSED
    cb.record_failure()
    cb.record_failure()
    assert cb.state == CircuitState.CLOSED
    assert cb.can_execute() is True

    # 3rd failure -> trips to OPEN
    cb.record_failure()
    assert cb.state == CircuitState.OPEN
    assert cb.can_execute() is False

    # Immediate execution while OPEN raises CircuitBreakerOpenException
    with pytest.raises(CircuitBreakerOpenException):
        with cb:
            pass

    # Wait for recovery timeout
    import time
    time.sleep(0.15)
    assert cb.can_execute() is True
    assert cb.state == CircuitState.HALF_OPEN

    # Success resets to CLOSED
    cb.record_success()
    assert cb.state == CircuitState.CLOSED


@pytest.mark.asyncio
async def test_provider_down_graceful_pending_fallback():
    """When APAAR gateway is down, provider gracefully returns status=PENDING instead of failing."""
    provider = MockApaarProvider(base_url="http://non-existent-apaar-gateway:9999", max_retries=1)

    # Simulate network failure / gateway down
    with patch("httpx.AsyncClient.post", side_effect=httpx.ConnectError("Connection refused")):
        res = await provider.verify("200000000010", name="Rohan Das")

        assert res.found is False
        assert res.status == "PENDING"
        assert "fallback" in res.details
        assert "Gateway connection error" in res.details["fallback"]


@pytest.mark.asyncio
async def test_batch_verify_graceful_pending_fallback():
    """Batch verify returns PENDING for all items if service is unreachable."""
    provider = MockApaarProvider(base_url="http://non-existent-apaar-gateway:9999", max_retries=1)

    with patch("httpx.AsyncClient.post", side_effect=httpx.TimeoutException("Read timeout")):
        items = [
            {"apaar_id": "200000000010", "name": "Student A"},
            {"apaar_id": "200000000020", "name": "Student B"},
        ]
        results = await provider.verify_batch(items)

        assert len(results) == 2
        assert results["200000000010"].status == "PENDING"
        assert results["200000000020"].status == "PENDING"


@pytest.mark.asyncio
async def test_retry_pending_apaar_verifications_task():
    """Celery background task re-checks students in PENDING status and updates to VERIFIED."""
    engine = create_async_engine("sqlite+aiosqlite:///:memory:")
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    AsyncSessionLocal = sessionmaker(bind=engine, class_=AsyncSession, expire_on_commit=False)

    async with AsyncSessionLocal() as session:
        # Create student with PENDING status
        st = Student(
            id=uuid.uuid4(),
            apaar_id="200000000099",
            apaar_status="PENDING",
            name_enc="Kiran Rao",
            dob_enc=date(2003, 5, 20),
            gender="FEMALE",
            name_bidx="bidx_name",
            dob_bidx="bidx_dob",
        )
        session.add(st)
        await session.commit()

        # Run reconciliation task
        from app.integrations.apaar.base import ApaarVerificationResult
        mock_res = ApaarVerificationResult(
            apaar_id="200000000099",
            is_valid=True,
            status="VERIFIED",
            name_match_score=100,
            dob_match=True,
        )

        from app.workers.tasks import async_retry_pending_verifications
        with patch("app.integrations.apaar.mock_provider.MockApaarProvider.verify_batch", new_callable=AsyncMock) as mock_verify_batch:
            mock_verify_batch.return_value = {"200000000099": mock_res}
            reconciled_count = await async_retry_pending_verifications(session=session)

            assert reconciled_count == 1
            await session.refresh(st)
            assert st.apaar_status == "VERIFIED"

    await engine.dispose()
