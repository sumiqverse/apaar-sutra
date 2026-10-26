"""Pydantic v2 schemas for authentication, authorization, and audit queries."""

from datetime import datetime
from typing import Any, Dict, List, Optional
import uuid
from pydantic import BaseModel, ConfigDict, EmailStr, Field


class LoginRequest(BaseModel):
    email: EmailStr = Field(..., description="User's organizational email address")
    password: str = Field(..., min_length=1, description="Account password")


class LoginResponse(BaseModel):
    access_token: Optional[str] = None
    refresh_token: Optional[str] = None
    token_type: str = "bearer"
    expires_in: int = 900
    mfa_required: bool = False
    mfa_setup_required: bool = False
    temp_token: Optional[str] = None


class MfaVerifyRequest(BaseModel):
    temp_token: str = Field(..., description="Short-lived temporary token from login step")
    code: str = Field(..., description="6-digit TOTP code or single-use backup code")


class MfaEnrollResponse(BaseModel):
    secret: str
    provisioning_uri: str
    backup_codes: List[str]


class MfaConfirmRequest(BaseModel):
    code: str = Field(..., min_length=6, max_length=6, description="6-digit TOTP code from authenticator app")


class RefreshTokenRequest(BaseModel):
    refresh_token: str = Field(..., description="Active rotating refresh token")


class TokenResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    expires_in: int = 900


class LogoutRequest(BaseModel):
    refresh_token: Optional[str] = None


class ChangePasswordRequest(BaseModel):
    current_password: str = Field(..., description="Existing account password")
    new_password: str = Field(..., min_length=12, description="New strong password meeting policy")


class UserMeResponse(BaseModel):
    id: uuid.UUID
    email: str
    full_name: str
    phone: Optional[str] = None
    roles: List[str]
    permissions: List[str]
    institution_ids: List[uuid.UUID]
    is_mfa_enabled: bool

    model_config = ConfigDict(from_attributes=True)


class AuditLogResponse(BaseModel):
    id: uuid.UUID
    seq: int
    actor_id: str
    actor_role: str
    action: str
    entity_type: str
    entity_id: str
    ip: str
    request_id: str
    payload: Optional[Dict[str, Any]] = None
    prev_hash: Optional[str] = None
    hash: str
    timestamp: datetime

    model_config = ConfigDict(from_attributes=True)


class AuditVerifyResponse(BaseModel):
    valid: bool
    checked: int
    first_broken_seq: Optional[int] = None
    reason: Optional[str] = None
