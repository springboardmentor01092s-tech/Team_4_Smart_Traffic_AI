"""
app/core/logging.py

Structured logging configuration for the TrafficVision AI backend.

Sets up Python's standard logging with a consistent format suitable
for both local development (human-readable) and production (JSON-ready).
"""
import logging
import sys

from app.core.config import settings


def setup_logging() -> None:
    """
    Configure application-wide logging.

    Call this once at startup (inside main.py lifespan).
    All subsequent `logging.getLogger(...)` calls will inherit
    this configuration.
    """
    log_level = getattr(logging, settings.log_level.upper(), logging.INFO)

    # Remove all existing handlers to avoid duplicate log entries
    # when setup_logging is called multiple times (e.g. in tests)
    root_logger = logging.getLogger()
    for handler in root_logger.handlers[:]:
        root_logger.removeHandler(handler)

    # ─── Formatter ───────────────────────────────────────────────────────────
    if settings.is_production:
        # Production: structured format that is easy to parse by log aggregators
        fmt = (
            "%(asctime)s | %(levelname)-8s | %(name)s | "
            "%(filename)s:%(lineno)d | %(message)s"
        )
    else:
        # Development: coloured, concise format for readability
        fmt = "%(asctime)s | %(levelname)-8s | %(name)-40s | %(message)s"

    formatter = logging.Formatter(fmt=fmt, datefmt="%Y-%m-%d %H:%M:%S")

    # ─── Handler ─────────────────────────────────────────────────────────────
    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(formatter)
    handler.setLevel(log_level)

    # ─── Root Logger ─────────────────────────────────────────────────────────
    root_logger.setLevel(log_level)
    root_logger.addHandler(handler)

    # Suppress noisy third-party loggers in non-debug mode
    if not settings.debug:
        logging.getLogger("uvicorn.access").setLevel(logging.WARNING)
        logging.getLogger("sqlalchemy.engine").setLevel(logging.WARNING)

    logger = logging.getLogger(__name__)
    logger.info(
        "Logging configured | level=%s | env=%s",
        settings.log_level,
        settings.app_env,
    )


def get_logger(name: str) -> logging.Logger:
    """
    Return a named logger.

    Convenience wrapper so modules don't import `logging` directly.

    Usage:
        from app.core.logging import get_logger
        logger = get_logger(__name__)
    """
    return logging.getLogger(name)
