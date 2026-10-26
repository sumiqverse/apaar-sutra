import asyncio
import logging
from typing import Any, Dict, List, Optional
import uuid
import redis

from app.core.config import settings
from app.models.base import AsyncSessionLocal
from app.models.student import Student
from app.services.bulk_ingestion_service import BulkIngestionService
from app.integrations.apaar import get_apaar_provider
from app.workers.celery_app import celery_app
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

logger = logging.getLogger("app.workers")

# Connect to Redis for telemetry
redis_conn = None
try:
    redis_conn = redis.from_url(settings.REDIS_URL, decode_responses=True)
except Exception:
    pass


@celery_app.task(bind=True, name="app.workers.tasks.process_bulk_student_upload")
def process_bulk_student_upload(
    self,
    batch_id: str,
    file_path: str,
    institution_id: str,
) -> Dict[str, Any]:
    """Asynchronously parse and ingest student upload file (CSV/XLSX) in chunks."""
    logger.info(f"Starting bulk ingestion task for batch {batch_id} (Institution: {institution_id}, File: {file_path})")

    async def _run():
        async with AsyncSessionLocal() as session:
            res = await BulkIngestionService.process_batch(
                batch_id=uuid.UUID(batch_id),
                file_path=file_path,
                institution_id=uuid.UUID(institution_id),
                session=session,
                redis_client=redis_conn,
            )
            # Automatically trigger validation engine post-upload
            await async_run_batch_validation(
                batch_id=batch_id,
                institution_id=institution_id,
                session=session,
            )
            return res

    return asyncio.run(_run())


async def async_retry_pending_verifications(session: Optional[AsyncSession] = None) -> int:
    """Async execution logic for retrying pending APAAR verifications."""
    own_session = session is None
    s = session if session is not None else AsyncSessionLocal()
    try:
        stmt = select(Student).where(Student.apaar_status == "PENDING").limit(500)
        res = await s.execute(stmt)
        students = res.scalars().all()
        if not students:
            return 0

        items = [{"apaar_id": st.apaar_id, "name": st.name_enc, "dob": st.dob_enc} for st in students]
        provider = get_apaar_provider()
        results = await provider.verify_batch(items)

        updated = 0
        for st in students:
            ver = results.get(st.apaar_id)
            if ver and ver.status != "PENDING":
                st.apaar_status = ver.status
                updated += 1

        await s.commit()
        logger.info(f"Reconciled {updated} of {len(students)} pending APAAR records.")
        return updated
    finally:
        if own_session:
            await s.close()


@celery_app.task(name="app.workers.tasks.retry_pending_apaar_verifications")
def retry_pending_apaar_verifications(session: Optional[Any] = None) -> Dict[str, Any]:
    """Reconcile and retry verification for student records in PENDING status."""
    logger.info("Executing scheduled retry for PENDING APAAR verifications...")
    count = asyncio.run(async_retry_pending_verifications(session=session))
    return {"reconciled": count}


async def async_run_batch_validation(
    batch_id: str,
    institution_id: Optional[str] = None,
    session: Optional[AsyncSession] = None,
) -> Dict[str, Any]:
    """Execute validation engine rules for an uploaded batch."""
    from app.models.batch import UploadBatch
    from app.validation.engine import RuleEngine

    own_session = session is None
    s = session if session is not None else AsyncSessionLocal()
    try:
        b_uuid = uuid.UUID(batch_id)
        inst_uuid = uuid.UUID(institution_id) if institution_id else None
        if not inst_uuid:
            b = await s.get(UploadBatch, b_uuid)
            if b:
                inst_uuid = b.institution_id

        if not inst_uuid:
            return {"error": "Institution not found", "violations": 0}

        engine = RuleEngine()
        violations = await engine.evaluate_batch(
            session=s,
            batch_id=b_uuid,
            institution_id=inst_uuid,
            persist=True,
        )
        return {"batch_id": batch_id, "violations": len(violations)}
    finally:
        if own_session:
            await s.close()


@celery_app.task(name="app.workers.tasks.run_batch_validation")
def run_batch_validation(batch_id: str, institution_id: Optional[str] = None) -> Dict[str, Any]:
    """Celery task running validation engine rules for an uploaded batch."""
    logger.info(f"Running validation rules for batch {batch_id}...")
    return asyncio.run(async_run_batch_validation(batch_id, institution_id))


async def async_run_cross_institution_scan(session: Optional[AsyncSession] = None) -> Dict[str, Any]:
    """Execute nightly set-based cross-institution scan across all enrolments."""
    from app.validation.engine import RuleEngine

    own_session = session is None
    s = session if session is not None else AsyncSessionLocal()
    try:
        engine = RuleEngine()
        violations = await engine.evaluate_cross_institution(session=s, persist=True)
        return {
            "status": "SUCCESS",
            "violations_detected": len(violations),
            "message": f"Nightly cross-institution scan completed. {len(violations)} issues flagged/updated.",
        }
    finally:
        if own_session:
            await s.close()


