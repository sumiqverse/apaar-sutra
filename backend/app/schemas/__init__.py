"""Schemas module exports."""

from app.schemas.common import (
    ErrorDetail,
    ErrorEnvelope,
    HealthStatus,
    ComponentHealth,
    ReadyStatus,
    PaginationParams,
    PaginatedResponse,
)
from app.schemas.student import StudentBase, StudentCreate, StudentResponse, AcademicRecordBase, AcademicRecordResponse
from app.schemas.verification import VerificationRequest, VerificationResult

__all__ = [
    "ErrorDetail",
    "ErrorEnvelope",
    "HealthStatus",
    "ComponentHealth",
    "ReadyStatus",
    "PaginationParams",
    "PaginatedResponse",
    "StudentBase",
    "StudentCreate",
    "StudentResponse",
    "AcademicRecordBase",
    "AcademicRecordResponse",
    "VerificationRequest",
    "VerificationResult",
]
