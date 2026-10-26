"""Pydantic schemas for ML intelligence layer and anomaly endpoints."""

from datetime import datetime
from typing import Any, Dict, List, Optional
import uuid
from pydantic import BaseModel, Field


class ContributingFactorSchema(BaseModel):
    feature: str
    institution_value: float
    peer_median: float
    deviation_pct: float
    z_score: float
    plain_english: str


class InstitutionRiskItem(BaseModel):
    id: uuid.UUID
    institution_id: uuid.UUID
    aicte_id: str
    name: str
    institution_type: str
    state_id: Optional[uuid.UUID] = None
    state_code: Optional[str] = None
    academic_year: str
    risk_score: float
    risk_level: str
    anomaly_score: float
    top_factors: List[str]
    metrics: Dict[str, float]
    model_version: str
    created_at: datetime


class InstitutionRiskListResponse(BaseModel):
    items: List[InstitutionRiskItem]
    total_items: int
    page: int
    page_size: int
    total_pages: int


class InstitutionExplainResponse(BaseModel):
    institution_id: uuid.UUID
    aicte_id: str
    name: str
    academic_year: str
    risk_score: float
    risk_level: str
    anomaly_score: float
    contributing_factors: List[ContributingFactorSchema]
    metrics: Dict[str, float]
    peer_comparison: Dict[str, Any]
    ghost_student_summary: Dict[str, Any]
    model_version: str
    assessed_at: datetime


class FuzzyCandidateRecord(BaseModel):
    id: Optional[str] = None
    name: str
    dob: Optional[str] = None
    apaar_id: Optional[str] = None
    institution_id: Optional[str] = None


class FuzzyDedupRequest(BaseModel):
    institution_id: Optional[uuid.UUID] = None
    similarity_threshold: float = Field(default=85.0, ge=50.0, le=100.0)
    records: Optional[List[FuzzyCandidateRecord]] = None


class FuzzyDedupMatch(BaseModel):
    student_a_id: str
    student_b_id: str
    student_a_name: str
    student_b_name: str
    dob_year: str
    phonetic_block: str
    similarity_score: float
    apaar_a: Optional[str] = None
    apaar_b: Optional[str] = None
    institution_a: Optional[str] = None
    institution_b: Optional[str] = None


class FuzzyDedupResponse(BaseModel):
    total_candidates: int
    duplicate_pairs_found: int
    matches: List[FuzzyDedupMatch]


class GhostStudentResponse(BaseModel):
    institution_id: str
    heuristic_risk_score: float
    suspect_students_count: int
    suspect_students_ratio: float
    burst_admission_clusters: List[Dict[str, Any]]
    sequential_apaar_runs: List[Dict[str, Any]]
    repeating_demographic_clusters: List[Dict[str, Any]]
    has_ghost_indicators: bool


class RetrainResponse(BaseModel):
    status: str
    model_version: str
    institutions_scored: int
    high_risk_count: int
    message: str
