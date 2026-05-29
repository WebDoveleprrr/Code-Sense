# backend/app/api/v1/health.py
"""
CodeSense — Health Check Endpoints
"""

from __future__ import annotations

from datetime import datetime

from fastapi import APIRouter, Depends
from pydantic import BaseModel

from app.core.config import Settings, get_settings

router = APIRouter()


class HealthResponse(BaseModel):
    status: str
    app: str
    version: str
    environment: str
    timestamp: str


@router.get("", response_model=HealthResponse, summary="Basic liveness probe")
async def health_check(settings: Settings = Depends(get_settings)) -> HealthResponse:
    return HealthResponse(
        status="ok",
        app=settings.APP_NAME,
        version=settings.APP_VERSION,
        environment=settings.APP_ENV,
        timestamp=datetime.utcnow().isoformat() + "Z",
    )


@router.get("/db", summary="Database readiness probe")
async def db_health():
    """Ping MongoDB and return connection status."""
    from app.db.mongodb import get_database

    try:
        db = get_database()
        await db.command("ping")
        return {"status": "ok", "database": "connected"}
    except Exception as exc:
        return {"status": "error", "database": str(exc)}
