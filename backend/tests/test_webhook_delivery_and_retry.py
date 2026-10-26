"""
Tests for Webhook HMAC Signatures, Exponential Backoff Retries, and Dead-Letter Queue (DLQ).
"""

from datetime import datetime, timedelta, timezone
import hashlib
import hmac
import json
import uuid
import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker

from app.api.deps import get_db
from app.core.jwt import create_access_token
from app.main import app
from app.models.base import Base
from app.models.credential import WebhookDeliveryLog, WebhookSubscription
from app.models.institution import Institution
from app.models.rbac import Role, User, UserRole
from app.models.state import State
from app.services.webhook_service import BACKOFF_DELAYS, MAX_RETRIES, WebhookService


@pytest.fixture
async def webhook_test_env():
    """Setup SQLite in-memory database with webhook subscription and super admin user."""
    engine = create_async_engine("sqlite+aiosqlite:///:memory:")
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    AsyncSessionLocal = sessionmaker(bind=engine, class_=AsyncSession, expire_on_commit=False)

    async with AsyncSessionLocal() as session:
        st = State(id=uuid.uuid4(), code="DL", name="Delhi")
        session.add(st)
        await session.flush()

        inst = Institution(
            id=uuid.uuid4(),
            aicte_id="1-WH-001",
            name="Delhi Tech University",
            state_id=st.id,
            district="Delhi",
            status="ACTIVE",
            approved_total_intake=400,
        )
        session.add(inst)
        await session.flush()

        # Webhook Subscription
        sub = WebhookSubscription(
            id=uuid.uuid4(),
            institution_id=inst.id,
            url="https://invalid.webhook.destination.test/events",
            secret_enc="whsec_test_secret_12345",
            events=["batch.completed", "alert.created"],
            active=True,
        )
        session.add(sub)

        # Super Admin User
        admin_role = Role(id=uuid.uuid4(), name="SUPER_ADMIN", description="Super Admin")
        session.add(admin_role)
        await session.flush()

        user = User(
            id=uuid.uuid4(),
            email="admin.webhooks@aicte.gov.in",
            password_hash="fakehash",
            full_name="Webhook Admin",
            is_active=True,
        )
        session.add(user)
        await session.flush()

        session.add(UserRole(id=uuid.uuid4(), user_id=user.id, role_id=admin_role.id))
        await session.commit()

        token = create_access_token(
            data={"sub": str(user.id), "email": user.email, "roles": ["SUPER_ADMIN"]}
        )

    async def override_get_db():
        async with AsyncSessionLocal() as sess:
            yield sess

    app.dependency_overrides[get_db] = override_get_db

    yield {
        "engine": engine,
        "token": token,
        "sub_id": sub.id,
        "secret": "whsec_test_secret_12345",
        "institution_id": inst.id,
        "session_factory": AsyncSessionLocal,
    }

    app.dependency_overrides.clear()
    await engine.dispose()


@pytest.mark.asyncio
async def test_webhook_hmac_signature_calculation():
    """Verify that WebhookService computes accurate HMAC-SHA256 signatures."""
    secret = "whsec_super_secret"
    payload = {"event": "batch.completed", "batch_id": "abc-123"}
    payload_bytes = json.dumps(payload, sort_keys=True).encode("utf-8")

    expected_sig = hmac.new(secret.encode("utf-8"), payload_bytes, hashlib.sha256).hexdigest()
    computed_sig = WebhookService.compute_webhook_signature(secret, payload_bytes)

    assert computed_sig == expected_sig


@pytest.mark.asyncio
async def test_webhook_dispatch_and_dlq_transitions(webhook_test_env):
    """Test webhook dispatching to unreachable destination schedules retries and transitions to DLQ."""
    session_factory = webhook_test_env["session_factory"]
    inst_id = webhook_test_env["institution_id"]

    async with session_factory() as db:
        svc = WebhookService(db)
        deliveries = await svc.dispatch_event(
            event_type="batch.completed",
            payload={"batch_id": "batch-001", "records": 10},
            institution_id=inst_id,
        )

        assert len(deliveries) == 1
        delivery = deliveries[0]
        # Since destination URL is unreachable in test, status should transition to RETRYING
        assert delivery.status == "RETRYING"
        assert delivery.attempt_count == 1
        assert delivery.next_retry_at is not None

        # Simulate reaching MAX_RETRIES to trigger Dead-Letter Queue (DLQ)
        delivery.attempt_count = MAX_RETRIES
        await db.commit()

        # Process retries: should mark as DEAD_LETTER
        dlq_items = await svc.process_retries()
        assert len(dlq_items) == 1
        assert dlq_items[0].status == "DEAD_LETTER"


@pytest.mark.asyncio
async def test_admin_webhook_retry_endpoint(webhook_test_env):
    """Test manual retry of a dead-letter webhook delivery via Admin API."""
    token = webhook_test_env["token"]
    session_factory = webhook_test_env["session_factory"]
    sub_id = webhook_test_env["sub_id"]

    # Seed a DEAD_LETTER log
    async with session_factory() as db:
        dlq_log = WebhookDeliveryLog(
            id=uuid.uuid4(),
            subscription_id=sub_id,
            event_type="alert.created",
            payload={"alert": "intake_overshoot"},
            status="DEAD_LETTER",
            attempt_count=5,
            created_at=datetime.now(timezone.utc),
        )
        db.add(dlq_log)
        await db.commit()
        log_id = dlq_log.id

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        retry_resp = await client.post(
            f"/api/v1/admin/webhooks/deliveries/{log_id}/retry",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert retry_resp.status_code == 200
        data = retry_resp.json()
        assert data["id"] == str(log_id)
        assert data["status"] in ["RETRYING", "SUCCESS", "DEAD_LETTER"]
