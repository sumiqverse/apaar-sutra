"""Abstract base provider interface and data models for APAAR verification."""

from abc import ABC, abstractmethod
from dataclasses import dataclass
from datetime import date
from typing import Any, Dict, List, Optional


@dataclass
class ApaarVerificationResult:
    apaar_id: str
    is_valid: bool
    status: str  # "VERIFIED", "NOT_FOUND", "MISMATCH", "PENDING", "UNVERIFIED", "ACTIVE"
    name_match_score: int = 0
    dob_match: bool = False
    details: Optional[Dict[str, Any]] = None
    reason: Optional[str] = None
    verified_at_registry: bool = False
    provider_unavailable: bool = False
    last_known_institution: Optional[str] = None
    found: bool = False

    def __post_init__(self):
        if not self.found and (self.status in ("ACTIVE", "VERIFIED") or self.verified_at_registry):
            self.found = True



class ApaarProvider(ABC):
    """Abstract interface defining the contract for national APAAR identity verification."""

    @abstractmethod
    async def verify(
        self,
        apaar_id: str,
        name: Optional[str] = None,
        dob: Optional[date] = None,
    ) -> ApaarVerificationResult:
        """Verify a single student APAAR ID against national registry."""
        pass

    @abstractmethod
    async def verify_batch(
        self,
        items: List[Dict[str, Any]],
    ) -> Dict[str, ApaarVerificationResult]:
        """Verify a batch of student APAAR IDs (up to 500 per call)."""
        pass