@celery_app.task(name="app.workers.tasks.run_nightly_cross_institution_scan")
def run_nightly_cross_institution_scan(session: Optional[Any] = None) -> Dict[str, Any]:
    """Scheduled task executing nightly set-based cross-institution compliance and capacity scan."""
    logger.info("Executing scheduled nightly cross-institution scan across AICTE database...")
    return asyncio.run(async_run_cross_institution_scan(session=session))


@celery_app.task(name="app.workers.tasks.run_nightly_anomaly_checks")
def run_nightly_anomaly_checks() -> Dict[str, Any]:
    """Backwards-compatible alias for nightly cross-institution scan."""
    return run_nightly_cross_institution_scan()


async def async_retrain_and_score_institutions(
    academic_year: str = "2025-26",
    session: Optional[AsyncSession] = None,
    version: Optional[str] = None,
) -> Dict[str, Any]:
    """Async execution logic for retraining Isolation Forest and updating institutional risk scores."""
    from datetime import datetime, timezone
    from app.models.institution import Institution
    from app.models.ml import InstitutionRiskScore
    from app.models.credential import Alert
    from app.ml.features import InstitutionFeatureExtractor
    from app.ml.peer_comparison import PeerGroupComparator
    from app.ml.anomaly_detector import InstitutionRiskDetector
    from app.ml.model_store import ModelStore

    own_session = session is None
    s = session if session is not None else AsyncSessionLocal()
    try:
        # 1. Extract features for all institutions
        features_by_id = await InstitutionFeatureExtractor.extract_for_all_institutions_async(
            session=s,
            academic_year=academic_year,
        )
        if not features_by_id:
            return {"status": "SKIPPED", "message": "No institutional records found for scoring."}

        # 2. Fetch institution metadata for peer grouping
        inst_res = await s.execute(select(Institution))
        institutions = list(inst_res.scalars().all())
        metadata_list = [
            {
                "id": str(i.id),
                "aicte_id": i.aicte_id,
                "name": i.name,
                "institution_type": i.institution_type,
                "state_id": str(i.state_id),
                "approved_total_intake": i.approved_total_intake,
            }
            for i in institutions
        ]

        # 3. Fit detector
        string_features = {str(k): v for k, v in features_by_id.items()}
        detector = InstitutionRiskDetector()
        detector.fit(string_features)

        # 4. Save model artifact
        model_ver = version or f"v{int(datetime.now(timezone.utc).timestamp())}"
        store = ModelStore()
        store.save_model(detector, version=model_ver, metadata={"academic_year": academic_year, "institutions_count": len(string_features)})

        # 5. Score institutions
        comparator = PeerGroupComparator(metadata_list, string_features)
        scored_institutions = detector.score_all(string_features, peer_comparator=comparator)

        # 6. Upsert risk scores in database
        high_risk_count = 0
        for item in scored_institutions:
            inst_uuid = uuid.UUID(item["institution_id"])
            score_val = item["risk_score"]
            level_val = item["risk_level"]

            if score_val >= 80.0:
                high_risk_count += 1
                # Auto-generate alert for critical risk institutions
                alert = Alert(
                    id=uuid.uuid4(),
                    type="CRITICAL_INSTITUTION_RISK",
                    severity="CRITICAL",
                    institution_id=inst_uuid,
                    message=f"Institution flagged as CRITICAL risk (Risk Score: {score_val}/100). Top factor: {item['contributing_factors'][0]['plain_english'] if item['contributing_factors'] else 'Multiple anomalous signals'}",
                    status="NEW",
                )
                s.add(alert)

            # Query existing score for this year
            existing_res = await s.execute(
                select(InstitutionRiskScore).where(
                    InstitutionRiskScore.institution_id == inst_uuid,
                    InstitutionRiskScore.academic_year == academic_year,
                    InstitutionRiskScore.model_version == model_ver,
                )
            )
            existing_record = existing_res.scalars().first()

            if existing_record:
                existing_record.risk_score = score_val
                existing_record.risk_level = level_val
                existing_record.anomaly_score = item["anomaly_score"]
                existing_record.contributing_factors = item["contributing_factors"]
                existing_record.metrics = item["metrics"]
                existing_record.peer_comparison = item["peer_comparison"]
                existing_record.ghost_student_flags = {}
            else:
                new_record = InstitutionRiskScore(
                    id=uuid.uuid4(),
                    institution_id=inst_uuid,
                    academic_year=academic_year,
                    risk_score=score_val,
                    risk_level=level_val,
                    anomaly_score=item["anomaly_score"],
                    contributing_factors=item["contributing_factors"],
                    metrics=item["metrics"],
                    peer_comparison=item["peer_comparison"],
                    ghost_student_flags={},
                    model_version=model_ver,
                )
                s.add(new_record)

        await s.commit()

        return {
            "status": "SUCCESS",
            "model_version": model_ver,
            "institutions_scored": len(scored_institutions),
            "high_risk_count": high_risk_count,
            "message": f"Nightly ML retraining and scoring completed. {len(scored_institutions)} institutions assessed ({high_risk_count} critical).",
        }
    finally:
        if own_session:
            await s.close()


