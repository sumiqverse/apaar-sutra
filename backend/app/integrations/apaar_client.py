"""Client adapter for external National APAAR Registry."""

import logging
from typing import Any, Dict, Optional
import httpx

from app.core.config import settings
from app.validation.apaar_rules import validate_apaar_id

logger = logging.getLogger(__name__)


class ApaarClient:
    """HTTP client communicating with Mock or National APAAR verification gateways."""

    def __init__(self, base_url: Optional[str] = None, api_key: Optional[str] = None):
        self.base_url = (base_url or settings.APAAR_GATEWAY_URL).rstrip("/")
        self.api_key = api_key or settings.APAAR_API_KEY

    async def verify_apaar(self, apaar_id: str) -> Dict[str, Any]:
        """Perform formal verification against registry gateway."""
        # Check syntax first locally
        is_valid_format, msg = validate_apaar_id(apaar_id)
        if not is_valid_format:
            return {"is_valid": False, "reason": msg, "verified_at_registry": False}

        headers = {"Authorization": f"Bearer {self.api_key}", "Accept": "application/json"}
        try:
            async with httpx.AsyncClient(timeout=5.0) as client:
                resp = await client.get(f"{self.base_url}/verify/{apaar_id}", headers=headers)
                if resp.status_code == 200:
                    data = resp.json()
                    return {"is_valid": True, "details": data, "verified_at_registry": True}
                elif resp.status_code == 404:
                    return {"is_valid": False, "reason": "APAAR ID not found in national registry.", "verified_at_registry": True}
                else:
                    return {"is_valid": False, "reason": f"Registry returned status {resp.status_code}", "verified_at_registry": False}
        except httpx.RequestError as exc:
            logger.warning(f"Failed to connect to APAAR Gateway: {exc}")
            # Fallback to local mathematical validation if gateway is temporarily unreachable
            return {"is_valid": is_valid_format, "reason": "Gateway unreachable, validated via local checksum.", "verified_at_registry": False}
