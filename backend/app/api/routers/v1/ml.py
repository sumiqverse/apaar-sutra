"""ML intelligence layer and institutional anomaly detection endpoints."""

from datetime import datetime, timezone
import math
from typing import Any, Dict, List, Optional
import uuid

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_db, get_current_user, require_role, TokenPayload
from app.core.exceptions import ForbiddenException, NotFoundException, ValidationException
from app.models.institution import Institution
from app.models.student import Student
from app.models.enrolment import Enrolment
from app.models.ml import InstitutionRiskScore
from app.ml.features import InstitutionFeatureExtractor
from app.ml.peer_comparison import PeerGroupComparator
from app.ml.anomaly_detector import InstitutionRiskDetector
from app.ml.fuzzy_dedup import FuzzyDeduplicator
from app.ml.ghost_students import GhostStudentDetector
from app.ml.model_store import ModelStore
from app.schemas.ml import (
    InstitutionRiskItem,
    InstitutionRiskListResponse,
    InstitutionExplainResponse,
    ContributingFactorSchema,
    FuzzyDedupRequest,
    FuzzyDedupResponse,
    FuzzyDedupMatch,
    GhostStudentResponse,
    RetrainResponse,
)
from app.workers.tasks import async_retrain_and_score_institutions

router = APIRouter(prefix="/ml", tags=["ML Intelligence & Anomalies"])


def check_tenant_access(user: TokenPayload, target_institution_id: uuid.UUID) -> None:
    """Enforce institutional tenant isolation for non-superadmin roles."""
    national_roles = {"SUPER_ADMIN", "AICTE_OFFICER", "AICTE_ANALYST", "AUDITOR"}
    if any(role in national_roles for role in user.roles):
        return
    if str(target_institution_id) not in [str(i) for i in user.institution_ids]:
        raise ForbiddenException("Cross-tenant data access violation: insufficient institutional privileges.")


@router.get("/institution-risk", response_model=InstitutionRiskListResponse)
async def list_institution_risk_scores(
    academic_year: str = Query("2025-26", description="Academic year"),
    min_risk: float = Query(0.0, ge=0.0, le=100.0, description="Minimum risk score threshold"),
    state_id: Optional[uuid.UUID] = Query(None, description="Filter by state UUID"),
    institution_type: Optional[str] = Query(None, description="Filter by institution type"),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
    user: TokenPayload = Depends(get_current_user),
) -> InstitutionRiskListResponse:
    """Retrieve ranked institutional anomaly risk scores with multi-tenant scoping and filtering."""
    national_roles = {"SUPER_ADMIN", "AICTE_OFFICER", "AICTE_ANALYST", "AUDITOR"}
    is_national = any(role in national_roles for role in user.roles)

    # 1. Check if DB has pre-computed risk scores for this academic year
    count_query = select(func.count(InstitutionRiskScore.id)).where(
        InstitutionRiskScore.academic_year == academic_year
    )
    res = await db.execute(count_query)
    existing_count = res.scalar() or 0

    # Auto-seed scores on-the-fly if empty
    if existing_count == 0:
        await async_retrain_and_score_institutions(academic_year=academic_year, session=db)

    # 2. Build filtered query joining Institution
    query = (
        select(InstitutionRiskScore, Institution)
        .join(Institution, InstitutionRiskScore.institution_id == Institution.id)
        .where(
            InstitutionRiskScore.academic_year == academic_year,
            InstitutionRiskScore.risk_score >= min_risk,
        )
    )

    if not is_national:
        query = query.where(InstitutionRiskScore.institution_id.in_(user.institution_ids))

    if state_id:
        query = query.where(Institution.state_id == state_id)

    if institution_type:
        query = query.where(Institution.institution_type == institution_type)

    # Count total matching
    count_subquery = select(func.count()).select_from(query.subquery())
    count_res = await db.execute(count_subquery)
    total_items = count_res.scalar() or 0

    # Order by risk score descending
    query = query.order_by(InstitutionRiskScore.risk_score.desc())
    query = query.offset((page - 1) * page_size).limit(page_size)

    results = await db.execute(query)
    rows = results.all()

    items: List[InstitutionRiskItem] = []
    for risk_row, inst_row in rows:
        factors = [f.get("plain_english", "") for f in (risk_row.contributing_factors or [])][:3]
        items.append(
            InstitutionRiskItem(
                id=risk_row.id,
                institution_id=inst_row.id,
                aicte_id=inst_row.aicte_id,
                name=inst_row.name,
                institution_type=inst_row.institution_type,
                state_id=inst_row.state_id,
                state_code=None,
                academic_year=risk_row.academic_year,
                risk_score=risk_row.risk_score,
                risk_level=risk_row.risk_level,
                anomaly_score=risk_row.anomaly_score,
                top_factors=[f for f in factors if f],
                metrics=risk_row.metrics or {},
                model_version=risk_row.model_version,
                created_at=risk_row.created_at,
            )
        )

    total_pages = math.ceil(total_items / page_size) if total_items > 0 else 1

    return InstitutionRiskListResponse(
        items=items,
        total_items=total_items,
        page=page,
        page_size=page_size,
        total_pages=total_pages,
    )


