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

from app.schemas.auth import (
    LoginRequest,
    LoginResponse,
    MfaVerifyRequest,
    MfaEnrollResponse,
    MfaConfirmRequest,
    RefreshTokenRequest,
    TokenResponse,
    LogoutRequest,
    ChangePasswordRequest,
    UserMeResponse,
    AuditLogResponse,
    AuditVerifyResponse,
)
from app.schemas.ingestion import (
    SingleStudentEnrolRequest,
    SingleStudentEnrolResponse,
    StudentEnrolmentUpdateRequest,
    ProgramIntakeDeclarationRequest,
    ProgramIntakeSummaryResponse,
    BatchSubmissionResponse,
    BatchDetailResponse,
    BatchErrorRow,
)

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
    "LoginRequest",
    "LoginResponse",
    "MfaVerifyRequest",
    "MfaEnrollResponse",
    "MfaConfirmRequest",
    "RefreshTokenRequest",
    "TokenResponse",
    "LogoutRequest",
    "ChangePasswordRequest",
    "UserMeResponse",
    "AuditLogResponse",
    "AuditVerifyResponse",
]
