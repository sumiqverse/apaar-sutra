"""Complete SQLAlchemy models registry for APAAR-Sutra."""

from app.models.base import (
    Base,
    TimestampMixin,
    SoftDeleteMixin,
    SessionLocal,
    AsyncSessionLocal,
    sync_engine,
    async_engine,
    get_sync_db,
)
from app.models.state import State
from app.models.institution import Institution
from app.models.program import Program
from app.models.student import Student
from app.models.enrolment import Enrolment, EnrolmentHistory
from app.models.batch import UploadBatch
from app.models.validation import ValidationRule, ValidationIssue
from app.models.rbac import (
    User,
    Role,
    Permission,
    UserRole,
    RolePermission,
    UserInstitution,
    RefreshToken,
    MfaSecret,
    ApiClient,
    PasswordHistory,
)
from app.models.audit import AuditLog
from app.models.credential import (
    ConsentRequest,
    VerificationLog,
    IssuedRecord,
    Alert,
    WebhookSubscription,
)
from app.models.ml import InstitutionRiskScore

__all__ = [
    "Base",
    "TimestampMixin",
    "SoftDeleteMixin",
    "SessionLocal",
    "AsyncSessionLocal",
    "sync_engine",
    "async_engine",
    "get_sync_db",
    "State",
    "Institution",
    "Program",
    "Student",
    "Enrolment",
    "EnrolmentHistory",
    "UploadBatch",
    "ValidationRule",
    "ValidationIssue",
    "User",
    "Role",
    "Permission",
    "UserRole",
    "RolePermission",
    "UserInstitution",
    "RefreshToken",
    "MfaSecret",
    "ApiClient",
    "PasswordHistory",
    "AuditLog",
    "ConsentRequest",
    "VerificationLog",
    "IssuedRecord",
    "Alert",
    "WebhookSubscription",
    "InstitutionRiskScore",
]
