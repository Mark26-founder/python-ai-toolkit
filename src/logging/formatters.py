"""Custom formatters for structured and console logging."""

from datetime import datetime, timezone
import json
import logging
from typing import Any, Dict
from .context import get_context


class JSONFormatter(logging.Formatter):
    """Formats log records as structured JSON strings."""

    def __init__(self, datefmt: str | None = None) -> None:
        """Initializes the JSON formatter."""
        super().__init__(datefmt=datefmt)

    def format(self, record: logging.LogRecord) -> str:
        """Formats the record as a JSON string."""
        timestamp = datetime.fromtimestamp(record.created, tz=timezone.utc).isoformat()
        log_data: Dict[str, Any] = {
            "timestamp": timestamp,
            "level": record.levelname,
            "message": record.getMessage(),
            "logger": record.name,
        }

        # Inject context metadata from contextvars
        context = get_context()
        if context:
            log_data["context"] = context

        # Format exception information if present
        if record.exc_info:
            log_data["exception"] = self.formatException(record.exc_info)

        # Capture extra fields passed to logger methods
        standard_fields = {
            "args",
            "asctime",
            "created",
            "exc_info",
            "exc_text",
            "filename",
            "funcName",
            "levelname",
            "levelno",
            "lineno",
            "module",
            "msecs",
            "message",
            "msg",
            "name",
            "pathname",
            "process",
            "processName",
            "relativeCreated",
            "stack_info",
            "thread",
            "threadName",
        }
        extra = {k: v for k, v in record.__dict__.items() if k not in standard_fields}
        if extra:
            log_data["extra"] = extra

        return json.dumps(log_data)


class ConsoleFormatter(logging.Formatter):
    """Formats log records for clean, human-readable terminal output."""

    def __init__(self, fmt: str | None = None, datefmt: str | None = None) -> None:
        """Initializes the console formatter."""
        default_fmt = "%(asctime)s [%(levelname)s] %(name)s: %(message)s"
        super().__init__(fmt=fmt or default_fmt, datefmt=datefmt)

    def format(self, record: logging.LogRecord) -> str:
        """Formats the record to plain text with appended context."""
        msg = super().format(record)

        context = get_context()
        if context:
            context_str = " | ".join(f"{k}={v}" for k, v in context.items())
            msg = f"{msg} {{{context_str}}}"

        return msg
