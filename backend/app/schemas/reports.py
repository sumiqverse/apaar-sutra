"""Pydantic v2 schemas for Statutory Reports and Verification Hashes."""

from datetime import datetime
from typing import Any, Dict, List, Literal, Optional
import uuid
from pydantic import BaseModel, Field

ReportType = Literal[
    "state_wise_intake",
    "overshoot_institutions",
    "supernumerary_distribution",
    "duplicate_register",
    "institution_risk_ranking",
    "data_completeness",
    "accreditation_support",
    "yoy_trend",
]

ReportFormat = Literal["PDF", "XLSX", "CSV"]


class ReportGenerateRequest(BaseModel):
    report_type: ReportType = Field(..., description="Statutory report type from catalog (a-h)")
    format: ReportFormat = Field("PDF", description="Export format: PDF, XLSX, or CSV")
    academic_year: str = Field("2025-26", description="Academic year filter, e.g. '2025-26'")
    state: Optional[str] = Field(None, description="Optional State/UT filter")
    institution_id: Optional[uuid.UUID] = Field(None, description="Optional institution scoping")


class GeneratedReportResponse(BaseModel):
    id: uuid.UUID
    report_type: str
    title: str
    format: str
    institution_id: Optional[uuid.UUID] = None
    filters: Dict[str, Any] = Field(default_factory=dict)
    generated_by: str
    row_count: int
    verification_hash: str
    status: str
    download_url: str
    created_at: datetime


class ReportVerificationResponse(BaseModel):
    is_authentic: bool
    report_id: Optional[str] = None
    report_type: Optional[str] = None
    title: Optional[str] = None
    generated_by: Optional[str] = None
    row_count: Optional[int] = None
    created_at: Optional[str] = None
    verification_hash: str
    message: str


class ReportCatalogItem(BaseModel):
    report_type: str
    code: str
    title: str
    description: str
    supported_formats: List[str]
    is_statutory: bool = True
