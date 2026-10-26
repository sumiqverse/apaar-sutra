"""Pydantic v2 schemas for Verifiable Credentials, DPDP Consent, Certificates, and JWKS."""

from datetime import datetime
from typing import Any, Dict, List, Optional
import uuid
from pydantic import BaseModel, Field


# ---------------------------------------------------------------------------
# Verifiable Student Record Schemas
# ---------------------------------------------------------------------------

class RecordIssueRequest(BaseModel):
    enrolment_id: uuid.UUID = Field(..., description="ID of student enrolment to issue verifiable record for")
    expires_in_days: Optional[int] = Field(None, ge=1, le=3650, description="Optional validity duration in days")
    template_id: Optional[str] = Field("aicte_classic", description="Certificate/transcript layout template")


class VerifiableCredentialPayload(BaseModel):
    record_id: str
    token: str
    apaar_ref: str
    student_ref_id: str
    institution: Dict[str, Any]
    program: Dict[str, Any]
    academic_year: str
    enrolment_start: str
    expected_end: str
    status: str
    issued_at: str
    expires_at: Optional[str] = None
    kid: str


class IssuedRecordResponse(BaseModel):
    id: uuid.UUID
    enrolment_id: uuid.UUID
    token: str
    kid: str
    status: str
    issued_at: datetime
    expires_at: Optional[datetime] = None
    revoked_at: Optional[datetime] = None
    revoke_reason: Optional[str] = None
    signature: str
    payload: Dict[str, Any]
    verification_url: str
    pdf_download_url: str


class PublicVerificationResult(BaseModel):
    status: str  # VALID, REVOKED, SUPERSEDED, EXPIRED, INVALID_SIGNATURE
    is_authentic: bool
    institution_name: Optional[str] = None
    aicte_id: Optional[str] = None
    program_name: Optional[str] = None
    academic_year: Optional[str] = None
    enrolment_start: Optional[str] = None
    expected_end: Optional[str] = None
    student_ref_id: Optional[str] = None
    issued_at: Optional[str] = None
    expires_at: Optional[str] = None
    revoked_at: Optional[str] = None
    revoke_reason: Optional[str] = None
    kid: Optional[str] = None
    signature_fingerprint: Optional[str] = None
    details: Dict[str, Any] = Field(default_factory=dict)


class OfflineVerificationRequest(BaseModel):
    json_payload: Optional[Dict[str, Any]] = None
    signature: Optional[str] = None
    kid: Optional[str] = None
    pdf_base64: Optional[str] = None


class OfflineVerificationResult(BaseModel):
    is_signature_valid: bool
    status: str
    kid: Optional[str] = None
    live_status: Optional[str] = None
    reason: Optional[str] = None
    payload_summary: Dict[str, Any] = Field(default_factory=dict)


class RecordRevokeRequest(BaseModel):
    reason: str = Field(..., min_length=3, max_length=255, description="Administrative justification for credential revocation")


# ---------------------------------------------------------------------------
# DPDP Act 2023 Consent Schemas
# ---------------------------------------------------------------------------

ALLOWED_CONSENT_FIELDS = [
    "name",
    "dob",
    "gender",
    "apaar_id",
    "institution_name",
    "institution_aicte_id",
    "program_name",
    "academic_year",
    "enrollment_status",
    "admission_date",
    "total_credits",
    "cgpa",
    "degree_awarded",
]


class VerifierOrgCreate(BaseModel):
    org_name: str = Field(..., min_length=2, max_length=255)
    cin_gstin: str = Field(..., min_length=5, max_length=50)
    contact_email: str = Field(..., min_length=5, max_length=255)
    purpose_categories: List[str] = Field(default=["EMPLOYMENT", "BACKGROUND_CHECK"])


class VerifierOrgResponse(BaseModel):
    id: uuid.UUID
    org_name: str
    cin_gstin: str
    contact_email: str
    purpose_categories: List[str]
    status: str
    created_at: datetime


class ConsentCreateRequest(BaseModel):
    apaar_id: str = Field(..., min_length=12, max_length=12, description="12-digit student APAAR ID")
    verifier_id: str = Field(..., description="Registered identifier of verifier organization")
    verifier_org_name: Optional[str] = Field("Authorized Verifier Organization", description="Human-readable verifier name")
    purpose: str = Field(..., min_length=3, max_length=255, description="Specific justification for record access")
    purpose_category: str = Field("EMPLOYMENT", description="EMPLOYMENT, HIGHER_EDUCATION, SCHOLARSHIP, VISA, GENERAL")
    fields_requested: List[str] = Field(..., min_length=1, description="List of fields requested from allowlist")
    retention_days: int = Field(30, ge=1, le=180, description="Data retention limit in days per DPDP Act")


class ConsentApprovalRequest(BaseModel):
    approved_fields: List[str] = Field(..., min_length=1, description="Subset of fields student explicitly authorises")
    otp: str = Field("123456", description="6-digit simulated OTP confirmation")


class ConsentRequestResponse(BaseModel):
    id: uuid.UUID
    student_id: uuid.UUID
    verifier_id: str
    verifier_org_name: str
    purpose: str
    purpose_category: str
    fields_requested: List[str]
    approved_fields: List[str]
    retention_days: int
    status: str
    token: str
    receipt_signature: Optional[str] = None
    expires_at: datetime
    approved_at: Optional[datetime] = None
    created_at: datetime


class ConsentedRecordResponse(BaseModel):
    is_valid: bool
    token: str
    verifier_id: str
    purpose: str
    student_data: Dict[str, Any]
    approved_fields: List[str]
    retention_expires_at: str
    receipt_signature: Optional[str] = None


class RegulatoryAccessRequest(BaseModel):
    apaar_id: str = Field(..., min_length=12, max_length=12)
    agency_name: str = Field(..., min_length=2, max_length=255)
    legal_basis: str = Field(..., min_length=3, max_length=150, description="Legal statutory authority, e.g. AICTE Act Sec 10(g)")
    reference_number: str = Field(..., min_length=2, max_length=100, description="Official requisition file/case number")
    justification: str = Field(..., min_length=10, description="Detailed lawful justification")
    requested_fields: List[str] = Field(default_factory=lambda: ["name", "institution", "program", "status"])


class RegulatoryAccessLogResponse(BaseModel):
    id: uuid.UUID
    actor_name: str
    agency_name: str
    legal_basis: str
    reference_number: str
    justification: str
    accessed_fields: List[str]
    created_at: datetime


class StudentAccessHistoryResponse(BaseModel):
    commercial_verifications: List[ConsentRequestResponse]
    regulatory_accesses: List[RegulatoryAccessLogResponse]


# ---------------------------------------------------------------------------
# Certificate Template & Degree Schemas
# ---------------------------------------------------------------------------

class CertificateTemplateResponse(BaseModel):
    id: str
    name: str
    description: str
    orientation: str
    layout_spec: Dict[str, Any]
    is_active: bool


class CertificateIssueRequest(BaseModel):
    enrolment_id: uuid.UUID
    template_id: str = "aicte_classic"
    mark_completed: bool = True
    cgpa: Optional[float] = None
    honors: Optional[str] = None


class CertificateBatchRequest(BaseModel):
    program_id: Optional[uuid.UUID] = None
    academic_year: Optional[str] = None
    institution_id: Optional[uuid.UUID] = None
    template_id: str = "aicte_classic"


class BulkCertificateTaskResponse(BaseModel):
    task_id: str
    total_records: int
    status: str
    download_url: Optional[str] = None
