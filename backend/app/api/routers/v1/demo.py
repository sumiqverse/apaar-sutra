"""Demo Mode Router: Fast environment reset, role quick-login, and asset telemetry."""

import asyncio
from datetime import datetime, timezone
import hashlib
import time
from typing import Any, Dict, List, Optional
import uuid
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.api.deps import get_db
from app.core.config import settings
from app.core.jwt import create_access_token, create_refresh_token
from app.models.rbac import (
    Permission,
    RefreshToken,
    Role,
    User,
)
from app.services.seed_pipeline import run_full_seed_pipeline

router = APIRouter(prefix="/demo", tags=["Demo Mode & Sandbox"])


class QuickLoginRequest(BaseModel):
    role: str = Field(..., description="Role to login as: SUPER_ADMIN, INSTITUTION_ADMIN, VERIFIER, STUDENT, AICTE_OFFICER")


class ResetResponse(BaseModel):
    status: str
    message: str
    reset_duration_ms: float
    timestamp: str
    seeded_entities: Dict[str, Any]
    demo_accounts: List[Dict[str, str]]
    demo_assets: List[Dict[str, str]]


@router.get("/info", summary="Retrieve demo mode information, pre-configured roles, and assets")
async def get_demo_info() -> Dict[str, Any]:
    """Provides metadata, demo credentials, TOTP bypass codes, and prepared CSV assets."""
    return {
        "demo_mode": True,
        "totp_bypass_codes": ["000000", "123456"],
        "roles": [
            {
                "role": "SUPER_ADMIN",
                "email": "superadmin@aicte.gov.in",
                "password": settings.DEMO_SUPERADMIN_PASSWORD,
                "label": "AICTE Directorate / National Admin",
                "scope": "Pan-India National View, Global Telemetry, Risk Heatmap",
            },
            {
                "role": "INSTITUTION_ADMIN",
                "email": "director.iitm@aicte.gov.in",
                "password": settings.DEMO_INSTITUTION_PASSWORD,
                "label": "IITM Mumbai Registrar",
                "scope": "Institution Scoped (IITM Mumbai, Approved Intake: 120)",
            },
            {
                "role": "INSTITUTION_ADMIN",
                "email": "registrar.dtu@aicte.gov.in",
                "password": settings.DEMO_INSTITUTION_PASSWORD,
                "label": "DTU Delhi Registrar",
                "scope": "Institution Scoped (DTU Delhi, Approved Intake: 120)",
            },
            {
                "role": "AICTE_OFFICER",
                "email": "officer@aicte.gov.in",
                "password": "Officer@2026!",
                "label": "AICTE Regional Inspector",
                "scope": "Regional Audits, Investigation Queue, Anomaly Resolution",
            },
            {
                "role": "VERIFIER",
                "email": "verifier.tcs@tcs.com",
                "password": settings.DEMO_VERIFIER_PASSWORD,
                "label": "TCS Background Verifier",
                "scope": "Consent Request, Credential Verification, Tamper Audit",
            },
            {
                "role": "STUDENT",
                "email": "student.demo@aicte.gov.in",
                "password": settings.DEMO_STUDENT_PASSWORD,
                "label": "Student Credential Holder",
                "scope": "Personal APAAR Ledger, DPDP Consent Approvals, Digital Transcript",
            },
        ],
        "demo_assets": [
            {
                "name": "clean.csv",
                "path": "/demo-assets/clean.csv",
                "description": "60 valid records for 60 sanctioned intake. 100% Verhoeff checksum pass, 0 violations.",
            },
            {
                "name": "violation.csv",
                "path": "/demo-assets/violation.csv",
                "description": "150 records on 120 intake (30 overshoot) + 2 cross-institution duplicates (already in DTU Delhi).",
            },
            {
                "name": "tamper_sample.json",
                "path": "/demo-assets/tamper_sample.json",
                "description": "Ed25519-signed academic credential with instructions for single-byte tampering.",
            },
        ],
    }


