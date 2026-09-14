"""
app/core/logging.py

Production-ready structured logging configuration for CommerceFlow AI.

Features:
  - Structured JSON logging for production environments
  - Human-readable colored logging for development
  - Rotating log files (prevents disk overflow)
  - Request/response logging middleware
  - Error logging with full tracebacks
  - Separate loggers per module

Usage:
    from app.core.logging import get_logger
    logger = get_logger(__name__)
    logger.info("Processing order", extra={"order_id": "ORD-123"})
"""

import json
import logging
import logging.handlers
import os
import sys
import time
import uuid
from collections.abc import Awaitable, Callable
from typing import Any

from fastapi import Request, Response

from app.config.settings import get_settings

settings = get_settings()


# ── Custom JSON Formatter ─────────────────────────────────────────────────────


class JSONFormatter(logging.Formatter):
    """
    Formats log records as structured JSON.
    Used in staging and production environments.
    """

    def format(self, record: logging.LogRecord) -> str:
        log_entry: dict[str, Any] = {
            "timestamp": self.formatTime(record, self.datefmt),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
            "module": record.module,
            "function": record.funcName,
            "line": record.lineno,
        }

        # Attach extra fields (e.g., request_id, user_id, order_id)
        if hasattr(record, "request_id"):
            log_entry["request_id"] = record.request_id
        if hasattr(record, "user_id"):
            log_entry["user_id"] = record.user_id
        if hasattr(record, "duration_ms"):
            log_entry["duration_ms"] = record.duration_ms

        # Attach exception info
        if record.exc_info:
            log_entry["exception"] = self.formatException(record.exc_info)

        return json.dumps(log_entry, ensure_ascii=False)


# ── Development Colored Formatter ─────────────────────────────────────────────

LEVEL_COLORS = {
    "DEBUG": "\033[36m",     # Cyan
    "INFO": "\033[32m",      # Green
    "WARNING": "\033[33m",   # Yellow
    "ERROR": "\033[31m",     # Red
    "CRITICAL": "\033[35m",  # Magenta
}
RESET = "\033[0m"


class ColoredFormatter(logging.Formatter):
    """
    Human-readable colored formatter for development.
    """

    def format(self, record: logging.LogRecord) -> str:
        color = LEVEL_COLORS.get(record.levelname, "")
        record.levelname = f"{color}{record.levelname:<8}{RESET}"
        return super().format(record)


# ── Logger Factory ────────────────────────────────────────────────────────────


def setup_logging() -> None:
    """
    Configure the root logging system.
    Called once at application startup from main.py lifespan.
    """
    log_level = getattr(logging, settings.LOG_LEVEL, logging.INFO)

    # Ensure log directory exists
    log_dir = os.path.dirname(settings.LOG_FILE)
    if log_dir:
        os.makedirs(log_dir, exist_ok=True)

    # Choose formatter based on environment
    if settings.is_production:
        console_formatter = JSONFormatter()
    else:
        console_formatter = ColoredFormatter(
            fmt="%(asctime)s | %(levelname)s | %(name)s:%(lineno)d | %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S",
        )

    file_formatter = JSONFormatter()

    # ── Console Handler ───────────────────────────────────────────────────────
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(log_level)
    console_handler.setFormatter(console_formatter)

    # ── Rotating File Handler ─────────────────────────────────────────────────
    file_handler = logging.handlers.RotatingFileHandler(
        filename=settings.LOG_FILE,
        maxBytes=settings.LOG_MAX_BYTES,
        backupCount=settings.LOG_BACKUP_COUNT,
        encoding="utf-8",
    )
    file_handler.setLevel(log_level)
    file_handler.setFormatter(file_formatter)

    # ── Root Logger ───────────────────────────────────────────────────────────
    root_logger = logging.getLogger()
    root_logger.setLevel(log_level)
    root_logger.handlers.clear()
    root_logger.addHandler(console_handler)
    root_logger.addHandler(file_handler)

    # ── Silence noisy third-party loggers ────────────────────────────────────
    logging.getLogger("uvicorn.access").setLevel(logging.WARNING)
    logging.getLogger("sqlalchemy.engine").setLevel(
        logging.INFO if settings.DEBUG else logging.WARNING
    )
    logging.getLogger("httpx").setLevel(logging.WARNING)
    logging.getLogger("httpcore").setLevel(logging.WARNING)

    logger = get_logger(__name__)
    logger.info(
        "Logging configured",
        extra={
            "environment": settings.ENVIRONMENT,
            "log_level": settings.LOG_LEVEL,
            "log_file": settings.LOG_FILE,
        },
    )


def get_logger(name: str) -> logging.Logger:
    """
    Returns a named logger.

    Usage:
        logger = get_logger(__name__)
        logger.info("Something happened", extra={"user_id": 42})
    """
    return logging.getLogger(name)


# ── Request Logging Middleware ─────────────────────────────────────────────────

logger = get_logger("commerceflow.requests")


async def log_requests_middleware(
    request: Request,
    call_next: Callable[[Request], Awaitable[Response]],
) -> Response:
    """
    ASGI middleware that logs every HTTP request with:
    - Request ID (UUID, for tracing)
    - Method, path, client IP
    - Response status code
    - Duration in milliseconds

    Attach to FastAPI in main.py:
        app.middleware("http")(log_requests_middleware)
    """
    request_id = str(uuid.uuid4())[:8]
    start_time = time.perf_counter()

    # Attach request_id to request state for use in route handlers
    request.state.request_id = request_id

    # Log incoming request
    logger.info(
        f"-> {request.method} {request.url.path}",
        extra={
            "request_id": request_id,
            "method": request.method,
            "path": request.url.path,
            "client_ip": request.client.host if request.client else "unknown",
            "query_params": str(request.query_params),
        },
    )

    try:
        response = await call_next(request)
    except Exception as exc:
        duration_ms = round((time.perf_counter() - start_time) * 1000, 2)
        logger.error(
            f"X {request.method} {request.url.path} - UNHANDLED EXCEPTION",
            extra={
                "request_id": request_id,
                "duration_ms": duration_ms,
            },
            exc_info=exc,
        )
        raise

    duration_ms = round((time.perf_counter() - start_time) * 1000, 2)

    # Log response
    log_fn = logger.warning if response.status_code >= 400 else logger.info
    log_fn(
        f"<- {response.status_code} {request.method} {request.url.path} [{duration_ms}ms]",
        extra={
            "request_id": request_id,
            "status_code": response.status_code,
            "duration_ms": duration_ms,
        },
    )

    # Attach request ID to response headers (useful for debugging)
    response.headers["X-Request-ID"] = request_id
    return response
