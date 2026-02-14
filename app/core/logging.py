"""
Logging configuration for the application.
Uses structlog for structured logging (JSON in production, colorful in dev).
"""

import logging
import sys
from typing import Any

import structlog
from asgi_correlation_id import correlation_id

from app.config import get_settings

settings = get_settings()


def configure_logging() -> None:
    """Configure structured logging."""
    shared_processors: list[Any] = [
        structlog.contextvars.merge_contextvars,
        structlog.stdlib.add_logger_name,
        structlog.stdlib.add_log_level,
        structlog.stdlib.PositionalArgumentsFormatter(),
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.StackInfoRenderer(),
        structlog.processors.UnicodeDecoder(),
    ]

    # Add correlation ID if available
    def add_correlation_id(logger, method_name, event_dict):
        request_id = correlation_id.get()
        if request_id:
            event_dict["request_id"] = request_id
        return event_dict

    shared_processors.insert(0, add_correlation_id)

    if settings.ENVIRONMENT == "production":
        # JSON logs for production (Splunk, ELK, Datadog compatible)
        processors = shared_processors + [
            structlog.processors.format_exc_info,
            structlog.processors.JSONRenderer(),
        ]
    else:
        # Colorful logs for local development
        processors = shared_processors + [
            structlog.dev.ConsoleRenderer(),
        ]

    # Configure structlog
    structlog.configure(
        processors=processors,
        logger_factory=structlog.stdlib.LoggerFactory(),
        wrapper_class=structlog.stdlib.BoundLogger,
        cache_logger_on_first_use=True,
    )

    # Configure standard library logging to use structlog
    formatter = structlog.stdlib.ProcessorFormatter(
        foreign_pre_chain=shared_processors,
        processors=[
            structlog.stdlib.ProcessorFormatter.remove_processors_meta,
            structlog.dev.ConsoleRenderer() if settings.ENVIRONMENT != "production" else structlog.processors.JSONRenderer(),
        ],
    )

    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(formatter)
    
    root_logger = logging.getLogger()
    root_logger.addHandler(handler)
    root_logger.setLevel(settings.LOG_LEVEL.upper() if hasattr(settings, "LOG_LEVEL") else "INFO")

    # Silence uvicorn access logs to avoid duplicate/unstructured logs if needed
    # logging.getLogger("uvicorn.access").disabled = True