@router.post("/quick-login", summary="One-click instantaneous demo login token generator")
async def quick_login(
    req: QuickLoginRequest,
    db: AsyncSession = Depends(get_db),
) -> Dict[str, Any]:
    """Generates an immediate JWT session for the requested demo role without manual form entry."""
    target_role = req.role.upper().strip()
    role_email_map = {
        "SUPER_ADMIN": "superadmin@aicte.gov.in",
        "INSTITUTION_ADMIN": "director.iitm@aicte.gov.in",
        "AICTE_OFFICER": "officer@aicte.gov.in",
        "VERIFIER": "verifier.tcs@tcs.com",
        "STUDENT": "student.demo@aicte.gov.in",
    }
    email = role_email_map.get(target_role)
    if not email:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Unsupported demo role: {target_role}. Supported: {list(role_email_map.keys())}",
        )

    stmt = (
        select(User)
        .options(
            selectinload(User.roles).selectinload(Role.permissions),
            selectinload(User.institutions),
        )
        .where(User.email == email)
    )
    res = await db.execute(stmt)
    user = res.scalar_one_or_none()

    if not user:
        # Auto-seed full demo data on-demand if database is fresh or unseeded
        await reset_demo_data(db)
        res = await db.execute(stmt)
        user = res.scalar_one_or_none()

    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Demo account {email} not found. Please click 'Reset Demo Data' first.",
        )

    role_names = [r.name for r in user.roles]
    permissions_set = set()
    for r in user.roles:
        for p in r.permissions:
            permissions_set.add(p.code)
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
    await db.commit()

    return {
        "access_token": access_token,
        "refresh_token": raw_refresh,
        "token_type": "bearer",
        "expires_in": 900,
        "user": {
            "id": str(user.id),
            "email": user.email,
            "full_name": user.full_name,
            "roles": role_names,
            "institution_ids": inst_ids,
        },
    }


@router.post("/reset", response_model=ResetResponse, summary="Reset database to full Phase 1 synthetic state")
async def reset_demo_data(
    db: AsyncSession = Depends(get_db),
) -> ResetResponse:
    """Restores the full Phase 1 synthetic dataset: 60 institutions, ~25,000 students,

    seed 42, injected issues, mock registry, preserved demo accounts, validation issues, and ML risk scores.
    """
    pipeline_res = await asyncio.to_thread(run_full_seed_pipeline)
    row_counts = pipeline_res.get("row_counts", {})
    duration_ms = round(pipeline_res.get("duration_seconds", 0.0) * 1000, 2)

    return ResetResponse(
        status="success",
        message=f"Full Phase 1 synthetic dataset ({row_counts.get('institutions', 60)} institutions, {row_counts.get('students', 25000):,} students) restored and validated in {duration_ms}ms.",
        reset_duration_ms=duration_ms,
        timestamp=datetime.now(timezone.utc).isoformat(),
        seeded_entities={
            "institutions_active": row_counts.get("institutions", 60),
            "programs_configured": row_counts.get("programs", 348),
            "baseline_students": row_counts.get("students", 25037),
            "total_enrolments": row_counts.get("enrolments", 25052),
            "validation_issues": row_counts.get("validation_issues", 124),
            "active_alerts": row_counts.get("alerts", 18),
            "risk_scores_computed": row_counts.get("risk_scores", 60),
            "verifiable_credentials": 1,
            "preapproved_consents": 1,
        },
        demo_accounts=[
            {"role": "SUPER_ADMIN", "email": "superadmin@aicte.gov.in", "password": settings.DEMO_SUPERADMIN_PASSWORD},
            {"role": "INSTITUTION_ADMIN", "email": "director.iitm@aicte.gov.in", "password": settings.DEMO_INSTITUTION_PASSWORD},
            {"role": "INSTITUTION_ADMIN", "email": "registrar.dtu@aicte.gov.in", "password": settings.DEMO_INSTITUTION_PASSWORD},
            {"role": "INSTITUTION_ADMIN", "email": "admin@iitb.ac.in", "password": "InstAdmin@2026"},
            {"role": "AICTE_OFFICER", "email": "officer@aicte.gov.in", "password": "Officer@2026!"},
            {"role": "AICTE_ANALYST", "email": "analyst@aicte.gov.in", "password": "Analyst@2026!"},
            {"role": "VERIFIER", "email": "verifier.tcs@tcs.com", "password": settings.DEMO_VERIFIER_PASSWORD},
            {"role": "STUDENT", "email": "student.demo@aicte.gov.in", "password": settings.DEMO_STUDENT_PASSWORD},
        ],
        demo_assets=[
            {"name": "clean.csv", "path": "/demo-assets/clean.csv", "records": "60 records (within 60 sanctioned)"},
            {"name": "violation.csv", "path": "/demo-assets/violation.csv", "records": "150 records on 120 intake + 2 cross-inst duplicates"},
            {"name": "tamper_sample.json", "path": "/demo-assets/tamper_sample.json", "purpose": "Tamper-proof signature validation demo"},
        ],
    )
