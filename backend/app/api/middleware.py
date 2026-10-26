"""Cross-cutting middlewares: Request ID, Structured Logging, and Security Headers."""

import logging
import time
import uuid
from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.requests import Request
from starlette.responses import Response

from app.core.logging import set_current_request_id

logger = logging.getLogger("app.middleware")


class RequestIDMiddleware(BaseHTTPMiddleware):
    """Inspects incoming X-Request-ID or mints a UUIDv4, attaching to context and headers."""

    async def dispatch(self, request: Request, call_next: RequestResponseEndpoint) -> Response:
        incoming_id = request.headers.get("X-Request-ID")
        req_id = incoming_id if (incoming_id and len(incoming_id) <= 64) else str(uuid.uuid4())

        # Store in request state and context variable
        request.state.request_id = req_id
        set_current_request_id(req_id)

        response = await call_next(request)
        response.headers["X-Request-ID"] = req_id
        return response


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    """Enforces essential security headers on all HTTP responses."""

    async def dispatch(self, request: Request, call_next: RequestResponseEndpoint) -> Response:
        response = await call_next(request)
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["X-XSS-Protection"] = "1; mode=block"
        response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
        response.headers["Permissions-Policy"] = "geolocation=(), microphone=(), camera=()"
        return response


class StructuredLoggingMiddleware(BaseHTTPMiddleware):
    """Logs incoming requests, response status codes, and execution duration in milliseconds."""

    async def dispatch(self, request: Request, call_next: RequestResponseEndpoint) -> Response:
        # Skip excessive logging for repetitive health probes
        is_probe = request.url.path in ("/health", "/api/v1/health")
        start_time = time.perf_counter()

        response = await call_next(request)
        duration_ms = round((time.perf_counter() - start_time) * 1000, 2)

        if not is_probe:
            req_id = getattr(request.state, "request_id", "")
            client_ip = request.client.host if request.client else "unknown"
            logger.info(
                f"{request.method} {request.url.path} -> {response.status_code} ({duration_ms}ms)",
                extra={
                    "request_id": req_id,
                    "method": request.method,
                    "path": request.url.path,
                    "status_code": response.status_code,
                    "duration_ms": duration_ms,
                    "client_ip": client_ip,
                },
            )
        return response
