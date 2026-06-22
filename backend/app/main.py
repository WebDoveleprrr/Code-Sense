# backend/app/main.py --- starts the whole backend
"""
CodeSense — FastAPI Application Entry Point
"""

from __future__ import annotations

import os
from pathlib import Path
from dotenv import load_dotenv

env_path = Path(__file__).resolve().parent.parent / ".env"
load_dotenv(dotenv_path=env_path)  #load env variables(secrets)


from contextlib import asynccontextmanager
from typing import AsyncGenerator

from fastapi import FastAPI
from fastapi.responses import JSONResponse

from app.core.config import get_settings
from app.core.exceptions import register_exception_handlers
from app_logger import setup_logging
from app.core.middleware import register_middleware

setup_logging() #Configure logging for entire application.

from app_logger import logger  # noqa: E402  (after setup)


# PURPOSE:
# Controls the startup and teardown lifecycle of the entire backend.
#
# WHY IT EXISTS:
# In FastAPI, we need to guarantee that databases are connected and ML
# models are validated *before* the application starts accepting HTTP 
# traffic. The `lifespan` context manager handles this asynchronously.
#
# ARCHITECTURE NOTE:
# `yield` marks the point where the server is officially running and routing 
# requests. Code before `yield` is startup; code after `yield` is shutdown.
#
# INTERVIEW NOTE:
# "How do you handle graceful degradation on startup?"
#
# GOOD ANSWER:
# "I use FastAPI's lifespan events. During startup, we validate the LLM provider
# keys and test the MongoDB connection. If a non-critical system (like an external 
# LLM) is down, we log a warning and fall back to local stubbing rather than 
# crashing the container, ensuring the app remains partially available."
# ─────────────────────────────────────────────

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
        # Pings the AI providers to verify they are online.
        # Catches exceptions so the app doesn't die on boot if Ollama is asleep.
        await validate_startup()
    except Exception as exc:
        logger.exception("LLM Startup Validation Failed")

    # Database
    from app.db.mongodb import connect_db
    # Initializes the Beanie ODM models (RepositoryDocument, ChunkDocument)
    await connect_db()

    logger.info("{name} is ready to serve requests.", name=settings.APP_NAME)
    
    # ------------------------------------------
    # Server runs here
    yield
    # ------------------------------------------

    # Shutdown
    from app.db.mongodb import disconnect_db
    await disconnect_db()
    logger.info("{name} shutdown complete.", name=settings.APP_NAME)


# ─────────────────────────────────────────────
# LINES 75-108
# PURPOSE:
# The Factory function that creates the FastAPI application instance.
#
# WHY IT EXISTS:
# Using an application factory pattern (instead of defining `app = FastAPI()` 
# globally at the top) prevents circular import issues and makes the app
# easier to instantiate dynamically for Pytest unit testing.
#
# DEPENDS ON:
# `middleware.py` (CORS), `exceptions.py` (Global error handlers),
# `api_router.py` (Endpoints).
# ─────────────────────────────────────────────

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
    # Handles CORS (Cross-Origin Resource Sharing) so the React frontend 
    # can communicate with this backend across different ports/domains.
    register_middleware(app)

    # Exception handlers
    # Intercepts raw Python exceptions (e.g., ValueError, PyMongoError) and 
    # formats them into clean, predictable JSON responses for the frontend.
    register_exception_handlers(app)

    # API routes
    # Pulls in all route definitions from api/router.py (/auth, /repos, /qa, etc.)
    from app.api.router import api_router
    app.include_router(api_router)

    # Root redirect
    @app.get("/", include_in_schema=False)
    async def root():
        return JSONResponse({"service": settings.APP_NAME, "version": settings.APP_VERSION, "docs": "/docs"})

    return app


app = create_app()