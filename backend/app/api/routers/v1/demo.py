"""Demo Mode Router: Fast environment reset, role quick-login, and asset telemetry."""

from datetime import date, datetime, timezone
import hashlib
import time
from typing import Any, Dict, List, Optional
import uuid
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.api.deps import get_db
from app.core.config import settings
from app.core.crypto import compute_blind_index
from app.core.jwt import create_access_token, create_refresh_token
from app.core.password import hash_password
from app.core.signing import sign_credential
from app.models.base import Base
from app.models.credential import (
    Alert,
    ConsentRequest,
    GeneratedReport,
    IssuedRecord,
    VerificationLog,
    VerifierOrg,
)
from app.models.enrolment import Enrolment, EnrolmentHistory
from app.models.institution import Institution
from app.models.ml import InstitutionRiskScore
from app.models.program import Program
from app.models.rbac import (
    MfaSecret,
    Permission,
    RefreshToken,
    Role,
    RolePermission,
    User,
    UserInstitution,
    UserRole,
)
from app.models.state import State
from app.models.student import Student
from app.models.batch import UploadBatch
from app.models.validation import ValidationIssue

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


@router.post("/reset", response_model=ResetResponse, summary="Reset database to a known baseline state in under 5 seconds")
async def reset_demo_data(
    db: AsyncSession = Depends(get_db),
) -> ResetResponse:
    """Wipes transient transactional data, re-seeds baseline institutions, programs, demo accounts,

    and dual-enrolment references for live demonstration.
    """
    start_time = time.time()

    # 1. Truncate dynamic transactional tables in safe dependency order
    await db.execute(delete(ValidationIssue))
    await db.execute(delete(Alert))
    await db.execute(delete(IssuedRecord))
    await db.execute(delete(ConsentRequest))
    await db.execute(delete(VerificationLog))
    await db.execute(delete(GeneratedReport))
    await db.execute(delete(InstitutionRiskScore))
    await db.execute(delete(EnrolmentHistory))
    await db.execute(delete(Enrolment))
    await db.execute(delete(UploadBatch))
    await db.commit()

    # 2. Ensure States exist
    states_def = [
        ("MH", "Maharashtra"),
        ("DL", "Delhi"),
        ("KA", "Karnataka"),
        ("TN", "Tamil Nadu"),
    ]
    state_map: Dict[str, State] = {}
    for code, name in states_def:
        stmt = select(State).where(State.code == code)
        res = await db.execute(stmt)
        st = res.scalar_one_or_none()
        if not st:
            st = State(id=uuid.uuid4(), code=code, name=name)
            db.add(st)
            await db.flush()
        state_map[code] = st

    # 3. Ensure Institutions exist
    # IITM Mumbai: Sanctioned Intake 120
    # DTU Delhi: Sanctioned Intake 120
    # PICT Pune: Sanctioned Intake 180
    inst_defs = [
        {
            "aicte_id": "1-100234901",
            "name": "Indian Institute of Technology & Management (IITM)",
            "state_code": "MH",
            "district": "Mumbai Suburban",
            "intake": 120,
            "email": "director.iitm@aicte.gov.in",
        },
        {
            "aicte_id": "1-100234902",
            "name": "Delhi Technological University (DTU)",
            "state_code": "DL",
            "district": "North Delhi",
            "intake": 120,
            "email": "registrar.dtu@aicte.gov.in",
        },
        {
            "aicte_id": "1-100234903",
            "name": "Pune Institute of Computer Technology (PICT)",
            "state_code": "MH",
            "district": "Pune",
            "intake": 180,
            "email": "records.pict@aicte.gov.in",
        },
    ]

    inst_map: Dict[str, Institution] = {}
    for idef in inst_defs:
        stmt = select(Institution).where(Institution.aicte_id == idef["aicte_id"])
        res = await db.execute(stmt)
        inst = res.scalar_one_or_none()
        if not inst:
            inst = Institution(
                id=uuid.uuid4(),
                aicte_id=idef["aicte_id"],
                name=idef["name"],
                state_id=state_map[idef["state_code"]].id,
                district=idef["district"],
                approved_total_intake=idef["intake"],
                institution_type="AFFILIATED",
                status="ACTIVE",
                email=idef["email"],
            )
            db.add(inst)
            await db.flush()
        else:
            inst.approved_total_intake = idef["intake"]
            inst.name = idef["name"]
            inst.email = idef["email"]
            inst.status = "ACTIVE"
        inst_map[idef["aicte_id"]] = inst

    # 4. Ensure Programs exist with approved intake of 120
    # Both IITM and DTU get B.Tech CSE with intake 120
    prog_map: Dict[str, Program] = {}
    for aicte_id in ["1-100234901", "1-100234902"]:
        inst = inst_map[aicte_id]
        stmt = select(Program).where(
            (Program.institution_id == inst.id) & (Program.name == "B.Tech Computer Science & Engineering")
        )
        res = await db.execute(stmt)
        prog = res.scalar_one_or_none()
        if not prog:
            prog = Program(
                id=uuid.uuid4(),
                institution_id=inst.id,
                name="B.Tech Computer Science & Engineering",
                level="UG",
                branch="Computer Science & Engineering",
                academic_year="2025-26",
                approved_intake=120,
                supernumerary_seats=18,
                duration_years=4,
            )
            db.add(prog)
            await db.flush()
        else:
            prog.approved_intake = 120
        prog_map[aicte_id] = prog

    # 5. Ensure Roles & Permissions
    all_roles = [
        "SUPER_ADMIN",
        "AICTE_OFFICER",
        "AICTE_ANALYST",
        "INSTITUTION_ADMIN",
        "INSTITUTION_OPERATOR",
        "VERIFIER",
        "AUDITOR",
        "STUDENT",
    ]
    role_map: Dict[str, Role] = {}
    for r_name in all_roles:
        stmt = select(Role).where(Role.name == r_name)
        res = await db.execute(stmt)
        r = res.scalar_one_or_none()
        if not r:
            r = Role(id=uuid.uuid4(), name=r_name, description=f"{r_name} role")
            db.add(r)
            await db.flush()
        role_map[r_name] = r

    # Permissions
    perm_codes = [
        "students:read",
        "students:read_full",
        "students:write",
        "batches:upload",
        "batches:read",
        "rules:manage",
        "rules:read",
        "audit:read",
        "audit:verify",
        "reports:generate",
        "verification:request",
        "verification:verify",
        "users:manage",
        "users:read",
    ]
    perm_map: Dict[str, Permission] = {}
    for p_code in perm_codes:
        stmt = select(Permission).where(Permission.code == p_code)
        res = await db.execute(stmt)
        p = res.scalar_one_or_none()
        if not p:
            p = Permission(id=uuid.uuid4(), code=p_code, description=p_code)
            db.add(p)
            await db.flush()
        perm_map[p_code] = p

    # Assign all permissions to SUPER_ADMIN (no id column on RolePermission)
    super_admin_role = role_map["SUPER_ADMIN"]
    stmt = select(RolePermission).where(RolePermission.role_id == super_admin_role.id)
    existing_rps = (await db.execute(stmt)).scalars().all()
    existing_pids = {rp.permission_id for rp in existing_rps}
    for p_code, p in perm_map.items():
        if p.id not in existing_pids:
            db.add(RolePermission(role_id=super_admin_role.id, permission_id=p.id))

    # 6. Ensure Demo Users exist with correct passwords & roles
    demo_users_spec = [
        (
            "superadmin@aicte.gov.in",
            settings.DEMO_SUPERADMIN_PASSWORD,
            "AICTE National Director",
            "SUPER_ADMIN",
            None,
        ),
        (
            "director.iitm@aicte.gov.in",
            settings.DEMO_INSTITUTION_PASSWORD,
            "IITM Mumbai Registrar",
            "INSTITUTION_ADMIN",
            inst_map["1-100234901"].id,
        ),
        (
            "registrar.dtu@aicte.gov.in",
            settings.DEMO_INSTITUTION_PASSWORD,
            "DTU Delhi Registrar",
            "INSTITUTION_ADMIN",
            inst_map["1-100234902"].id,
        ),
        (
            "officer@aicte.gov.in",
            "Officer@2026!",
            "AICTE Regional Inspector",
            "AICTE_OFFICER",
            None,
        ),
        (
            "student.demo@aicte.gov.in",
            settings.DEMO_STUDENT_PASSWORD,
            "Rohan Mehta",
            "STUDENT",
            None,
        ),
        (
            "verifier.tcs@tcs.com",
            settings.DEMO_VERIFIER_PASSWORD,
            "TCS Background Verifier",
            "VERIFIER",
            None,
        ),
    ]

    for email, pwd, full_name, r_name, inst_id in demo_users_spec:
        stmt = select(User).where(User.email == email)
        res = await db.execute(stmt)
        u = res.scalar_one_or_none()
        pwd_hash = hash_password(pwd)
        if not u:
            u = User(
                id=uuid.uuid4(),
                email=email,
                password_hash=pwd_hash,
                full_name=full_name,
                is_active=True,
                is_verified=True,
            )
            db.add(u)
            await db.flush()
        else:
            u.password_hash = pwd_hash
            u.is_active = True
            u.failed_login_attempts = 0
            u.locked_until = None

        # Ensure user role (no id column on UserRole)
        target_r = role_map[r_name]
        stmt_ur = select(UserRole).where((UserRole.user_id == u.id) & (UserRole.role_id == target_r.id))
        ur = (await db.execute(stmt_ur)).scalar_one_or_none()
        if not ur:
            db.add(UserRole(user_id=u.id, role_id=target_r.id))

        # Ensure institution linkage (no id column on UserInstitution)
        if inst_id:
            stmt_ui = select(UserInstitution).where(
                (UserInstitution.user_id == u.id) & (UserInstitution.institution_id == inst_id)
            )
            ui = (await db.execute(stmt_ui)).scalar_one_or_none()
            if not ui:
                db.add(UserInstitution(user_id=u.id, institution_id=inst_id))

    # 7. Seed Cross-Institution Duplicate Baseline Students in DTU Delhi
    # These 2 students are actively enrolled in DTU Delhi for 2025-26.
    # When violation.csv is uploaded to IITM Mumbai, it contains rows 10 & 28 with these exact APAAR IDs!
    dtu_inst = inst_map["1-100234902"]
    dtu_prog = prog_map["1-100234902"]

    dup_students_spec = [
        ("100000000010", "Aarav", "Sharma", "MALE", "EN-DTU-2025-010"),
        ("100000000028", "Diya", "Patel", "FEMALE", "EN-DTU-2025-028"),
    ]

    for apaar, fn, ln, gdr, en_num in dup_students_spec:
        stmt = select(Student).where(Student.apaar_id == apaar)
        res = await db.execute(stmt)
        s = res.scalar_one_or_none()
        full_name = f"{fn} {ln}"
        if not s:
            s = Student(
                id=uuid.uuid4(),
                apaar_id=apaar,
                apaar_status="VERIFIED",
                name_enc=full_name,
                dob_enc=date(2004, 3, 10),
                gender=gdr,
                name_bidx=compute_blind_index(full_name),
                dob_bidx=compute_blind_index(date(2004, 3, 10)),
            )
            db.add(s)
            await db.flush()

        # Seed Enrolment in DTU Delhi
        stmt_enr = select(Enrolment).where(
            (Enrolment.student_id == s.id) & (Enrolment.academic_year == "2025-26")
        )
        enr = (await db.execute(stmt_enr)).scalar_one_or_none()
        if not enr:
            enr = Enrolment(
                id=uuid.uuid4(),
                student_id=s.id,
                institution_id=dtu_inst.id,
                program_id=dtu_prog.id,
                academic_year="2025-26",
                student_ref_id=en_num,
                admission_category="GEN",
                quota_type="REGULAR",
                admission_date=date(2025, 8, 1),
                status="ACTIVE",
                validation_status="CLEAN",
            )
            db.add(enr)

    # 8. Seed Rohan Mehta in IITM Mumbai with an active verifiable credential
    # for the verifier/consent and tamper demonstration
    iitm_inst = inst_map["1-100234901"]
    iitm_prog = prog_map["1-100234901"]
    rohan_apaar = "987654321016"

    stmt = select(Student).where(Student.apaar_id == rohan_apaar)
    rohan_s = (await db.execute(stmt)).scalar_one_or_none()
    if not rohan_s:
        rohan_name = "Rohan Mehta"
        rohan_s = Student(
            id=uuid.uuid4(),
            apaar_id=rohan_apaar,
            apaar_status="VERIFIED",
            name_enc=rohan_name,
            dob_enc=date(2003, 7, 21),
            gender="MALE",
            name_bidx=compute_blind_index(rohan_name),
            dob_bidx=compute_blind_index(date(2003, 7, 21)),
        )
        db.add(rohan_s)
        await db.flush()

    # Enrolment for Rohan
    rohan_enr = Enrolment(
        id=uuid.uuid4(),
        student_id=rohan_s.id,
        institution_id=iitm_inst.id,
        program_id=iitm_prog.id,
        academic_year="2024-25",
        student_ref_id="IITM-2022-CSE-042",
        admission_category="GEN",
        quota_type="REGULAR",
        admission_date=date(2022, 8, 10),
        status="ACTIVE",
        validation_status="CLEAN",
    )
    db.add(rohan_enr)
    await db.flush()

    # Issued Record with Ed25519 signature
    cred_token = "rec_demo_rohan_2026_valid"
    cred_payload = {
        "record_id": str(uuid.uuid4()),
        "token": cred_token,
        "apaar_ref": hashlib.sha256(f"apaar_salt_{rohan_apaar}".encode()).hexdigest()[:32],
        "student_ref_id": "IITM-2022-CSE-042",
        "student_name": "Rohan Mehta",
        "institution": {
            "aicte_id": iitm_inst.aicte_id,
            "name": iitm_inst.name,
        },
        "program": iitm_prog.name,
        "academic_year": "2024-25",
        "enrolment_start": "2022-08-10",
        "expected_end": "2026-06-30",
        "status": "ACTIVE",
        "cgpa": 8.92,
        "issued_at": datetime.now(timezone.utc).isoformat(),
    }
    sig_b64, _, kid = sign_credential(cred_payload)
    issued_rec = IssuedRecord(
        id=uuid.uuid4(),
        enrolment_id=rohan_enr.id,
        token=cred_token,
        kid=kid,
        payload=cred_payload,
        signature=sig_b64,
        status="VALID",
        issued_at=datetime.now(timezone.utc),
    )
    db.add(issued_rec)

    # VerifierOrg & Pre-Approved Consent Request for TCS
    stmt_vorg = select(VerifierOrg).where(VerifierOrg.cin_gstin == "L65990MH1968PLC014039")
    vorg = (await db.execute(stmt_vorg)).scalar_one_or_none()
    if not vorg:
        vorg = VerifierOrg(
            id=uuid.uuid4(),
            org_name="Tata Consultancy Services Ltd (TCS)",
            cin_gstin="L65990MH1968PLC014039",
            contact_email="verifier.tcs@tcs.com",
            purpose_categories=["EMPLOYMENT"],
            status="APPROVED",
        )
        db.add(vorg)
        await db.flush()

    # Consent Request pre-approved for immediate demo verification
    consent_tok = "tok_tcs_demo_consent_2026"
    consent_req = ConsentRequest(
        id=uuid.uuid4(),
        student_id=rohan_s.id,
        verifier_id="verifier.tcs@tcs.com",
        verifier_org_name="Tata Consultancy Services Ltd",
        purpose="Campus Placement Credential Verification (Software Engineer Role)",
        purpose_category="EMPLOYMENT",
        fields_requested=["student_name", "institution", "program", "academic_year", "cgpa", "status"],
        approved_fields=["student_name", "institution", "program", "academic_year", "cgpa", "status"],
        retention_days=30,
        status="APPROVED",
        token=consent_tok,
        approved_at=datetime.now(timezone.utc),
        expires_at=datetime(2027, 1, 1, tzinfo=timezone.utc),
    )
    db.add(consent_req)

    # 9. Seed Initial Baseline ML Risk Scores for institutions
    # DTU: Low risk (14.2)
    # PICT: Medium risk (48.5)
    # IITM: Low risk before upload (12.0)
    scores = [
        (iitm_inst.id, 12.0, "LOW", 0.12),
        (dtu_inst.id, 14.5, "LOW", 0.14),
        (inst_map["1-100234903"].id, 48.5, "MEDIUM", 0.48),
    ]
    for i_id, rscore, rlvl, ascore in scores:
        rs = InstitutionRiskScore(
            id=uuid.uuid4(),
            institution_id=i_id,
            academic_year="2025-26",
            risk_score=rscore,
            risk_level=rlvl,
            anomaly_score=ascore,
            contributing_factors=[],
            metrics={"total_enrolments": 2, "approved_intake": 120},
            peer_comparison={"peer_median_risk_score": 18.0},
            ghost_student_flags={"burst_detected": False},
            model_version="v1.0",
        )
        db.add(rs)

    # 10. Seed 2 baseline informational alerts
    alt1 = Alert(
        id=uuid.uuid4(),
        type="SYSTEM_READY",
        severity="INFO",
        institution_id=iitm_inst.id,
        message="AICTE Central Academic Ledger initialized. Waiting for 2025-26 batch uploads.",
        status="NEW",
    )
    alt2 = Alert(
        id=uuid.uuid4(),
        type="SECURITY_AUDIT",
        severity="INFO",
        institution_id=None,
        message="Cryptographic keystore loaded. Ed25519 signing service online (KID: aicte-key-2026-v1).",
        status="NEW",
    )
    db.add(alt1)
    db.add(alt2)

    await db.commit()

    duration = round((time.time() - start_time) * 1000, 2)

    return ResetResponse(
        status="success",
        message=f"Demo database reset and re-seeded successfully in {duration}ms.",
        reset_duration_ms=duration,
        timestamp=datetime.now(timezone.utc).isoformat(),
        seeded_entities={
            "institutions_active": 3,
            "programs_configured": 2,
            "baseline_students": 3,
            "duplicate_references": 2,
            "verifiable_credentials": 1,
            "preapproved_consents": 1,
            "initial_alerts": 2,
        },
        demo_accounts=[
            {"role": "SUPER_ADMIN", "email": "superadmin@aicte.gov.in", "password": settings.DEMO_SUPERADMIN_PASSWORD},
            {"role": "INSTITUTION_ADMIN", "email": "director.iitm@aicte.gov.in", "password": settings.DEMO_INSTITUTION_PASSWORD},
            {"role": "INSTITUTION_ADMIN", "email": "registrar.dtu@aicte.gov.in", "password": settings.DEMO_INSTITUTION_PASSWORD},
            {"role": "AICTE_OFFICER", "email": "officer@aicte.gov.in", "password": "Officer@2026!"},
            {"role": "VERIFIER", "email": "verifier.tcs@tcs.com", "password": settings.DEMO_VERIFIER_PASSWORD},
            {"role": "STUDENT", "email": "student.demo@aicte.gov.in", "password": settings.DEMO_STUDENT_PASSWORD},
        ],
        demo_assets=[
            {"name": "clean.csv", "path": "/demo-assets/clean.csv", "records": "60 records (within 60 sanctioned)"},
            {"name": "violation.csv", "path": "/demo-assets/violation.csv", "records": "150 records on 120 intake + 2 cross-inst duplicates"},
            {"name": "tamper_sample.json", "path": "/demo-assets/tamper_sample.json", "purpose": "Tamper-proof signature validation demo"},
        ],
    )