@celery_app.task(name="app.workers.tasks.retrain_and_score_institutions")
def retrain_and_score_institutions(academic_year: str = "2025-26", session: Optional[Any] = None) -> Dict[str, Any]:
    """Scheduled task executing nightly retraining of Isolation Forest and institutional risk scoring."""
    logger.info(f"Executing scheduled nightly ML retraining and scoring for academic year {academic_year}...")
    return asyncio.run(async_retrain_and_score_institutions(academic_year=academic_year, session=session))


async def async_generate_bulk_certificates(
    program_id: Optional[str] = None,
    academic_year: Optional[str] = None,
    institution_id: Optional[str] = None,
    template_id: str = "aicte_classic",
    session: Optional[AsyncSession] = None,
) -> Dict[str, Any]:
    """Generates a ZIP archive containing verifiable PDF certificates for an entire cohort."""
    import zipfile
    import os
    from app.models.enrolment import Enrolment
    from app.services.credential_service import CredentialService
    from sqlalchemy.orm import selectinload

    own_session = session is None
    s = session if session is not None else AsyncSessionLocal()
    try:
        stmt = (
            select(Enrolment)
            .options(
                selectinload(Enrolment.student),
                selectinload(Enrolment.institution),
                selectinload(Enrolment.program),
            )
            .limit(100)
        )
        if institution_id:
            stmt = stmt.where(Enrolment.institution_id == uuid.UUID(institution_id))
        if program_id:
            stmt = stmt.where(Enrolment.program_id == uuid.UUID(program_id))
        if academic_year:
            stmt = stmt.where(Enrolment.academic_year == academic_year)

        res = await s.execute(stmt)
        enrolments = res.scalars().all()

        cred_service = CredentialService(s)
        out_dir = os.path.join(os.getcwd(), "backend", "scratch")
        os.makedirs(out_dir, exist_ok=True)
        zip_filename = f"certificates_{uuid.uuid4().hex[:8]}.zip"
        zip_path = os.path.join(out_dir, zip_filename)

        with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as zf:
            for enr in enrolments:
                rec, pdf_bytes = await cred_service.issue_degree_certificate(
                    enrolment_id=enr.id,
                    template_id=template_id,
                    mark_completed=False,
                )
                safe_roll = "".join(c for c in enr.student_ref_id if c.isalnum() or c in "-_")
                zf.writestr(f"certificate_{safe_roll}_{rec.token[:8]}.pdf", pdf_bytes)

        return {
            "status": "SUCCESS",
            "total_certificates": len(enrolments),
            "zip_filename": zip_filename,
            "zip_path": zip_path,
        }
    finally:
        if own_session:
            await s.close()


@celery_app.task(bind=True, name="app.workers.tasks.generate_bulk_certificates_task")
def generate_bulk_certificates_task(
    self,
    program_id: Optional[str] = None,
    academic_year: Optional[str] = None,
    institution_id: Optional[str] = None,
    template_id: str = "aicte_classic",
) -> Dict[str, Any]:
    """Celery task executing asynchronous bulk PDF certificate rendering and ZIP export."""
    logger.info(f"Starting bulk certificate generation task for template {template_id}...")
    return asyncio.run(
        async_generate_bulk_certificates(
            program_id=program_id,
            academic_year=academic_year,
            institution_id=institution_id,
            template_id=template_id,
        )
    )


async def async_generate_scheduled_statutory_reports(session: Optional[AsyncSession] = None) -> Dict[str, Any]:
    """Celery beat worker generating weekly statutory capacity reports."""
    from app.services.report_service import ReportService
    from app.schemas.reports import ReportGenerateRequest

    own_session = session is None
    s = session if session is not None else AsyncSessionLocal()
    try:
        service = ReportService(s)
        reports = ["state_wise_intake", "overshoot_institutions", "institution_risk_ranking"]
        generated = []
        for r_type in reports:
            rep = await service.generate_and_persist_report(
                req=ReportGenerateRequest(report_type=r_type, format="PDF", academic_year="2025-26"),
                actor_id="CELERY_BEAT_SCHEDULER",
            )
            generated.append(rep.report_type)
        return {"status": "SUCCESS", "generated_reports": generated}
    finally:
        if own_session:
            await s.close()


@celery_app.task(name="app.workers.tasks.generate_scheduled_statutory_reports")
def generate_scheduled_statutory_reports() -> Dict[str, Any]:
    """Scheduled task generating weekly statutory AICTE reports."""
    logger.info("Executing scheduled statutory reports generation...")
    return asyncio.run(async_generate_scheduled_statutory_reports())



