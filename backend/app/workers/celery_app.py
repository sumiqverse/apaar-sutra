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
    "nightly-anomaly-sweep": {
        "task": "app.workers.tasks.run_nightly_anomaly_checks",
        "schedule": crontab(hour="2", minute="0"),  # 02:00 UTC daily
    },
}

celery_app.autodiscover_tasks(["app.workers"])
