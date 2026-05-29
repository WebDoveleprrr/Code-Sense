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


import threading

# ------------------------------------------------------------------ #
# Intercept stdlib logging so third-party libs use loguru
# ------------------------------------------------------------------ #
class _InterceptHandler(logging.Handler):
    """Route stdlib logging records into loguru."""
    _local = threading.local()

    def emit(self, record: logging.LogRecord) -> None:  # type: ignore[override]
        # Prevent logging feedback recursion loops
        if getattr(self._local, "processing", False):
            return
        self._local.processing = True
        try:
            try:
                level: str | int = logger.level(record.levelname).name
            except ValueError:
                level = record.levelno

            frame, depth = logging.currentframe(), 2
            while frame and frame.f_code.co_filename == logging.__file__:
                frame = frame.f_back  # type: ignore[assignment]
                depth += 1

            logger.opt(depth=depth, exception=record.exc_info).log(level, record.getMessage())
        finally:
            self._local.processing = False


def setup_logging() -> None:
    """Configure loguru based on app environment."""
    settings = get_settings()

    # Remove default loguru sink
    logger.remove()

    def production_formatter(record: dict[str, Any]) -> str:
        """Serialize the record to JSON and guarantee key existence for the sink."""
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
            exc = record["exception"]
            try:
                subset["exception"] = f"{exc.type.__name__}: {exc.value}"
            except Exception:
                subset["exception"] = str(exc)
        record["extra"]["serialized"] = json.dumps(subset)
        return "{extra[serialized]}\n"

    if settings.is_production:
        # JSON to stdout + rotating file in production
        logger.add(
            sys.stdout,
            format=production_formatter,
            level=settings.LOG_LEVEL,
            enqueue=True,
        )
        logger.add(
            str(settings.LOG_FILE),
            format=production_formatter,
            level=settings.LOG_LEVEL,
            rotation="50 MB",
            retention="30 days",
            compression="gz",
            enqueue=True,
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

    # Redirect stdlib loggers without duplicating or looping
    logging.basicConfig(handlers=[_InterceptHandler()], level=logging.INFO, force=True)
    for lib_logger in ("uvicorn", "uvicorn.access", "uvicorn.error", "fastapi"):
        l = logging.getLogger(lib_logger)
        l.handlers = [_InterceptHandler()]
        l.propagate = False


def get_logger(name: str = "codesense"):
    """Return a named loguru logger."""
    return logger.bind(name=name)

