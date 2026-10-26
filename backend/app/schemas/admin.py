"""Pydantic v2 schemas for Super Admin Console, Rules, System Health, and Policy Settings."""

from datetime import datetime
from typing import Any, Dict, List, Optional
import uuid
from pydantic import BaseModel, Field


# ---------------------------------------------------------------------------
# Rule Configuration & Thresholds
# ---------------------------------------------------------------------------

class RuleUpdateRequest(BaseModel):
    enabled: bool = Field(..., description="Enable or disable validation rule execution")
    severity: str = Field("ERROR", description="CRITICAL, ERROR, WARNING, INFO")
    params: Dict[str, Any] = Field(default_factory=dict, description="Rule parameters, e.g. thresholds, tolerance")


class RuleConfigResponse(BaseModel):
    id: uuid.UUID
    code: str
    name: str
    severity: str
    scope: str
    enabled: bool
    description: Optional[str] = None
    params: Dict[str, Any]
    version: int
    updated_at: datetime


# ---------------------------------------------------------------------------
# Institution Management
# ---------------------------------------------------------------------------

class AdminInstitutionCreate(BaseModel):
    name: str = Field(..., min_length=3, max_length=255)
    aicte_id: str = Field(..., min_length=3, max_length=50)
    state: str = Field(..., min_length=2, max_length=100)
    institution_type: str = Field("GOVERNMENT", description="GOVERNMENT, PRIVATE, AIDED, DEEMED, UNIVERSITY")
    approved_intake: int = Field(600, ge=10, le=100000)


class AdminInstitutionUpdate(BaseModel):
    name: Optional[str] = None
    state: Optional[str] = None
    is_active: Optional[bool] = None
    approved_intake: Optional[int] = None


# ---------------------------------------------------------------------------
# System Telemetry & Operational Policies
# ---------------------------------------------------------------------------

class SystemHealthResponse(BaseModel):
    status: str
    redis_connected: bool
    queue_depth: int
    failed_jobs_count: int
    last_nightly_scan: Optional[str] = None
    db_size_mb: float
    ml_model_version: str
    active_institutions: int
    total_enrolments: int
    uptime_seconds: float


class PolicySettingRequest(BaseModel):
    id: str = Field(..., description="Setting ID, e.g. quota_intake_rules or admission_deadline")
    value: Dict[str, Any] = Field(..., description="JSON policy payload")
    description: str = Field(..., max_length=255)


class PolicySettingResponse(BaseModel):
    id: str
    value: Dict[str, Any]
    description: str
    updated_at: datetime
    updated_by: Optional[str] = None


# ---------------------------------------------------------------------------
# Webhook Administration & Delivery Logs
# ---------------------------------------------------------------------------

class WebhookSubscriptionCreate(BaseModel):
    institution_id: uuid.UUID
    url: str = Field(..., max_length=500)
    events: List[str] = Field(default=["batch.completed", "alert.created", "record.revoked", "consent.updated"])
    secret: str = Field(..., min_length=16, description="Shared secret for HMAC-SHA256 signature generation")


class WebhookSubscriptionResponse(BaseModel):
    id: uuid.UUID
    institution_id: uuid.UUID
    url: str
    events: List[str]
    is_active: bool
    created_at: datetime


class WebhookDeliveryLogResponse(BaseModel):
    id: uuid.UUID
    subscription_id: uuid.UUID
    event_type: str
    status: str  # SUCCESS, RETRYING, DEAD_LETTER
    status_code: Optional[int] = None
    response_body: Optional[str] = None
    attempt_count: int
    next_retry_at: Optional[datetime] = None
    created_at: datetime
