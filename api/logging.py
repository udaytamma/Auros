from __future__ import annotations

import json
import logging
import sys
import uuid
from contextvars import ContextVar
from datetime import datetime, UTC

# Context variable for correlation ID
correlation_id_var: ContextVar[str] = ContextVar("correlation_id", default="")


def get_correlation_id() -> str:
    """Get current correlation ID or generate new one."""
    cid = correlation_id_var.get()
    if not cid:
        cid = str(uuid.uuid4())[:8]
        correlation_id_var.set(cid)
    return cid


def set_correlation_id(cid: str) -> None:
    """Set correlation ID for current context."""
    correlation_id_var.set(cid)


class JsonFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        payload = {
            "timestamp": datetime.now(UTC).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "correlation_id": get_correlation_id(),
            "message": record.getMessage(),
        }
        # Add extra fields if present
        if hasattr(record, "extra_fields"):
            payload.update(record.extra_fields)
        if record.exc_info:
            payload["exception"] = self.formatException(record.exc_info)
        return json.dumps(payload)


class StructuredLogger(logging.Logger):
    """Logger that supports structured logging with extra fields."""

    def _log_with_extra(self, level: int, msg: str, **kwargs):
        extra_fields = kwargs.pop("extra", {})
        super().log(level, msg, extra={"extra_fields": extra_fields}, **kwargs)

    def info_structured(self, msg: str, **extra):
        self._log_with_extra(logging.INFO, msg, extra=extra)

    def warning_structured(self, msg: str, **extra):
        self._log_with_extra(logging.WARNING, msg, extra=extra)

    def error_structured(self, msg: str, **extra):
        self._log_with_extra(logging.ERROR, msg, extra=extra)


def configure_logging() -> StructuredLogger:
    logging.setLoggerClass(StructuredLogger)
    logger = logging.getLogger("auros")
    if logger.handlers:
        return logger
    logger.setLevel(logging.INFO)
    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(JsonFormatter())
    logger.addHandler(handler)
    logger.propagate = False
    return logger
