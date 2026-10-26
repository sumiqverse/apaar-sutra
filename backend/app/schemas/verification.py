"""Pydantic v2 schemas for Verification queries and transcripts."""

from datetime import datetime
from typing import List, Optional
import uuid
from pydantic import BaseModel, Field

from app.schemas.student import AcademicRecordResponse


class VerificationRequest(BaseModel):
    apaar_id: str = Field(..., min_length=12, max_length=12, description="12-digit student APAAR ID")
    verifier_id: str = Field(..., description="Registered ID of verifying organization")
    consent_token: Optional[str] = Field(None, description="Student authorization consent token")


class VerificationResult(BaseModel):
    is_verified: bool
    apaar_id: str
    masked_apaar_id: str
    student_name: str
    institution_name: str
    aicte_id: str
    program_name: str
    admission_year: int
    graduation_status: str
    total_credits_earned: float
    cryptographic_signature: str
    verification_timestamp: str
    records: List[AcademicRecordResponse] = []
