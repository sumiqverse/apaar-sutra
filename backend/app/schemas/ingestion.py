"""Pydantic v2 schemas for Single Entry, Bulk Ingestion, and Intake Declarations."""

from datetime import date, datetime
from typing import Any, Dict, List, Literal, Optional, Union
import uuid
from pydantic import BaseModel, ConfigDict, Field, field_validator


class SingleStudentEnrolRequest(BaseModel):
    """Full 21-field specification for single student enrollment."""

    # 1. Identity & Credentials
    apaar_id: str = Field(..., min_length=12, max_length=16, description="12-digit APAAR ID (Hindi digits allowed)")
    student_ref_id: str = Field(..., min_length=1, max_length=100, description="College roll number / admission registration")
    name: str = Field(..., min_length=1, max_length=150, description="Full student legal name")
    dob: date = Field(..., description="Date of birth (YYYY-MM-DD)")
    gender: Literal["MALE", "FEMALE", "OTHER"] = Field(..., description="Gender: MALE, FEMALE, OTHER")
    parent_name: Optional[str] = Field(None, max_length=150, description="Parent or Guardian name")
    contact: Optional[Dict[str, Any]] = Field(default_factory=dict, description="Email, phone, address details")

    # 2. Academic Program Link
    program_id: Optional[uuid.UUID] = Field(None, description="UUID of enrolled academic program")
    program_name: Optional[str] = Field(None, description="Name of program if program_id not known")
    branch: Optional[str] = Field(None, description="Branch/Specialization if program_id not known")
    academic_year: str = Field("2025-26", pattern=r"^\d{4}-\d{2}$", description="Academic Year format YYYY-YY (e.g. 2025-26)")

    # 3. Categorization & Quota Rules
    admission_category: Literal["GEN", "EWS", "OBC", "SC", "ST", "PWD", "OTHER"] = Field(
        "GEN", description="Category: GEN, EWS, OBC, SC, ST, PWD, OTHER"
    )
    quota_type: Literal["REGULAR", "SUPERNUMERARY", "NRI", "OCI", "FN", "TFW", "OTHER"] = Field(
        "REGULAR", description="Admission quota: REGULAR, SUPERNUMERARY, NRI, OCI, FN, TFW, OTHER"
    )

    # 4. International / Special Status
    is_nri: bool = Field(False, description="NRI applicant flag")
    sponsor_details: Optional[Dict[str, Any]] = Field(None, description="Sponsorship metadata if NRI/Sponsored")
    oci_status: bool = Field(False, description="Overseas Citizen of India status")
    is_foreign_national: bool = Field(False, description="Foreign National student flag")
    nationality: str = Field("INDIAN", max_length=100, description="Nationality (default INDIAN)")

    # 5. Admission State
    admission_date: date = Field(default_factory=date.today, description="Date of admission")
    status: Literal["ACTIVE", "WITHDRAWN", "COMPLETED"] = Field("ACTIVE", description="Enrolment status")

    @field_validator("name", "parent_name", mode="before")
    @classmethod
    def clean_name(cls, v: Optional[str]) -> Optional[str]:
        if v is not None:
            return " ".join(str(v).strip().split())
        return v


class SingleStudentEnrolResponse(BaseModel):
    """Enrolment confirmation response."""
    student_id: uuid.UUID
    enrolment_id: uuid.UUID
    apaar_id: str
    masked_apaar_id: str
    apaar_status: str  # VERIFIED, PENDING, MISMATCH, NOT_FOUND
    status: str
    name_match_score: int
    dob_match: bool
    verification_reason: Optional[str] = None
    created_at: datetime


class StudentEnrolmentUpdateRequest(BaseModel):
    """Payload for updating student enrolment attributes with audit diff tracking."""
    student_ref_id: Optional[str] = None
    name: Optional[str] = None
    dob: Optional[date] = None
    parent_name: Optional[str] = None
    contact: Optional[Dict[str, Any]] = None
    admission_category: Optional[Literal["GEN", "EWS", "OBC", "SC", "ST", "PWD", "OTHER"]] = None
    quota_type: Optional[Literal["REGULAR", "SUPERNUMERARY", "NRI", "OCI", "FN", "TFW", "OTHER"]] = None
    is_nri: Optional[bool] = None
    sponsor_details: Optional[Dict[str, Any]] = None
    status: Optional[Literal["ACTIVE", "WITHDRAWN", "COMPLETED"]] = None


class ProgramIntakeDeclarationRequest(BaseModel):
    """Institution intake and quota declaration."""
    program_id: Optional[uuid.UUID] = None
    program_name: Optional[str] = None
    level: str = Field("UG", description="DIPLOMA, UG, PG, PGDM, PHD")
    branch: str = Field(..., description="Branch/Department")
    academic_year: str = Field(..., pattern=r"^\d{4}-\d{2}$")
    approved_intake: int = Field(..., ge=1, description="AICTE approved intake")
    supernumerary_seats: int = Field(0, ge=0, description="Declared supernumerary seats")
    supernumerary_cap_pct: float = Field(15.0, ge=0.0, le=100.0, description="Cap percentage (default 15%)")
    declared_enrolment: Optional[int] = Field(None, ge=0, description="Institution declared actual enrolment")


class ProgramIntakeSummaryResponse(BaseModel):
    """Summary comparing approved intake vs actual enrolled students."""
    program_id: uuid.UUID
    program_name: str
    level: str
    branch: str
    academic_year: str
    approved_intake: int
    supernumerary_seats: int
    supernumerary_cap_pct: float
    actual_enrolment: int
    declared_enrolment: Optional[int] = None
    capacity_status: str  # WITHIN_CAPACITY, WARNING_NEAR_CAPACITY, CAPACITY_EXCEEDED
    utilization_pct: float


class BatchSubmissionResponse(BaseModel):
    batch_id: uuid.UUID
    status: str
    filename: str
    file_hash: str
    message: str
    warning: Optional[str] = None


class BatchDetailResponse(BaseModel):
    id: uuid.UUID
    institution_id: uuid.UUID
    filename: str
    file_hash: str
    source: str
    status: str  # PENDING, PROCESSING, COMPLETED, FAILED
    total_rows: int
    processed_rows: int
    accepted_rows: int
    warning_rows: int
    rejected_rows: int
    started_at: Optional[datetime]
    finished_at: Optional[datetime]
    created_at: datetime


class BatchErrorRow(BaseModel):
    row_number: int
    column: Optional[str] = None
    value: Optional[str] = None
    error_code: str
    reason: str
    fix_hint: str
