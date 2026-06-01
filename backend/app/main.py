# backend/app/main.py
"""
CodeSense — FastAPI Application Entry Point
"""

from __future__ import annotations

import os
from pathlib import Path
from dotenv import load_dotenv

env_path = Path(__file__).resolve().parent.parent / ".env"
load_dotenv(dotenv_path=env_path)


from contextlib import asynccontextmanager
from typing import AsyncGenerator

from fastapi import FastAPI
from fastapi.responses import JSONResponse

from app.core.config import get_settings
from app.core.exceptions import register_exception_handlers
from app_logger import setup_logging
from app.core.middleware import register_middleware


# ------------------------------------------------------------------ #
# Bootstrap logging before anything else
# ------------------------------------------------------------------ #
setup_logging()

from app_logger import logger  # noqa: E402  (after setup)


# ------------------------------------------------------------------ #
# Lifespan (startup / shutdown)
# ------------------------------------------------------------------ #

@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """Manage application lifecycle: connect DB and pre-load ML models."""
    settings = get_settings()
    logger.info("Starting {name} v{version} [{env}] …", name=settings.APP_NAME, version=settings.APP_VERSION, env=settings.APP_ENV)

    # ENV Check
    llm_provider = os.getenv("LLM_PROVIDER")
    openai_key_loaded = bool(os.getenv("OPENAI_API_KEY"))
    logger.info("[ENV CHECK] LLM_PROVIDER={provider} OPENAI_API_KEY loaded={key}", provider=llm_provider, key=openai_key_loaded)

    # Startup validation
    from app.ml.llm_client import validate_startup
    try:
        await validate_startup()
    except Exception as exc:
        logger.exception("LLM Startup Validation Failed")

    # Database
    from app.db.mongodb import connect_db
    await connect_db()

    logger.info("{name} is ready to serve requests.", name=settings.APP_NAME)
    yield

    # Shutdown
    from app.db.mongodb import disconnect_db
    await disconnect_db()
    logger.info("{name} shutdown complete.", name=settings.APP_NAME)


# ------------------------------------------------------------------ #
# Application factory
# ------------------------------------------------------------------ #

def create_app() -> FastAPI:
    settings = get_settings()

    app = FastAPI(
        title=settings.APP_NAME,
        version=settings.APP_VERSION,
        description=(
            "CodeSense — AI-powered semantic repository intelligence platform. "
            "Upload GitHub repos or ZIPs, then search, query, and analyse codebases with AI."
        ),
        docs_url="/docs",
        redoc_url="/redoc",
        openapi_url="/openapi.json",
        lifespan=lifespan,
    )

    # Middleware (order is important — see middleware.py)
    register_middleware(app)

    # Exception handlers
    register_exception_handlers(app)

    # API routes
    from app.api.router import api_router
    app.include_router(api_router)

    # Root redirect
    @app.get("/", include_in_schema=False)
    async def root():
        return JSONResponse({"service": settings.APP_NAME, "version": settings.APP_VERSION, "docs": "/docs"})

    return app


app = create_app()
