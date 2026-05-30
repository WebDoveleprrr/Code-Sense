#!/usr/bin/env python
# backend/run.py
"""
CodeSense — Development Server Launcher
Run: python run.py
"""

import uvicorn
from app.core.config import get_settings


if __name__ == "__main__":
    settings = get_settings()
    uvicorn.run(
        "app.main:app",
        host=settings.APP_HOST,
        port=settings.APP_PORT,
        reload=settings.is_development,
        reload_dirs=["app"] if settings.is_development else None,
        reload_excludes=["uploads/*", "vector_store/*", "logs/*", "**/__pycache__/*", "**/.pytest_cache/*"] if settings.is_development else None,
        log_level=settings.LOG_LEVEL.lower(),
        access_log=False,   # handled by RequestContextMiddleware
    )
