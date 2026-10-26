"""Global exception definitions and FastAPI exception handlers."""

import logging
from typing import Any, Dict, Optional
from fastapi import FastAPI, Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

from app.core.logging import get_current_request_id

logger = logging.getLogger(__name__)


class AppException(Exception):
    """Base application exception for domain errors."""

    def __init__(
        self,
        code: str,
        message: str,
        status_code: int = status.HTTP_400_BAD_REQUEST,
        details: Optional[Dict[str, Any]] = None,
    ):
        self.code = code
        self.message = message
        self.status_code = status_code
        self.details = details or {}
        super().__init__(self.message)


class NotFoundException(AppException):
    def __init__(self, message: str = "Resource not found", details: Optional[Dict[str, Any]] = None):
        super().__init__(code="NOT_FOUND", message=message, status_code=status.HTTP_404_NOT_FOUND, details=details)


class UnauthorizedException(AppException):
    def __init__(self, message: str = "Authentication required", details: Optional[Dict[str, Any]] = None):
        super().__init__(code="UNAUTHORIZED", message=message, status_code=status.HTTP_401_UNAUTHORIZED, details=details)


class ForbiddenException(AppException):
    def __init__(self, message: str = "Access forbidden", details: Optional[Dict[str, Any]] = None):
        super().__init__(code="FORBIDDEN", message=message, status_code=status.HTTP_403_FORBIDDEN, details=details)


class ConflictException(AppException):
    def __init__(self, message: str = "Resource conflict", details: Optional[Dict[str, Any]] = None):
        super().__init__(code="CONFLICT", message=message, status_code=status.HTTP_409_CONFLICT, details=details)


class ValidationException(AppException):
    def __init__(
        self,
        message: str = "Validation failed",
        details: Optional[Dict[str, Any]] = None,
        error_code: Optional[str] = None,
        code: Optional[str] = None,
    ):
        c = error_code or code or "VALIDATION_ERROR"
        super().__init__(code=c, message=message, status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, details=details)



class TooManyRequestsException(AppException):
    def __init__(self, message: str = "Rate limit exceeded", details: Optional[Dict[str, Any]] = None):
        super().__init__(code="TOO_MANY_REQUESTS", message=message, status_code=status.HTTP_429_TOO_MANY_REQUESTS, details=details)


def _format_error_response(
    code: str,
    message: str,
    details: Dict[str, Any],
    request: Request,
    status_code: int,
) -> JSONResponse:
    request_id = getattr(request.state, "request_id", None) or get_current_request_id() or "unknown"
    payload = {
        "error": {
            "code": code,
            "message": message,
            "details": details,
            "request_id": request_id,
        }
    }
    return JSONResponse(status_code=status_code, content=payload)


def register_exception_handlers(app: FastAPI) -> None:
    """Register all global exception handlers on the FastAPI application."""

    @app.exception_handler(AppException)
    async def app_exception_handler(request: Request, exc: AppException) -> JSONResponse:
        logger.warning(
            f"AppException: [{exc.code}] {exc.message}",
            extra={"error_code": exc.code, "details": exc.details, "status_code": exc.status_code},
        )
        return _format_error_response(
            code=exc.code,
            message=exc.message,
            details=exc.details,
            request=request,
            status_code=exc.status_code,
        )

    @app.exception_handler(StarletteHTTPException)
    async def http_exception_handler(request: Request, exc: StarletteHTTPException) -> JSONResponse:
        code_map = {
            400: "BAD_REQUEST",
            401: "UNAUTHORIZED",
            403: "FORBIDDEN",
            404: "NOT_FOUND",
            405: "METHOD_NOT_ALLOWED",
            409: "CONFLICT",
            422: "UNPROCESSABLE_ENTITY",
            500: "INTERNAL_SERVER_ERROR",
            502: "BAD_GATEWAY",
            503: "SERVICE_UNAVAILABLE",
        }
        code = code_map.get(exc.status_code, "HTTP_ERROR")
        message = exc.detail if isinstance(exc.detail, str) else "An HTTP error occurred"
        details = exc.detail if isinstance(exc.detail, dict) else {}
        return _format_error_response(
            code=code,
            message=message,
            details=details,
            request=request,
            status_code=exc.status_code,
        )

    @app.exception_handler(RequestValidationError)
    async def validation_exception_handler(request: Request, exc: RequestValidationError) -> JSONResponse:
        errors = []
        for err in exc.errors():
            loc = " -> ".join(str(l) for l in err.get("loc", []))
            msg = err.get("msg", "")
            errors.append({"field": loc, "message": msg, "type": err.get("type", "")})

        return _format_error_response(
            code="REQUEST_VALIDATION_ERROR",
            message="Request input validation failed",
            details={"validation_errors": errors},
            request=request,
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        )

    @app.exception_handler(Exception)
    async def unhandled_exception_handler(request: Request, exc: Exception) -> JSONResponse:
        logger.error(f"Unhandled system error: {str(exc)}", exc_info=True)
        return _format_error_response(
            code="INTERNAL_SERVER_ERROR",
            message="An unexpected server error occurred. Please contact AICTE support.",
            details={},
            request=request,
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        )
