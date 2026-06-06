# =============================================================================
# app/core/logging.py
# Structured logging setup using structlog.
#
# In development:  colourised console output with key=value rendering.
# In production:   JSON lines to stdout — ready for Loki / Datadog / CloudWatch.
#
# Usage throughout the app:
#   from app.core.logging import get_logger
#   logger = get_logger(__name__)
#   logger.info("video.processing.started", video_id=str(video_id), user_id=str(user_id))
#
# Every log event is a dict with at minimum:
#   timestamp, level, event, logger, service
# Plus any kwargs passed to the call site.
# =============================================================================
from __future__ import annotations

import logging
import logging.config
import sys
from typing import Any

import structlog
from structlog.types import EventDict, Processor

from app.core.config import settings


# ---------------------------------------------------------------------------
# Custom processors
# ---------------------------------------------------------------------------

def _add_service_name(
    logger: Any,        # noqa: ANN401 — structlog typing is loose
    method: str,
    event_dict: EventDict,
) -> EventDict:
    """Inject the service name into every log record."""
    event_dict["service"] = settings.APP_NAME
    event_dict["env"] = settings.APP_ENV
    return event_dict


def _drop_color_message_key(
    logger: Any,        # noqa: ANN401
    method: str,
    event_dict: EventDict,
) -> EventDict:
    """
    Uvicorn adds a 'color_message' key with ANSI escapes for its console log.
    Drop it when we're producing structured output so it doesn't pollute JSON.
    """
    event_dict.pop("color_message", None)
    return event_dict


def _reorder_keys(
    logger: Any,        # noqa: ANN401
    method: str,
    event_dict: EventDict,
) -> EventDict:
    """
    Move high-signal keys to the front of the dict so they appear first in
    JSON output — makes reading raw log lines easier.
    """
    priority = ["timestamp", "level", "event", "service", "env", "logger"]
    reordered: EventDict = {}
    for key in priority:
        if key in event_dict:
            reordered[key] = event_dict.pop(key)
    reordered.update(event_dict)
    return reordered


# ---------------------------------------------------------------------------
# Shared processors applied to every log record
# ---------------------------------------------------------------------------

_SHARED_PROCESSORS: list[Processor] = [
    structlog.contextvars.merge_contextvars,    # per-request context (request_id, user_id)
    structlog.stdlib.add_logger_name,           # adds "logger" key
    structlog.stdlib.add_log_level,             # adds "level" key
    structlog.stdlib.ExtraAdder(),              # merges logging.extra dict
    structlog.processors.TimeStamper(fmt="iso", utc=True),  # ISO-8601 UTC timestamp
    _drop_color_message_key,
    _add_service_name,
    structlog.processors.StackInfoRenderer(),   # renders stack_info= kwarg
    structlog.processors.UnicodeDecoder(),      # ensure all strings are unicode
]


def _build_renderer() -> Processor:
    """Return the appropriate final renderer based on LOG_FORMAT setting."""
    if settings.LOG_FORMAT == "json" or settings.is_production:
        return structlog.processors.JSONRenderer()
    # Dev: colourised key=value output
    return structlog.dev.ConsoleRenderer(colors=True, exception_formatter=structlog.dev.plain_traceback)


# ---------------------------------------------------------------------------
# Initialise structlog
# ---------------------------------------------------------------------------

def configure_logging() -> None:
    """
    Configure structlog and stdlib logging.
    Call once at application startup (inside lifespan in main.py).
    """
    renderer = _build_renderer()

    structlog.configure(
        processors=_SHARED_PROCESSORS + [
            # Bridge: convert structlog events to stdlib LogRecord, then render
            structlog.stdlib.ProcessorFormatter.wrap_for_formatter,
        ],
        wrapper_class=structlog.stdlib.BoundLogger,
        context_class=dict,
        logger_factory=structlog.stdlib.LoggerFactory(),
        cache_logger_on_first_use=True,
    )

    formatter = structlog.stdlib.ProcessorFormatter(
        # Processors applied to events coming *from stdlib* logging:
        foreign_pre_chain=_SHARED_PROCESSORS,
        # Final processor that formats the merged event dict:
        processors=[
            structlog.stdlib.ProcessorFormatter.remove_processors_meta,
            _reorder_keys,
            renderer,
        ],
    )

    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(formatter)

    # Configure root logger
    root_logger = logging.getLogger()
    root_logger.handlers.clear()
    root_logger.addHandler(handler)
    root_logger.setLevel(settings.LOG_LEVEL.upper())

    # Optional file handler
    if settings.LOG_FILE:
        import pathlib
        log_path = pathlib.Path(settings.LOG_FILE)
        log_path.parent.mkdir(parents=True, exist_ok=True)
        file_handler = logging.FileHandler(log_path)
        file_handler.setFormatter(formatter)
        root_logger.addHandler(file_handler)

    # Quieten noisy third-party loggers in production
    if settings.is_production:
        logging.getLogger("uvicorn.access").setLevel(logging.WARNING)
        logging.getLogger("sqlalchemy.engine").setLevel(logging.WARNING)
        logging.getLogger("celery").setLevel(logging.INFO)
        logging.getLogger("httpx").setLevel(logging.WARNING)
        logging.getLogger("httpcore").setLevel(logging.WARNING)
    else:
        # In development, show SQL queries if DB_ECHO is true
        if settings.DB_ECHO:
            logging.getLogger("sqlalchemy.engine").setLevel(logging.INFO)


def get_logger(name: str) -> structlog.stdlib.BoundLogger:
    """
    Return a bound structlog logger for *name*.

    Usage:
        logger = get_logger(__name__)
        logger.info("user.registered", user_id=user.id, email=user.email)
    """
    return structlog.get_logger(name)


# ---------------------------------------------------------------------------
# Request context helpers
# ---------------------------------------------------------------------------
# These are called from the request middleware to bind per-request values
# (request_id, user_id, path) to the structlog context variables.
# All subsequent log calls in that request automatically include them.

def bind_request_context(
    *,
    request_id: str,
    path: str,
    method: str,
    user_id: str | None = None,
) -> None:
    """Bind request-scoped context variables for structured logging."""
    ctx: dict[str, Any] = {
        "request_id": request_id,
        "http_path": path,
        "http_method": method,
    }
    if user_id:
        ctx["user_id"] = user_id
    structlog.contextvars.bind_contextvars(**ctx)


def clear_request_context() -> None:
    """Clear per-request context variables (called at end of request)."""
    structlog.contextvars.clear_contextvars()