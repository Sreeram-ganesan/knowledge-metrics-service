"""Core Logging Configuration.

Provides application-wide logging setup including:
- JSON formatter for production (log aggregators)
- Console formatter for development (human-readable)
- Centralized logging configuration

This is core infrastructure, not HTTP middleware.
For request/response logging, see app.middleware.logging.
"""

import json
import logging
import sys
from datetime import datetime, timezone

from app.core.config import Settings


class JSONFormatter(logging.Formatter):
    """JSON formatter for structured logging in production.

    Outputs logs as single-line JSON objects for easy parsing by
    log aggregators (Datadog, ELK, CloudWatch, etc.).

    Example output:
        {"timestamp": "2026-01-10T14:30:00+00:00", "level": "INFO", ...}
    """

    def format(self, record: logging.LogRecord) -> str:
        log_data = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
        }

        # Add exception info if present
        if record.exc_info:
            log_data["exception"] = self.formatException(record.exc_info)

        # Add extra fields if any (e.g., request_id from contextvars)
        request_id = getattr(record, "request_id", None)
        if request_id is not None:
            log_data["request_id"] = request_id

        return json.dumps(log_data, default=str)


class ConsoleFormatter(logging.Formatter):
    """Human-readable formatter for development.

    Format: 2026-01-10 14:30:00 INFO  app.request: [abc-123] → GET /api/v1/metrics
    """

    FORMAT = "%(asctime)s %(levelname)-5s %(name)s: %(message)s"
    DATE_FORMAT = "%Y-%m-%d %H:%M:%S"

    def __init__(self) -> None:
        super().__init__(fmt=self.FORMAT, datefmt=self.DATE_FORMAT)


def setup_logging(settings: Settings) -> None:
    """Configure application logging based on settings.

    This should be called once at application startup, before any
    other initialization that might emit logs.

    Usage:
        from app.core.config import get_settings
        from app.core.logging import setup_logging

        settings = get_settings()
        setup_logging(settings)

    Args:
        settings: Application settings instance containing log configuration.
    """
    # Get the root logger
    root_logger = logging.getLogger()
    root_logger.setLevel(getattr(logging, settings.effective_log_level))

    # Remove existing handlers to avoid duplicates on reload
    root_logger.handlers.clear()

    # Create stdout handler
    handler = logging.StreamHandler(sys.stdout)
    handler.setLevel(getattr(logging, settings.effective_log_level))

    # Choose formatter based on settings
    if settings.effective_log_format == "json":
        handler.setFormatter(JSONFormatter())
    else:
        handler.setFormatter(ConsoleFormatter())

    root_logger.addHandler(handler)

    # Reduce noise from third-party libraries
    logging.getLogger("uvicorn.access").setLevel(logging.WARNING)
    logging.getLogger("uvicorn.error").setLevel(logging.INFO)
    logging.getLogger("httpx").setLevel(logging.WARNING)
    logging.getLogger("httpcore").setLevel(logging.WARNING)
    logging.getLogger("openai").setLevel(logging.WARNING)

    # Log the configuration (useful for debugging startup issues)
    logger = logging.getLogger("app.core")
    logger.info(
        f"Logging configured: level={settings.effective_log_level}, "
        f"format={settings.effective_log_format}, env={settings.environment}"
    )


def get_logger(name: str) -> logging.Logger:
    """Get a logger with the given name.

    Convenience function for getting loggers with consistent naming.

    Usage:
        from app.core.logging import get_logger
        logger = get_logger(__name__)
        logger.info("Something happened")

    Args:
        name: Logger name, typically __name__ of the calling module.

    Returns:
        Configured logger instance.
    """
    return logging.getLogger(name)
