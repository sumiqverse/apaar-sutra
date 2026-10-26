"""Structured JSON logging with request context propagation."""

import json
import logging
import sys
from contextvars import ContextVar
from datetime import datetime, timezone
from typing import Any, Dict

# Context variable storing the current request ID
request_id_ctx: ContextVar[str] = ContextVar("request_id_ctx", default="")


def get_current_request_id() -> str:
    """Retrieve the current request ID from context."""
    return request_id_ctx.get()


def set_current_request_id(req_id: str) -> None:
    """Store the request ID into context."""
    request_id_ctx.set(req_id)


class JSONFormatter(logging.Formatter):
    """Formats log records into structured JSON strings."""

    def format(self, record: logging.LogRecord) -> str:
        log_payload: Dict[str, Any] = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
            "request_id": get_current_request_id(),
        }

        # Include file/line location on WARNING or above
        if record.levelno >= logging.WARNING:
            log_payload["source"] = f"{record.filename}:{record.lineno}"

        # Capture exception details
        if record.exc_info:
            log_payload["exception"] = self.formatException(record.exc_info)

        # Include any extra fields passed in record.__dict__
        standard_attrs = {
            "name", "msg", "args", "levelname", "levelno", "pathname", "filename",
            "module", "exc_info", "exc_text", "stack_info", "lineno", "funcName",
            "created", "msecs", "relativeCreated", "thread", "threadName",
            "processName", "process", "message"
        }
        extras = {k: v for k, v in record.__dict__.items() if k not in standard_attrs}
        if extras:
            log_payload["extra"] = extras

        return json.dumps(log_payload, default=str)


def setup_logging(log_level: str = "INFO", log_format: str = "json") -> None:
    """Initialize root logger with appropriate handlers and formatters."""
    numeric_level = getattr(logging, log_level.upper(), logging.INFO)
    root_logger = logging.getLogger()
    root_logger.setLevel(numeric_level)

    # Clear existing handlers to avoid duplicates
    for handler in root_logger.handlers[:]:
        root_logger.removeHandler(handler)

    stream_handler = logging.StreamHandler(sys.stdout)
    if log_format.lower() == "json":
        stream_handler.setFormatter(JSONFormatter())
    else:
        text_format = "%(asctime)s [%(levelname)s] [%(name)s] %(message)s"
        stream_handler.setFormatter(logging.Formatter(text_format))

    root_logger.addHandler(stream_handler)

    # Quiet overly verbose external loggers
    logging.getLogger("uvicorn.access").setLevel(logging.WARNING)
    logging.getLogger("uvicorn.error").setLevel(logging.INFO)
