"""Enterprise Webhook Dispatcher with HMAC-SHA256 signatures, Exponential Backoff, and Dead-Letter Queue."""

from datetime import datetime, timedelta, timezone
import hashlib
import hmac
import json
import logging
from typing import Any, Dict, List, Optional
import uuid
import httpx
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import NotFoundException
from app.models.credential import WebhookDeliveryLog, WebhookSubscription

logger = logging.getLogger("app.services.webhooks")

# Exponential backoff schedule in seconds: 30s, 2m, 10m, 30m, 2h
BACKOFF_DELAYS = [30, 120, 600, 1800, 7200]
MAX_ATTEMPTS = 5


class WebhookService:
    def __init__(self, session: AsyncSession):
        self.session = session

    @staticmethod
    def compute_webhook_signature(secret: str, payload_bytes: bytes) -> str:
        """Computes HMAC-SHA256 signature for webhook payload."""
        return hmac.new(secret.encode("utf-8"), payload_bytes, hashlib.sha256).hexdigest()

    async def register_subscription(
        self,
        institution_id: uuid.UUID,
        url: str,
        events: List[str],
        secret: str,
    ) -> WebhookSubscription:
        """Creates a new institutional webhook subscription."""
        sub = WebhookSubscription(
            institution_id=institution_id,
            url=url,
            events=events,
            secret_enc=secret,  # In production, wrapped via EncryptedString
            is_active=True,
        )
        self.session.add(sub)
        await self.session.commit()
        await self.session.refresh(sub)
        return sub

    async def dispatch_event(
        self,
        event_type: str,
        payload: Dict[str, Any],
        institution_id: Optional[uuid.UUID] = None,
    ) -> List[WebhookDeliveryLog]:
        """Dispatches an event to all matching active webhook subscriptions."""
        stmt = select(WebhookSubscription).where(WebhookSubscription.is_active == True)
        if institution_id:
            stmt = stmt.where(WebhookSubscription.institution_id == institution_id)

        res = await self.session.execute(stmt)
        subs = res.scalars().all()

        matching_subs = [s for s in subs if event_type in s.events or "*" in s.events]
        deliveries = []

        now_utc = datetime.now(timezone.utc)
        payload_bytes = json.dumps(payload, sort_keys=True).encode("utf-8")

        for sub in matching_subs:
            sig = self.compute_webhook_signature(sub.secret_enc, payload_bytes)
            headers = {
                "Content-Type": "application/json",
                "X-APAAR-Event": event_type,
                "X-Signature": f"sha256={sig}",
                "X-Delivery-ID": str(uuid.uuid4()),
                "User-Agent": "APAAR-Sutra-Webhook-Dispatcher/1.0",
            }

            status = "SUCCESS"
            status_code = None
            response_body = None
            next_retry = None

            try:
                async with httpx.AsyncClient(timeout=5.0) as client:
                    resp = await client.post(sub.url, content=payload_bytes, headers=headers)
                    status_code = resp.status_code
                    response_body = resp.text[:500]
                    if resp.status_code >= 400:
                        status = "RETRYING"
                        next_retry = now_utc + timedelta(seconds=BACKOFF_DELAYS[0])
            except Exception as e:
                status = "RETRYING"
                response_body = str(e)[:500]
                next_retry = now_utc + timedelta(seconds=BACKOFF_DELAYS[0])

            delivery = WebhookDeliveryLog(
                subscription_id=sub.id,
                event_type=event_type,
                payload=payload,
                status=status,
                status_code=status_code,
                response_body=response_body,
                attempt_count=1,
                next_retry_at=next_retry,
                created_at=now_utc,
            )
            self.session.add(delivery)
            deliveries.append(delivery)

        await self.session.commit()
        return deliveries

    async def retry_delivery(self, delivery_id: uuid.UUID) -> WebhookDeliveryLog:
        """Manually retries a failed or dead-letter webhook delivery."""
        stmt = select(WebhookDeliveryLog).where(WebhookDeliveryLog.id == delivery_id)
        res = await self.session.execute(stmt)
        log = res.scalar_one_or_none()

        if not log:
            raise NotFoundException(message="Webhook delivery record not found.")

        sub_stmt = select(WebhookSubscription).where(WebhookSubscription.id == log.subscription_id)
        sub_res = await self.session.execute(sub_stmt)
        sub = sub_res.scalar_one_or_none()

        if not sub:
            raise NotFoundException(message="Webhook subscription not found.")

        now_utc = datetime.now(timezone.utc)
        payload_bytes = json.dumps(log.payload, sort_keys=True).encode("utf-8")
        sig = self.compute_webhook_signature(sub.secret_enc, payload_bytes)
        headers = {
            "Content-Type": "application/json",
            "X-APAAR-Event": log.event_type,
            "X-Signature": f"sha256={sig}",
            "X-Delivery-ID": str(uuid.uuid4()),
            "X-Retry-Attempt": str(log.attempt_count + 1),
        }

        log.attempt_count += 1
        try:
            async with httpx.AsyncClient(timeout=5.0) as client:
                resp = await client.post(sub.url, content=payload_bytes, headers=headers)
                log.status_code = resp.status_code
                log.response_body = resp.text[:500]
                if resp.status_code < 400:
                    log.status = "SUCCESS"
                    log.next_retry_at = None
                else:
                    if log.attempt_count >= MAX_ATTEMPTS:
                        log.status = "DEAD_LETTER"
                        log.next_retry_at = None
                    else:
                        delay = BACKOFF_DELAYS[min(log.attempt_count - 1, len(BACKOFF_DELAYS) - 1)]
                        log.status = "RETRYING"
                        log.next_retry_at = now_utc + timedelta(seconds=delay)
        except Exception as e:
            log.response_body = str(e)[:500]
            if log.attempt_count >= MAX_ATTEMPTS:
                log.status = "DEAD_LETTER"
                log.next_retry_at = None
            else:
                delay = BACKOFF_DELAYS[min(log.attempt_count - 1, len(BACKOFF_DELAYS) - 1)]
                log.status = "RETRYING"
                log.next_retry_at = now_utc + timedelta(seconds=delay)

        await self.session.commit()
        await self.session.refresh(log)
        return log

    async def list_deliveries(
        self,
        status: Optional[str] = None,
        limit: int = 50,
    ) -> List[WebhookDeliveryLog]:
        """Lists recent webhook delivery logs, filterable by status (e.g. DEAD_LETTER)."""
        stmt = select(WebhookDeliveryLog).order_by(WebhookDeliveryLog.created_at.desc()).limit(limit)
        if status:
            stmt = stmt.where(WebhookDeliveryLog.status == status)
        res = await self.session.execute(stmt)
        return list(res.scalars().all())
