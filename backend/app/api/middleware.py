"""Cross-cutting middlewares: Request ID, Structured Logging, Security Headers, and Upload Hardening."""

import logging
import time
import uuid
import zipfile
import io
from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.requests import Request
from starlette.responses import JSONResponse, Response

from app.core.exceptions import ValidationException
from app.core.logging import set_current_request_id

logger = logging.getLogger("app.middleware")

MAX_JSON_BODY_BYTES = 1 * 1024 * 1024  # 1 MB for regular JSON payloads
MAX_UPLOAD_BODY_BYTES = 20 * 1024 * 1024  # 20 MB for bulk ingestion files


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
    """Enforces rigorous production security headers (CSP, HSTS, X-Content-Type-Options, etc.)."""

    async def dispatch(self, request: Request, call_next: RequestResponseEndpoint) -> Response:
        response = await call_next(request)
        response.headers["Content-Security-Policy"] = (
            "default-src 'self'; "
            "script-src 'self'; "
            "style-src 'self' 'unsafe-inline'; "
            "img-src 'self' data: https:; "
            "font-src 'self'; "
            "connect-src 'self'; "
            "frame-ancestors 'none';"
        )
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["X-XSS-Protection"] = "1; mode=block"
        response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains; preload"
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
        response.headers["Permissions-Policy"] = "geolocation=(), microphone=(), camera=()"
        return response


class RequestBodyLimitMiddleware(BaseHTTPMiddleware):
    """Enforces maximum payload size limits to guard against DoS via oversized requests."""

    async def dispatch(self, request: Request, call_next: RequestResponseEndpoint) -> Response:
        content_length = request.headers.get("content-length")
        is_upload = "upload" in request.url.path or "batch" in request.url.path
        limit = MAX_UPLOAD_BODY_BYTES if is_upload else MAX_JSON_BODY_BYTES

        if content_length and int(content_length) > limit:
            req_id = getattr(request.state, "request_id", str(uuid.uuid4()))
            limit_mb = limit / (1024 * 1024)
            return JSONResponse(
                status_code=413,
                content={
                    "error": {
                        "code": "PAYLOAD_TOO_LARGE",
                        "message": f"Request body exceeds maximum allowed limit of {limit_mb:.0f} MB.",
                        "details": {"max_bytes": limit, "received_bytes": int(content_length)},
                        "request_id": req_id,
                    }
                },
                headers={"X-Request-ID": req_id},
            )

        return await call_next(request)


class StructuredLoggingMiddleware(BaseHTTPMiddleware):
    """Logs incoming requests, response status codes, and execution duration in milliseconds."""

    async def dispatch(self, request: Request, call_next: RequestResponseEndpoint) -> Response:
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


def validate_file_magic_bytes(content: bytes, filename: str) -> str:
    """Validate uploaded file types using magic-byte signature analysis.
    
    Returns file type ('CSV' or 'XLSX') or raises ValidationException.
    """
    if len(content) > MAX_UPLOAD_BODY_BYTES:
        raise ValidationException(
            message=f"File exceeds maximum upload size of {MAX_UPLOAD_BODY_BYTES // (1024*1024)} MB."
        )

    lower_name = filename.lower()

    # 1. XLSX validation (ZIP file header: PK\x03\x04 with valid workbook XML contents)
    if lower_name.endswith(".xlsx"):
        if not content.startswith(b"PK\x03\x04"):
            raise ValidationException(message="Invalid XLSX file: File header does not match Excel OpenXML signature.")
        try:
            with zipfile.ZipFile(io.BytesIO(content)) as z:
                names = z.namelist()
                if not any("[Content_Types].xml" in name or "xl/" in name for name in names):
                    raise ValidationException(message="Invalid XLSX file: Missing internal Excel structures.")
        except zipfile.BadZipFile:
            raise ValidationException(message="Corrupted or tampered XLSX file.")
        return "XLSX"

    # 2. CSV validation (Plaintext / UTF-8, no binary null bytes, no executable macros)
    elif lower_name.endswith(".csv"):
        if b"\x00" in content[:4096]:
            raise ValidationException(message="Invalid CSV file: Binary null bytes detected.")
        try:
            sample_text = content[:2048].decode("utf-8")
        except UnicodeDecodeError:
            raise ValidationException(message="Invalid CSV file: File must be UTF-8 encoded text.")

        # Guard against CSV formula injection (DDE attacks)
        dangerous_prefixes = ("=cmd", "=powershell", "@summarize", "+cmd")
        for line in sample_text.splitlines()[:5]:
            for cell in line.split(","):
                clean_cell = cell.strip().lower()
                if any(clean_cell.startswith(p) for p in dangerous_prefixes):
                    raise ValidationException(message="Security Policy Violation: Potential CSV formula injection detected.")
        return "CSV"

    else:
        raise ValidationException(message="Unsupported file format. Only CSV (.csv) and Excel (.xlsx) files are accepted.")
