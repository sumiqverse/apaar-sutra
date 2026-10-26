"""HTTP Client Provider communicating with Mock APAAR Gateway with circuit breaking & retries."""

import asyncio
from datetime import date
import logging
from typing import Any, Dict, List, Optional
import httpx

from app.core.config import settings
from app.integrations.apaar.base import ApaarProvider, ApaarVerificationResult
from app.integrations.apaar.circuit_breaker import CircuitBreaker, CircuitBreakerOpenException
from app.validation.apaar_validator import validate_apaar

logger = logging.getLogger("apaar_mock_provider")


class MockApaarProvider(ApaarProvider):
    """Resilient HTTP client communicating with the Mock National APAAR Gateway."""

    def __init__(
        self,
        base_url: Optional[str] = None,
        api_key: Optional[str] = None,
        timeout: float = 5.0,
        max_retries: int = 3,
    ):
        self.base_url = (base_url or getattr(settings, "APAAR_GATEWAY_URL", "http://localhost:8001")).rstrip("/")
        self.api_key = api_key or getattr(settings, "APAAR_API_KEY", "mock-apaar-secret-key-2026")
        self.timeout = timeout
        self.max_retries = max_retries
        self.circuit_breaker = CircuitBreaker(name="MOCK_APAAR_GATEWAY", failure_threshold=5, recovery_timeout_seconds=30.0)

    def _headers(self) -> Dict[str, str]:
        return {
            "X-API-Key": self.api_key,
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
            "Accept": "application/json",
        }

    async def verify(
        self,
        apaar_id: str,
        name: Optional[str] = None,
        dob: Optional[date] = None,
    ) -> ApaarVerificationResult:
        """Verify single student APAAR ID with retry policy and circuit breaker."""
        # 1. Format validation first
        fmt_res = validate_apaar(apaar_id)
        if not fmt_res.is_valid:
            return ApaarVerificationResult(
                apaar_id=apaar_id,
                is_valid=False,
                status="NOT_FOUND",
                reason=fmt_res.message,
                verified_at_registry=False,
            )

        clean_id = fmt_res.normalized_id

        # 2. Check circuit breaker state
        if not self.circuit_breaker.can_execute():
            logger.warning(f"Circuit breaker OPEN for APAAR Gateway. Marking {clean_id} as PENDING.")
            return ApaarVerificationResult(
                apaar_id=clean_id,
                is_valid=True,
                status="PENDING",
                reason="Gateway circuit is open due to recent outages. Ingestion completed with PENDING status.",
                provider_unavailable=True,
            )

        payload = {
            "apaar_id": clean_id,
            "name": name,
            "dob": dob.isoformat() if dob else None,
        }

        # 3. Request with exponential backoff
        for attempt in range(self.max_retries):
            try:
                async with httpx.AsyncClient(timeout=self.timeout) as client:
                    resp = await client.post(
                        f"{self.base_url}/apaar/verify",
                        json=payload,
                        headers=self._headers(),
                    )
                    if resp.status_code == 200:
                        data = resp.json()
                        self.circuit_breaker.record_success()
                        return self._map_response(clean_id, data)
                    elif resp.status_code == 503 or resp.status_code >= 500:
                        raise httpx.HTTPStatusError("Gateway server error", request=resp.request, response=resp)
                    else:
                        self.circuit_breaker.record_success()
                        return ApaarVerificationResult(
                            apaar_id=clean_id,
                            is_valid=False,
                            status="NOT_FOUND",
                            reason=f"Gateway responded with status {resp.status_code}",
                            verified_at_registry=True,
                        )
            except (httpx.RequestError, httpx.HTTPStatusError) as exc:
                logger.warning(f"Attempt {attempt + 1}/{self.max_retries} to verify APAAR {clean_id} failed: {exc}")
                if attempt == self.max_retries - 1:
                    self.circuit_breaker.record_failure()
                    # Graceful degradation: Mark as PENDING rather than rejecting valid data
                    return ApaarVerificationResult(
                        apaar_id=clean_id,
                        is_valid=True,
                        status="PENDING",
                        reason=f"Gateway connection error: {exc}. Stored as PENDING for asynchronous retry.",
                        details={"fallback": f"Gateway connection error: {exc}"},
                        provider_unavailable=True,
                    )
                await asyncio.sleep(0.3 * (2 ** attempt))

        return ApaarVerificationResult(
            apaar_id=clean_id,
            is_valid=True,
            status="PENDING",
            reason="Exceeded retry attempts. Stored as PENDING.",
            details={"fallback": "Exceeded retry attempts"},
            provider_unavailable=True,
        )

    async def verify_batch(
        self,
        items: List[Dict[str, Any]],
    ) -> Dict[str, ApaarVerificationResult]:
        """Batch verify up to 500 APAAR IDs in a single HTTP payload."""
        results: Dict[str, ApaarVerificationResult] = {}
        if not items:
            return results

        # Pre-validate formats locally
        valid_payload_items = []
        for item in items:
            raw_id = item.get("apaar_id", "")
            fmt = validate_apaar(raw_id)
            if not fmt.is_valid:
                results[raw_id] = ApaarVerificationResult(
                    apaar_id=raw_id,
                    is_valid=False,
                    status="NOT_FOUND",
                    reason=fmt.message,
                )
            else:
                d = item.get("dob")
                dob_str = d.isoformat() if isinstance(d, date) else (str(d) if d else None)
                valid_payload_items.append({
                    "apaar_id": fmt.normalized_id,
                    "name": item.get("name"),
                    "dob": dob_str,
                })

        if not valid_payload_items:
            return results

        # Circuit breaker check
        if not self.circuit_breaker.can_execute():
            for it in valid_payload_items:
                cid = it["apaar_id"]
                results[cid] = ApaarVerificationResult(
                    apaar_id=cid,
                    is_valid=True,
                    status="PENDING",
                    reason="Circuit breaker OPEN; queued for retry.",
                    provider_unavailable=True,
                )
            return results

        # Dispatch batch call with backoff
        for attempt in range(self.max_retries):
            try:
                async with httpx.AsyncClient(timeout=self.timeout * 2) as client:
                    resp = await client.post(
                        f"{self.base_url}/apaar/verify-batch",
                        json={"items": valid_payload_items},
                        headers=self._headers(),
                    )
                    if resp.status_code == 200:
                        batch_data = resp.json().get("results", {})
                        self.circuit_breaker.record_success()
                        for cid, rec in batch_data.items():
                            results[cid] = self._map_response(cid, rec)
                        return results
                    elif resp.status_code >= 500:
                        raise httpx.HTTPStatusError("Batch gateway error", request=resp.request, response=resp)
            except (httpx.RequestError, httpx.HTTPStatusError) as exc:
                logger.warning(f"Batch verification attempt {attempt + 1}/{self.max_retries} failed: {exc}")
                if attempt == self.max_retries - 1:
                    self.circuit_breaker.record_failure()
                    for it in valid_payload_items:
                        cid = it["apaar_id"]
                        results[cid] = ApaarVerificationResult(
                            apaar_id=cid,
                            is_valid=True,
                            status="PENDING",
                            reason=f"Gateway batch error: {exc}. Stored as PENDING.",
                            provider_unavailable=True,
                        )
                    return results
                await asyncio.sleep(0.3 * (2 ** attempt))

        return results

    def _map_response(self, apaar_id: str, data: Dict[str, Any]) -> ApaarVerificationResult:
        found = data.get("found", False)
        status_str = data.get("status", "NOT_FOUND").upper()
        name_score = data.get("name_match_score", 0)
        dob_match = data.get("dob_match", False)

        if not found:
            return ApaarVerificationResult(
                apaar_id=apaar_id,
                is_valid=False,
                status="NOT_FOUND",
                name_match_score=name_score,
                dob_match=dob_match,
                verified_at_registry=True,
                reason="APAAR ID not found in national registry.",
            )

        # Evaluate mismatches
        final_status = "VERIFIED"
        reasons = []
        if name_score < 60:
            final_status = "MISMATCH"
            reasons.append(f"Name match score too low ({name_score}/100)")
        if not dob_match:
            final_status = "MISMATCH"
            reasons.append("Date of birth does not match national registry")

        return ApaarVerificationResult(
            apaar_id=apaar_id,
            is_valid=True,
            status=final_status,
            name_match_score=name_score,
            dob_match=dob_match,
            verified_at_registry=True,
            details=data,
            reason="; ".join(reasons) if reasons else None,
        )
