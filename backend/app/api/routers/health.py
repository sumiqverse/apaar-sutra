"""Health and readiness check endpoints."""

import time
from datetime import datetime, timezone
from fastapi import APIRouter, Depends, Response, status
import redis.asyncio as aioredis
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_db, get_request_id
from app.core.config import settings
from app.schemas.common import ComponentHealth, HealthStatus, ReadyStatus

router = APIRouter(tags=["Health & Readiness"])


@router.get(
    "/health",
    response_model=HealthStatus,
    summary="Liveness Probe",
    description="Returns 200 if the FastAPI application process is alive and accepting traffic.",
)
async def liveness(req_id: str = Depends(get_request_id)) -> HealthStatus:
    return HealthStatus(
        status="healthy",
        app_name=settings.APP_NAME,
        environment=settings.ENVIRONMENT,
        version="0.1.0",
        timestamp=datetime.now(timezone.utc).isoformat(),
        request_id=req_id,
    )


@router.get(
    "/ready",
    response_model=ReadyStatus,
    summary="Readiness Probe",
    description="Deep probe validating connectivity to PostgreSQL 16 and Redis 7.",
)
async def readiness(
    response: Response,
    db: AsyncSession = Depends(get_db),
    req_id: str = Depends(get_request_id),
) -> ReadyStatus:
    # 1. Probe PostgreSQL
    db_health = ComponentHealth(status="connected")
    try:
        t0 = time.perf_counter()
        result = await db.execute(text("SELECT 1"))
        result.scalar()
        db_health.latency_ms = round((time.perf_counter() - t0) * 1000, 2)
    except Exception as exc:
        db_health.status = "degraded"
        db_health.message = f"Database probe failed: {str(exc)}"

    # 2. Probe Redis
    redis_health = ComponentHealth(status="connected")
    try:
        t0 = time.perf_counter()
        r = aioredis.from_url(settings.REDIS_URL, socket_timeout=2.0)
        pong = await r.ping()
        await r.aclose()
        if not pong:
            redis_health.status = "degraded"
            redis_health.message = "Redis ping returned false"
        else:
            redis_health.latency_ms = round((time.perf_counter() - t0) * 1000, 2)
    except Exception as exc:
        redis_health.status = "degraded"
        redis_health.message = f"Redis probe failed: {str(exc)}"

    is_ready = db_health.status == "connected" and redis_health.status == "connected"
    if not is_ready:
        response.status_code = status.HTTP_503_SERVICE_UNAVAILABLE

    return ReadyStatus(
        status="ready" if is_ready else "unhealthy",
        database=db_health,
        redis=redis_health,
        timestamp=datetime.now(timezone.utc).isoformat(),
        request_id=req_id,
    )
