"""Authentication endpoints: Login, MFA, Token Rotation, Session Management, and Password Policy."""

from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
import uuid
from fastapi import APIRouter, Depends, Request
from sqlalchemy import desc, select, update
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.api.deps import CurrentUser, get_client_ip, get_current_user, get_db, get_request_id
from app.core.crypto import decrypt_field, encrypt_field
from app.core.exceptions import (
    ForbiddenException,
    TooManyRequestsException,
    UnauthorizedException,
    ValidationException,
)
from app.core.jwt import (
    create_access_token,
    create_mfa_temp_token,
    create_refresh_token,
    decode_token,
    hash_token,
)
from app.core.mfa import (
    generate_backup_codes,
    generate_totp_secret,
    get_provisioning_uri,
    verify_and_consume_backup_code,
    verify_totp_code,
)
from app.core.password import hash_password, validate_password_policy, verify_password
from app.core.rate_limit import (
    check_rate_limit,
    clear_login_failures,
    is_account_locked,
    register_login_failure,
)
from app.models.rbac import MfaSecret, PasswordHistory, RefreshToken, User
from app.schemas.auth import (
    ChangePasswordRequest,
    LoginRequest,
    LoginResponse,
    LogoutRequest,
    MfaConfirmRequest,
    MfaEnrollResponse,
    MfaVerifyRequest,
    RefreshTokenRequest,
    TokenResponse,
    UserMeResponse,
)
from app.services.audit_service import AuditService

router = APIRouter(prefix="/auth", tags=["Authentication & Session"])

PRIVILEGED_ROLES = {"SUPER_ADMIN", "AICTE_OFFICER", "INSTITUTION_ADMIN", "AUDITOR"}


@router.post("/login", response_model=LoginResponse, summary="Authenticate user with email and password")
async def login(
    req: LoginRequest,
    request: Request,
    db: AsyncSession = Depends(get_db),
) -> LoginResponse:
    """Authenticate credentials with Argon2id, rate limiting, and brute-force lockout."""
    client_ip = get_client_ip(request)
    req_id = get_request_id(request)

    # 1. IP-level rate limit: 5 attempts per minute
    if not check_rate_limit(f"ratelimit:login:ip:{client_ip}", limit=5, window_seconds=60):
        raise TooManyRequestsException(message="Too many login attempts. Please wait 1 minute before trying again.")

    # 2. Look up user by email
    stmt = (
        select(User)
        .options(
            selectinload(User.roles).selectinload(User.roles.property.mapper.class_.permissions),
            selectinload(User.institutions),
            selectinload(User.mfa_secret),
        )
        .where(User.email == req.email.lower().strip())
    )
    res = await db.execute(stmt)
    user = res.scalar_one_or_none()

    # 3. Account lockout check
    locked_remaining = is_account_locked(req.email, user.locked_until if user else None)
    if locked_remaining:
        await AuditService.log_event(
            session=db,
            actor_id=req.email,
            actor_role="ANONYMOUS",
            action="AUTH_LOGIN_LOCKED_ATTEMPT",
            entity_type="USER",
            entity_id=str(user.id) if user else "UNKNOWN",
            ip=client_ip,
            request_id=req_id,
            payload={"remaining_seconds": locked_remaining},
        )
        raise UnauthorizedException(
            message=f"Account is temporarily locked due to repeated failed attempts. Try again in {locked_remaining}s."
        )

    # Generic invalid credentials handler to prevent user enumeration
    if not user or not verify_password(req.password, user.password_hash):
        register_login_failure(req.email)
        if user:
            user.failed_login_attempts += 1
            if user.failed_login_attempts >= 5:
                user.locked_until = datetime.now(timezone.utc)
            await db.commit()

        await AuditService.log_event(
            session=db,
            actor_id=req.email,
            actor_role="ANONYMOUS",
            action="AUTH_LOGIN_FAILED",
            entity_type="USER",
            entity_id=str(user.id) if user else "UNKNOWN",
            ip=client_ip,
            request_id=req_id,
        )
        raise UnauthorizedException(message="Invalid email or password.")

    if not user.is_active:
        raise UnauthorizedException(message="Your account has been deactivated. Contact AICTE support.")

    # Successful password match: clear lockout counters
    clear_login_failures(user.email)
    user.failed_login_attempts = 0
    user.locked_until = None
    await db.commit()

    role_names = [r.name for r in user.roles]
    is_mfa_enabled = bool(user.mfa_secret and user.mfa_secret.is_enabled)
    is_privileged = bool(PRIVILEGED_ROLES.intersection(role_names))

    # Mandatory MFA enforcement: If privileged role has not enrolled MFA yet
    if is_privileged and not is_mfa_enabled:
        temp_token = create_mfa_temp_token(user.id)
        return LoginResponse(mfa_setup_required=True, temp_token=temp_token)

    # MFA prompt: If MFA is enabled on user
    if is_mfa_enabled:
        temp_token = create_mfa_temp_token(user.id)
        return LoginResponse(mfa_required=True, temp_token=temp_token)

    # Standard non-MFA login (e.g. regular Student/Operator if MFA unconfigured)
    permissions_set = set()
    for role in user.roles:
        for perm in role.permissions:
            permissions_set.add(perm.code)
    if "SUPER_ADMIN" in role_names:
        permissions_set.add("*:*")

    inst_ids = [str(inst.id) for inst in user.institutions]
    access_token = create_access_token(
        user_id=user.id,
        roles=role_names,
        institution_ids=inst_ids,
        permissions=list(permissions_set),
    )
    raw_refresh, refresh_hash, family_id, refresh_exp = create_refresh_token()

    db_refresh = RefreshToken(
        id=uuid.uuid4(),
        user_id=user.id,
        family_id=family_id,
        token_hash=refresh_hash,
        expires_at=refresh_exp,
    )
    db.add(db_refresh)

    await AuditService.log_event(
        session=db,
        actor_id=str(user.id),
        actor_role=",".join(role_names),
        action="AUTH_LOGIN_SUCCESS",
        entity_type="USER",
        entity_id=str(user.id),
        ip=client_ip,
        request_id=req_id,
    )
    await db.commit()

    return LoginResponse(
        access_token=access_token,
        refresh_token=raw_refresh,
        expires_in=900,
    )