@router.get("/explain/{institution_id}", response_model=InstitutionExplainResponse)
async def explain_institution_risk(
    institution_id: uuid.UUID,
    academic_year: str = Query("2025-26"),
    db: AsyncSession = Depends(get_db),
    user: TokenPayload = Depends(get_current_user),
) -> InstitutionExplainResponse:
    """Retrieve granular plain-English explainability, radar metrics, and peer percentiles for an institution."""
    check_tenant_access(user, institution_id)

    # 1. Fetch institution
    inst_res = await db.execute(select(Institution).where(Institution.id == institution_id))
    inst = inst_res.scalars().first()
    if not inst:
        raise NotFoundException(f"Institution with ID '{institution_id}' not found.")

    # 2. Fetch risk score record
    score_res = await db.execute(
        select(InstitutionRiskScore).where(
            InstitutionRiskScore.institution_id == institution_id,
            InstitutionRiskScore.academic_year == academic_year,
        ).order_by(InstitutionRiskScore.created_at.desc())
    )
    risk_record = score_res.scalars().first()

    if not risk_record:
        # Trigger scoring on-the-fly
        await async_retrain_and_score_institutions(academic_year=academic_year, session=db)
        score_res = await db.execute(
            select(InstitutionRiskScore).where(
                InstitutionRiskScore.institution_id == institution_id,
                InstitutionRiskScore.academic_year == academic_year,
            ).order_by(InstitutionRiskScore.created_at.desc())
        )
        risk_record = score_res.scalars().first()

    # 3. Analyze ghost student indicators
    enrol_res = await db.execute(
        select(Enrolment, Student)
        .join(Student, Enrolment.student_id == Student.id)
        .where(Enrolment.institution_id == institution_id, Enrolment.academic_year == academic_year)
    )
    enrol_rows = enrol_res.all()
    enrolments_dicts = [
        {"id": str(en.id), "student_id": str(en.student_id), "admission_date": en.admission_date, "created_at": en.created_at}
        for en, _ in enrol_rows
    ]
    students_dicts = [
        {"id": str(st.id), "apaar_id": st.apaar_id, "dob_enc": st.dob_enc, "parent_name_enc": st.parent_name_enc}
        for _, st in enrol_rows
    ]
    ghost_summary = GhostStudentDetector.analyze_institution(str(institution_id), enrolments_dicts, students_dicts)

    factors = []
    if risk_record and risk_record.contributing_factors:
        for f in risk_record.contributing_factors:
            factors.append(ContributingFactorSchema(
                feature=f.get("feature", ""),
                institution_value=float(f.get("institution_value", 0.0)),
                peer_median=float(f.get("peer_median", 0.0)),
                deviation_pct=float(f.get("deviation_pct", 0.0)),
                z_score=float(f.get("z_score", 0.0)),
                plain_english=f.get("plain_english", ""),
            ))

    return InstitutionExplainResponse(
        institution_id=inst.id,
        aicte_id=inst.aicte_id,
        name=inst.name,
        academic_year=academic_year,
        risk_score=risk_record.risk_score if risk_record else 0.0,
        risk_level=risk_record.risk_level if risk_record else "LOW",
        anomaly_score=risk_record.anomaly_score if risk_record else 0.0,
        contributing_factors=factors,
        metrics=risk_record.metrics if risk_record else {},
        peer_comparison=risk_record.peer_comparison if risk_record else {},
        ghost_student_summary=ghost_summary,
        model_version=risk_record.model_version if risk_record else "v1.0",
        assessed_at=risk_record.created_at if risk_record else datetime.now(timezone.utc),
    )


