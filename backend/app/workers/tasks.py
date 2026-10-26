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