@router.post("/mfa/verify", response_model=TokenResponse, summary="Verify 6-digit TOTP or backup code")
async def verify_mfa(
    req: MfaVerifyRequest,
    request: Request,
    db: AsyncSession = Depends(get_db),
) -> TokenResponse:
    """Validate temporary MFA token and TOTP or backup code, returning rotating access + refresh tokens."""
    client_ip = get_client_ip(request)
    req_id = get_request_id(request)

    payload = decode_token(req.temp_token)
    if payload.get("type") != "mfa_temp":
        raise UnauthorizedException(message="Invalid token type for MFA verification.")

    user_id = uuid.UUID(payload["sub"])
    stmt = (
        select(User)
        .options(
            selectinload(User.roles).selectinload(User.roles.property.mapper.class_.permissions),
            selectinload(User.institutions),
            selectinload(User.mfa_secret),
        )
        .where(User.id == user_id)
    )
    res = await db.execute(stmt)
    user = res.scalar_one_or_none()

    if not user or not user.mfa_secret:
        raise UnauthorizedException(message="MFA credential not found.")

    # 1. Try TOTP code verification
    totp_secret = decrypt_field(user.mfa_secret.secret_enc)
    is_valid = verify_totp_code(totp_secret, req.code)

    # 2. If TOTP fails, check single-use backup codes
    if not is_valid:
        is_backup_valid, remaining_codes = verify_and_consume_backup_code(
            req.code, user.mfa_secret.backup_codes
        )
        if is_backup_valid:
            user.mfa_secret.backup_codes = remaining_codes
            is_valid = True

    if not is_valid:
        await AuditService.log_event(
            session=db,
            actor_id=str(user.id),
            actor_role="ANONYMOUS",
            action="AUTH_MFA_FAILED",
            entity_type="USER",
            entity_id=str(user.id),
            ip=client_ip,
            request_id=req_id,
        )
        raise UnauthorizedException(message="Invalid TOTP or backup code.")

    role_names = [r.name for r in user.roles]
    permissions_set = set()
    for role in user.roles:
        for perm in role.permissions:
            permissions_set.add(perm.code)
    if "SUPER_ADMIN" in role_names:
        permissions_set.add("*:*")

    inst_ids = [str(inst.id) for inst in user.institutions]
    access_token = create_access_token(
        user_id=user.id,
        roles=role_names,
        institution_ids=inst_ids,
        permissions=list(permissions_set),
    )
    raw_refresh, refresh_hash, family_id, refresh_exp = create_refresh_token()

    db_refresh = RefreshToken(
        id=uuid.uuid4(),
        user_id=user.id,
        family_id=family_id,
        token_hash=refresh_hash,
        expires_at=refresh_exp,
    )
    db.add(db_refresh)

    await AuditService.log_event(
        session=db,
        actor_id=str(user.id),
        actor_role=",".join(role_names),
        action="AUTH_MFA_VERIFIED",
        entity_type="USER",
        entity_id=str(user.id),
        ip=client_ip,
        request_id=req_id,
    )
    await db.commit()

    return TokenResponse(
        access_token=access_token,
        refresh_token=raw_refresh,
        expires_in=900,
    )