@router.get("/ghost-students/{institution_id}", response_model=GhostStudentResponse)
async def get_ghost_students_analysis(
    institution_id: uuid.UUID,
    academic_year: str = Query("2025-26"),
    db: AsyncSession = Depends(get_db),
    user: TokenPayload = Depends(get_current_user),
) -> GhostStudentResponse:
    """Analyze ghost-student indicators including timestamp bursts, sequential APAARs, and demographic clusters."""
    check_tenant_access(user, institution_id)

    enrol_res = await db.execute(
        select(Enrolment, Student)
        .join(Student, Enrolment.student_id == Student.id)
        .where(Enrolment.institution_id == institution_id, Enrolment.academic_year == academic_year)
    )
    rows = enrol_res.all()
    enrol_dicts = [
        {"id": str(en.id), "student_id": str(en.student_id), "admission_date": en.admission_date, "created_at": en.created_at}
        for en, _ in rows
    ]
    student_dicts = [
        {"id": str(st.id), "apaar_id": st.apaar_id, "dob_enc": st.dob_enc, "parent_name_enc": st.parent_name_enc}
        for _, st in rows
    ]

    report = GhostStudentDetector.analyze_institution(str(institution_id), enrol_dicts, student_dicts)

    return GhostStudentResponse(
        institution_id=str(institution_id),
        heuristic_risk_score=report["heuristic_risk_score"],
        suspect_students_count=report["suspect_students_count"],
        suspect_students_ratio=report["suspect_students_ratio"],
        burst_admission_clusters=report["burst_admission_clusters"],
        sequential_apaar_runs=report["sequential_apaar_runs"],
        repeating_demographic_clusters=report["repeating_demographic_clusters"],
        has_ghost_indicators=report["has_ghost_indicators"],
    )


@router.post("/fuzzy-dedup", response_model=FuzzyDedupResponse)
async def run_fuzzy_deduplication(
    payload: FuzzyDedupRequest,
    db: AsyncSession = Depends(get_db),
    user: TokenPayload = Depends(get_current_user),
) -> FuzzyDedupResponse:
    """Perform scalable Indian-name-aware blocked fuzzy deduplication across student records."""
    candidate_records: List[Dict[str, Any]] = []

    if payload.records:
        candidate_records = [
            {
                "id": r.id or str(uuid.uuid4()),
                "name": r.name,
                "dob": r.dob,
                "apaar_id": r.apaar_id,
                "institution_id": r.institution_id,
            }
            for r in payload.records
        ]
    elif payload.institution_id:
        check_tenant_access(user, payload.institution_id)
        res = await db.execute(
            select(Student, Enrolment)
            .join(Enrolment, Student.id == Enrolment.student_id)
            .where(Enrolment.institution_id == payload.institution_id)
        )
        for st, en in res.all():
            candidate_records.append({
                "id": str(st.id),
                "name": str(st.name_enc),
                "dob": str(st.dob_enc) if st.dob_enc else None,
                "apaar_id": st.apaar_id,
                "institution_id": str(payload.institution_id),
            })
    else:
        raise ValidationException("Either 'institution_id' or a non-empty 'records' list must be provided.")

    deduplicator = FuzzyDeduplicator(similarity_threshold=payload.similarity_threshold)
    raw_matches = deduplicator.find_duplicates(candidate_records)

    matches = [
        FuzzyDedupMatch(
            student_a_id=m["student_a_id"],
            student_b_id=m["student_b_id"],
            student_a_name=m["student_a_name"],
            student_b_name=m["student_b_name"],
            dob_year=m["dob_year"],
            phonetic_block=m["phonetic_block"],
            similarity_score=m["similarity_score"],
            apaar_a=m.get("apaar_a"),
            apaar_b=m.get("apaar_b"),
            institution_a=m.get("institution_a"),
            institution_b=m.get("institution_b"),
        )
        for m in raw_matches
    ]

    return FuzzyDedupResponse(
        total_candidates=len(candidate_records),
        duplicate_pairs_found=len(matches),
        matches=matches,
    )


@router.post("/retrain", response_model=RetrainResponse, dependencies=[Depends(require_role(["SUPER_ADMIN"]))])
async def trigger_model_retraining(
    academic_year: str = Query("2025-26"),
    db: AsyncSession = Depends(get_db),
    user: TokenPayload = Depends(get_current_user),
) -> RetrainResponse:
    """Manually trigger Isolation Forest model retraining and institutional risk score recalculation."""
    result = await async_retrain_and_score_institutions(academic_year=academic_year, session=db)
    return RetrainResponse(
        status=result.get("status", "SUCCESS"),
        model_version=result.get("model_version", "v1.0"),
        institutions_scored=result.get("institutions_scored", 0),
        high_risk_count=result.get("high_risk_count", 0),
        message=result.get("message", "Model retraining and scoring executed."),
    )
