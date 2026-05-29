# backend/app/core/logging.py
"""
CodeSense — Structured Logging
Uses loguru with a JSON sink in production and colourised output in development.
"""

from __future__ import annotations

import logging
import sys
from pathlib import Path
from typing import Any

from loguru import logger

from app.core.config import get_settings


# ------------------------------------------------------------------ #
# Intercept stdlib logging so third-party libs use loguru
# ------------------------------------------------------------------ #
class _InterceptHandler(logging.Handler):
    """Route stdlib logging records into loguru."""

    def emit(self, record: logging.LogRecord) -> None:  # type: ignore[override]
        try:
            level: str | int = logger.level(record.levelname).name
        except ValueError:
            level = record.levelno

        frame, depth = logging.currentframe(), 2
        while frame and frame.f_code.co_filename == logging.__file__:
            frame = frame.f_back  # type: ignore[assignment]
            depth += 1

        logger.opt(depth=depth, exception=record.exc_info).log(level, record.getMessage())


def _json_serialiser(record: dict[str, Any]) -> str:
    """Custom JSON format for production logs."""
    import json

    subset = {
        "timestamp": record["time"].isoformat(),
        "level": record["level"].name,
        "logger": record["name"],
        "message": record["message"],
        "module": record["module"],
        "function": record["function"],
        "line": record["line"],
    }
    if record["exception"]:
        subset["exception"] = str(record["exception"])
    return json.dumps(subset)


def setup_logging() -> None:
    """Configure loguru based on app environment."""
    settings = get_settings()

    # Remove default loguru sink
    logger.remove()

    if settings.is_production:
        # JSON to stdout + rotating file in production
        logger.add(
            sys.stdout,
            format=_json_serialiser,  # type: ignore[arg-type]
            level=settings.LOG_LEVEL,
            serialize=False,
            enqueue=True,
        )
        logger.add(
            str(settings.LOG_FILE),
            format=_json_serialiser,  # type: ignore[arg-type]
            level=settings.LOG_LEVEL,
            rotation="50 MB",
            retention="30 days",
            compression="gz",
            enqueue=True,
            serialize=False,
        )
    else:
        # Pretty colourised output in development
        fmt = (
            "<green>{time:YYYY-MM-DD HH:mm:ss}</green> | "
            "<level>{level: <8}</level> | "
            "<cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> — "
            "<level>{message}</level>"
        )
        logger.add(sys.stderr, format=fmt, level=settings.LOG_LEVEL, colorize=True)
        logger.add(
            str(settings.LOG_FILE),
            format=fmt,
            level=settings.LOG_LEVEL,
            rotation="10 MB",
            retention="7 days",
            enqueue=True,
        )

    # Redirect stdlib loggers
    logging.basicConfig(handlers=[_InterceptHandler()], level=0, force=True)
    for lib_logger in ("uvicorn", "uvicorn.access", "uvicorn.error", "fastapi"):
        logging.getLogger(lib_logger).handlers = [_InterceptHandler()]


def get_logger(name: str = "codesense"):
    """Return a named loguru logger."""
    return logger.bind(name=name)