@router.post("/mfa/enroll", response_model=MfaEnrollResponse, summary="Enrol in Multi-Factor Authentication")
async def enroll_mfa(
    current_user: CurrentUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> MfaEnrollResponse:
    """Generate TOTP secret, provisioning URI with QR code, and 8 single-use backup codes."""
    secret = generate_totp_secret()
    provisioning_uri = get_provisioning_uri(secret, current_user.email)
    plain_codes, hashed_codes = generate_backup_codes(count=8)

    encrypted_secret = encrypt_field(secret)

    # Upsert mfa_secrets record
    stmt = select(MfaSecret).where(MfaSecret.user_id == current_user.id)
    res = await db.execute(stmt)
    mfa_entry = res.scalar_one_or_none()

    if mfa_entry:
        mfa_entry.secret_enc = encrypted_secret
        mfa_entry.backup_codes = hashed_codes
        mfa_entry.is_enabled = False
    else:
        mfa_entry = MfaSecret(
            id=uuid.uuid4(),
            user_id=current_user.id,
            secret_enc=encrypted_secret,
            backup_codes=hashed_codes,
            is_enabled=False,
        )
        db.add(mfa_entry)

    await db.commit()
    return MfaEnrollResponse(
        secret=secret,
        provisioning_uri=provisioning_uri,
        backup_codes=plain_codes,
    )


@router.post("/mfa/confirm", summary="Confirm MFA enrolment with initial 6-digit TOTP code")
async def confirm_mfa(
    req: MfaConfirmRequest,
    current_user: CurrentUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> Dict[str, str]:
    """Verify first code from authenticator app to officially enable MFA on the account."""
    stmt = select(MfaSecret).where(MfaSecret.user_id == current_user.id)
    res = await db.execute(stmt)
    mfa_entry = res.scalar_one_or_none()

    if not mfa_entry:
        raise ValidationException(message="MFA has not been initiated. Call /mfa/enroll first.")

    totp_secret = decrypt_field(mfa_entry.secret_enc)
    if not verify_totp_code(totp_secret, req.code):
        raise ValidationException(message="Invalid code. Please ensure your authenticator app time is synced.")

    mfa_entry.is_enabled = True
    await db.commit()
    return {"status": "mfa_enabled", "message": "Multi-Factor Authentication successfully activated."}


@router.post("/refresh", response_model=TokenResponse, summary="Rotate refresh token and issue new access token")
async def refresh_tokens(
    req: RefreshTokenRequest,
    request: Request,
    db: AsyncSession = Depends(get_db),
) -> TokenResponse:
    """Rotate refresh token. Detects token reuse and immediately revokes entire token family."""
    client_ip = get_client_ip(request)
    req_id = get_request_id(request)
    provided_hash = hash_token(req.refresh_token)

    stmt = (
        select(RefreshToken)
        .options(selectinload(RefreshToken.user).selectinload(User.roles).selectinload(User.roles.property.mapper.class_.permissions))
        .options(selectinload(RefreshToken.user).selectinload(User.institutions))
        .where(RefreshToken.token_hash == provided_hash)
    )
    res = await db.execute(stmt)
    token_record = res.scalar_one_or_none()

    if not token_record:
        raise UnauthorizedException(message="Invalid refresh token.")

    # REPLAY ATTACK DETECTION: Token was already revoked!
    if token_record.revoked_at is not None:
        # Revoke the entire token family immediately
        family_stmt = (
            update(RefreshToken)
            .where(RefreshToken.family_id == token_record.family_id)
            .values(revoked_at=datetime.now(timezone.utc))
        )
        await db.execute(family_stmt)
        await AuditService.log_event(
            session=db,
            actor_id=str(token_record.user_id),
            actor_role="SECURITY_ALERT",
            action="AUTH_TOKEN_REPLAY_DETECTED",
            entity_type="REFRESH_TOKEN_FAMILY",
            entity_id=str(token_record.family_id),
            ip=client_ip,
            request_id=req_id,
            payload={"reused_token_id": str(token_record.id)},
        )
        await db.commit()
        raise UnauthorizedException(
            message="Token reuse detected: An old refresh token was presented. All active sessions in this family have been terminated."
        )

    # Check expiration
    now_utc = datetime.now(timezone.utc)
    token_exp = token_record.expires_at
    if token_exp.tzinfo is None:
        token_exp = token_exp.replace(tzinfo=timezone.utc)
    if token_exp < now_utc:
        raise UnauthorizedException(message="Refresh token has expired. Please log in again.")

    user = token_record.user
    if not user.is_active:
        raise UnauthorizedException(message="User account is deactivated.")

    # Mark old token as revoked
    token_record.revoked_at = now_utc

    # Issue new rotating refresh token in the SAME family
    new_raw_refresh, new_refresh_hash, _, new_refresh_exp = create_refresh_token(family_id=token_record.family_id)
    new_db_refresh = RefreshToken(
        id=uuid.uuid4(),
        user_id=user.id,
        family_id=token_record.family_id,
        token_hash=new_refresh_hash,
        expires_at=new_refresh_exp,
    )
    db.add(new_db_refresh)

    role_names = [r.name for r in user.roles]
    permissions_set = set()
    for role in user.roles:
        for perm in role.permissions:
            permissions_set.add(perm.code)
    if "SUPER_ADMIN" in role_names:
        permissions_set.add("*:*")

    inst_ids = [str(inst.id) for inst in user.institutions]
    new_access_token = create_access_token(
        user_id=user.id,
        roles=role_names,
        institution_ids=inst_ids,
        permissions=list(permissions_set),
    )

    await db.commit()
    return TokenResponse(
        access_token=new_access_token,
        refresh_token=new_raw_refresh,
        expires_in=900,
    )


@router.post("/logout", summary="Revoke current refresh token")
async def logout(
    req: LogoutRequest,
    db: AsyncSession = Depends(get_db),
) -> Dict[str, str]:
    """Revoke provided refresh token on logout."""
    if req.refresh_token:
        h = hash_token(req.refresh_token)
        stmt = (
            update(RefreshToken)
            .where(RefreshToken.token_hash == h)
            .values(revoked_at=datetime.now(timezone.utc))
        )
        await db.execute(stmt)
        await db.commit()
    return {"status": "logged_out", "message": "Session terminated successfully."}


@router.post("/logout-all", summary="Revoke all active sessions for current user")
async def logout_all(
    current_user: CurrentUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> Dict[str, str]:
    """Invalidate all active refresh tokens for the authenticated user across all devices."""
    stmt = (
        update(RefreshToken)
        .where(RefreshToken.user_id == current_user.id, RefreshToken.revoked_at == None)
        .values(revoked_at=datetime.now(timezone.utc))
    )
    await db.execute(stmt)
    await db.commit()
    return {"status": "all_sessions_revoked", "message": "All active sessions have been terminated."}


@router.get("/me", response_model=UserMeResponse, summary="Get current authenticated user profile")
async def get_me(current_user: CurrentUser = Depends(get_current_user)) -> UserMeResponse:
    """Return identity, roles, permissions, and institution scope for caller."""
    return UserMeResponse(
        id=current_user.id,
        email=current_user.email,
        full_name=current_user.full_name,
        phone=current_user.phone,
        roles=current_user.roles,
        permissions=current_user.permissions,
        institution_ids=current_user.institution_ids,
        is_mfa_enabled=current_user.is_mfa_enabled,
    )


@router.post("/change-password", summary="Change account password with policy enforcement")
async def change_password(
    req: ChangePasswordRequest,
    current_user: CurrentUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> Dict[str, str]:
    """Update password enforcing minimum length, breach lists, and no reuse of last 3 passwords."""
    stmt = (
        select(User)
        .options(selectinload(User.password_history))
        .where(User.id == current_user.id)
    )
    res = await db.execute(stmt)
    user = res.scalar_one_or_none()

    if not user or not verify_password(req.current_password, user.password_hash):
        raise UnauthorizedException(message="Current password is incorrect.")

    # Retrieve last 3 password hashes
    history_hashes = [user.password_hash] + [h.password_hash for h in user.password_history]
    validate_password_policy(req.new_password, history_hashes)

    # Archive current password in password_histories
    history_record = PasswordHistory(
        id=uuid.uuid4(),
        user_id=user.id,
        password_hash=user.password_hash,
    )
    db.add(history_record)

    # Update new password hash
    user.password_hash = hash_password(req.new_password)

    # Invalidate all existing sessions
    await db.execute(
        update(RefreshToken)
        .where(RefreshToken.user_id == user.id)
        .values(revoked_at=datetime.now(timezone.utc))
    )
    await db.commit()

    return {"status": "password_updated", "message": "Password updated successfully. Please re-authenticate."}
