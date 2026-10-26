"""Pydantic schemas for AICTE National and Institution Dashboards."""

from datetime import datetime
from typing import Any, Dict, List, Optional
import uuid
from pydantic import BaseModel, Field


class KpiStripResponse(BaseModel):
    """Aggregated national and tenant-scoped KPIs for executive strip."""
    institutions_reporting_pct: float = Field(..., description="Percentage of institutions reporting enrolments")
    total_enrolments: int = Field(..., description="Total active enrolled student count")
    intake_utilisation_pct: float = Field(..., description="Pan-India approved intake utilisation percentage")
    open_critical_alerts: int = Field(..., description="Active critical alerts requiring immediate intervention")
    duplicates_detected: int = Field(..., description="Total suspected cross-college or intra-college duplicate records")
    verified_records_pct: float = Field(..., description="Percentage of student records verified with DigiLocker/APAAR")
    total_institutions: int = Field(..., description="Total approved institutions")
    reporting_institutions: int = Field(..., description="Institutions with active enrolments submitted")
    total_approved_intake: int = Field(..., description="Sum of approved capacity across programs")


class StateChoroplethItem(BaseModel):
    """State-wise metric aggregation for vector choropleth map."""
    state_id: str
    state_code: str = Field(..., description="Two-letter ISO state code, e.g. MH, DL, KA")
    state_name: str
    intake_utilisation_pct: float
    violation_count: int
    risk_score: float = Field(..., ge=0.0, le=100.0)
    risk_level: str = Field(..., description="LOW, MEDIUM, HIGH, CRITICAL")
    institutions_count: int
    total_enrolments: int
    approved_intake: int


class StateChoroplethResponse(BaseModel):
    """Choropleth dataset across all states."""
    academic_year: str
    items: List[StateChoroplethItem]


class LeaderboardItem(BaseModel):
    """Institutional ranking item with risk telemetry."""
    id: str
    aicte_id: str
    name: str
    state_name: str
    state_code: str
    institution_type: str
    approved_intake: int
    enrolment_count: int
    utilisation_pct: float
    risk_score: float
    risk_level: str
    open_issues_count: int
    critical_issues_count: int
    top_contributing_factor: Optional[str] = None
    status: str


class LeaderboardResponse(BaseModel):
    """Paginated institutional leaderboard."""
    total: int
    page: int
    page_size: int
    total_pages: int
    items: List[LeaderboardItem]


class ProgramCapacityDetail(BaseModel):
    """Program-wise intake and enrolment bar breakdown."""
    id: str
    name: str
    branch: str
    level: str
    approved_intake: int
    regular_enrolment: int
    supernumerary_enrolment: int
    total_enrolment: int
    utilisation_pct: float
    has_overshoot: bool
    supernumerary_pct: float


class ValidationIssueDetail(BaseModel):
    """Validation issue for drill-down."""
    id: str
    rule_code: str
    severity: str
    message: str
    explanation: Dict[str, Any]
    status: str
    created_at: datetime


class TimelineEvent(BaseModel):
    """Chronological event for institution timeline."""
    id: str
    event_type: str  # BATCH_UPLOAD, ANOMALY_SCAN, AUDIT_ACTION, INTAKE_REVISION
    title: str
    description: str
    timestamp: datetime
    badge: Optional[str] = None


class AuditActivityItem(BaseModel):
    """Tamper-evident audit activity snippet."""
    id: str
    seq: int
    actor_id: str
    actor_role: str
    action: str
    entity_type: str
    timestamp: datetime


class InstitutionDrilldownResponse(BaseModel):
    """Comprehensive drilldown for a single institution."""
    id: str
    aicte_id: str
    name: str
    state_name: str
    state_code: str
    district: Optional[str] = None
    institution_type: str
    email: Optional[str] = None
    status: str
    approved_total_intake: int
    current_total_enrolment: int
    intake_utilisation_pct: float

    # ML Anomaly & Risk Profile
    risk_score: float
    risk_level: str
    anomaly_score: float
    contributing_factors: List[Dict[str, Any]]
    peer_comparison: Dict[str, Any]
    ghost_student_flags: Dict[str, Any]

    # Programs & Issues
    programs: List[ProgramCapacityDetail]
    open_issues: List[ValidationIssueDetail]
    timeline: List[TimelineEvent]
    recent_audit: List[AuditActivityItem]


class ProgramGaugeItem(BaseModel):
    """Gauge data for a single program in tenant view."""
    program_id: str
    name: str
    branch: str
    level: str
    approved_intake: int
    current_enrolment: int
    utilisation_pct: float
    status: str  # NORMAL, WARNING, CAPACITY_EXCEEDED


class FixNowIssueItem(BaseModel):
    """Actionable open issue with deep link."""
    issue_id: str
    rule_code: str
    severity: str
    category: str
    message: str
    affected_count: int
    fix_action: str
    deep_link: str


class BatchUploadSummary(BaseModel):
    """Upload pipeline status summary."""
    batch_id: Optional[str] = None
    file_name: Optional[str] = None
    status: str  # COMPLETED, PROCESSING, FAILED, NO_UPLOADS
    total_rows: int = 0
    valid_rows: int = 0
    invalid_rows: int = 0
    created_at: Optional[datetime] = None


class InstitutionTenantDashboardResponse(BaseModel):
    """Institution tenant dashboard operational telemetry."""
    institution_id: str
    institution_name: str
    aicte_id: str
    data_completeness_pct: float
    verification_pending_count: int
    total_enrolments: int
    approved_intake: int
    overall_utilisation_pct: float
    upload_summary: BatchUploadSummary
    program_gauges: List[ProgramGaugeItem]
    fix_now_issues: List[FixNowIssueItem]
    deadline_timestamp: datetime
    days_to_deadline: int
    compliance_status: str  # ON_TRACK, ACTION_REQUIRED, CRITICAL


class AlertItem(BaseModel):
    """Live telemetry alert item."""
    id: str
    type: str
    severity: str  # CRITICAL, HIGH, MEDIUM, LOW
    institution_id: Optional[str] = None
    institution_name: Optional[str] = None
    message: str
    status: str  # NEW, ASSIGNED, RESOLVED
    assigned_to: Optional[str] = None
    created_at: datetime


class AlertActionRequest(BaseModel):
    """Request payload to acknowledge, assign, or resolve an alert."""
    action: str = Field(..., description="ACKNOWLEDGE, ASSIGN, or RESOLVE")
    assigned_to: Optional[uuid.UUID] = None
    notes: Optional[str] = Field(None, max_length=1000)


class AlertActionResponse(BaseModel):
    """Response confirming workflow transition."""
    id: str
    status: str
    message: str
    updated_at: datetime
