"""APAAR Integration Provider factory and exports."""

from typing import Optional

from app.core.config import settings
from app.integrations.apaar.base import ApaarProvider, ApaarVerificationResult
from app.integrations.apaar.circuit_breaker import CircuitBreaker, CircuitState
from app.integrations.apaar.mock_provider import MockApaarProvider
from app.integrations.apaar.real_provider import RealApaarProvider

_provider_instance: Optional[ApaarProvider] = None


def get_apaar_provider() -> ApaarProvider:
    """Return configured APAAR provider singleton based on environment settings."""
    global _provider_instance
    if _provider_instance is None:
        provider_type = getattr(settings, "APAAR_PROVIDER", "mock").lower()
        if provider_type == "real":
            _provider_instance = RealApaarProvider()
        else:
            _provider_instance = MockApaarProvider()
    return _provider_instance


__all__ = [
    "ApaarProvider",
    "ApaarVerificationResult",
    "CircuitBreaker",
    "CircuitState",
    "MockApaarProvider",
    "RealApaarProvider",
    "get_apaar_provider",
]
