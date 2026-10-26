"""Pydantic schemas for Validation Rules, Issues, and Explainability Endpoints."""

from datetime import datetime
from typing import Any, Dict, List, Optional
import uuid
from pydantic import BaseModel, ConfigDict, Field


class ValidationRuleResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    code: str
    name: str
    severity: str
    scope: str
    enabled: bool
    description: Optional[str] = None
    remediation_hint: Optional[str] = None
    params: Dict[str, Any] = Field(default_factory=dict)
    version: int
    created_at: datetime
    updated_at: datetime


class ValidationRuleUpdateRequest(BaseModel):
    enabled: Optional[bool] = None
    severity: Optional[str] = None
    params: Optional[Dict[str, Any]] = None
    description: Optional[str] = None
    remediation_hint: Optional[str] = None


class ValidationIssueResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    rule_code: str
    severity: str
    institution_id: uuid.UUID
    program_id: Optional[uuid.UUID] = None
    enrolment_id: Optional[uuid.UUID] = None
    batch_id: Optional[uuid.UUID] = None
    message: str
    explanation: Dict[str, Any] = Field(default_factory=dict)
    status: str
    created_at: datetime
    resolved_by: Optional[uuid.UUID] = None


class ValidationIssueStatusUpdateRequest(BaseModel):
    status: str  # OPEN, ACKNOWLEDGED, RESOLVED, FALSE_POSITIVE
    resolution_note: Optional[str] = None


class ValidationExplainResponse(BaseModel):
    issue_id: uuid.UUID
    rule_code: str
    rule_name: str
    severity: str
    regulatory_reference: str
    fields_involved: List[str]
    offending_values: Dict[str, Any]
    why_flagged: str
    remediation_steps: List[str]
    related_entities: Dict[str, Any] = Field(default_factory=dict)
