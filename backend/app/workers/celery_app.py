"""Celery task queue configuration and initialization."""

from celery import Celery
from celery.schedules import crontab

from app.core.config import settings

celery_app = Celery(
    "apaar_sutra_workers",
    broker=settings.CELERY_BROKER_URL,
    backend=settings.CELERY_RESULT_BACKEND,
)

celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
    task_track_started=True,
    task_time_limit=3600,
    worker_prefetch_multiplier=1,
)

# Celery Beat Scheduled Tasks
celery_app.conf.beat_schedule = {
    "nightly-cross-institution-scan": {
        "task": "app.workers.tasks.run_nightly_cross_institution_scan",
        "schedule": crontab(hour="2", minute="0"),  # 02:00 UTC daily
    },
    "nightly-ml-retrain-and-score": {
        "task": "app.workers.tasks.retrain_and_score_institutions",
        "schedule": crontab(hour="3", minute="0"),  # 03:00 UTC daily
    },
    "retry-pending-apaar-verifications": {
        "task": "app.workers.tasks.retry_pending_apaar_verifications",
        "schedule": crontab(minute="*/15"),  # Every 15 minutes
    },
    "weekly-statutory-reports-generation": {
        "task": "app.workers.tasks.generate_scheduled_statutory_reports",
        "schedule": crontab(day_of_week="monday", hour="4", minute="0"),  # 04:00 UTC Monday
    },
}

celery_app.autodiscover_tasks(["app.workers"])
