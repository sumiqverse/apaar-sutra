"""Main FastAPI Application Entrypoint for APAAR-Sutra."""

from contextlib import asynccontextmanager
from typing import AsyncGenerator
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.middleware import RequestIDMiddleware, SecurityHeadersMiddleware, StructuredLoggingMiddleware
from app.api.routers import health_router, api_v1_router
from app.core.config import settings
from app.core.exceptions import register_exception_handlers
from app.core.logging import setup_logging
from app.mock_apaar.server import mock_apaar_app


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """Application lifecycle management."""
    # Setup structured logging
    setup_logging(log_level=settings.LOG_LEVEL, log_format=settings.LOG_FORMAT)
    yield


def create_application() -> FastAPI:
    """Factory creating and configuring the primary FastAPI application."""
    app = FastAPI(
        title=settings.APP_NAME,
        description="AICTE Student Data Management and Verification Platform (SIH Problem 26263)",
        version="0.1.0",
        docs_url="/api/docs",
        redoc_url="/api/redoc",
        openapi_url="/api/openapi.json",
        lifespan=lifespan,
    )

    # 1. Register Global Exception Handlers (Standard Error Envelope)
    register_exception_handlers(app)

    # 2. Register Cross-Cutting Middlewares (executed in reverse registration order)
    # Structured request execution logging
    app.add_middleware(StructuredLoggingMiddleware)
    # Enforce security headers (HSTS, CSP, nosniff, etc.)
    app.add_middleware(SecurityHeadersMiddleware)
    # Request-ID propagation (X-Request-ID in & out)
    app.add_middleware(RequestIDMiddleware)
    # CORS Allowlist
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.CORS_ORIGINS,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
        expose_headers=["X-Request-ID"],
    )

    # 3. Mount Health Probes (Available both at root /health and /api/v1/health)
    app.include_router(health_router)
    app.include_router(health_router, prefix=settings.API_V1_PREFIX)

    # 4. Mount Versioned Functional API Router (/api/v1)
    app.include_router(api_v1_router, prefix=settings.API_V1_PREFIX)

    # 5. Mount Mock National APAAR Gateway for Dev/Test
    app.mount(f"{settings.API_V1_PREFIX}/mock-apaar", mock_apaar_app)

    return app


app = create_application()


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "app.main:app",
        host=settings.HOST,
        port=settings.PORT,
        reload=settings.DEBUG,
    )
