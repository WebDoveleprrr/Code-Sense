# backend/app/db/mongodb.py
"""
CodeSense — MongoDB Connection Manager
Provides an async Motor client with Beanie ODM initialisation.
"""

from __future__ import annotations

from typing import Optional

import motor.motor_asyncio
from beanie import init_beanie
from app_logger import logger
from motor.motor_asyncio import AsyncIOMotorClient, AsyncIOMotorDatabase

from app.core.config import get_settings

# ------------------------------------------------------------------ #
# Module-level client singleton
# ------------------------------------------------------------------ #
_client: Optional[AsyncIOMotorClient] = None  # type: ignore[type-arg]
_database: Optional[AsyncIOMotorDatabase] = None  # type: ignore[type-arg]


async def connect_db() -> None:
    """
    Open a Motor connection and initialise Beanie with all document models.
    Called from the FastAPI lifespan startup hook.
    """
    global _client, _database

    settings = get_settings()

    logger.info("Connecting to MongoDB at {uri} …", uri=_redact_uri(settings.MONGODB_URI))

    _client = motor.motor_asyncio.AsyncIOMotorClient(
        settings.MONGODB_URI,
        serverSelectionTimeoutMS=5_000,
        connectTimeoutMS=5_000,
        socketTimeoutMS=30_000,
    )
    _database = _client[settings.MONGODB_DB_NAME]

    # ---------------------------------------------------------------- #
    # Import document models here — Beanie needs them registered upfront
    # ---------------------------------------------------------------- #
    from app.models.repository import RepositoryDocument
    from app.models.chunk import ChunkDocument
    from app.models.search_log import SearchLogDocument
    from app.models.dependency_graph import DependencyGraphDocument
    from app.models.review_report import ReviewReportDocument
    from app.models.user import UserDocument

    await init_beanie(
        database=_database,
        document_models=[
            RepositoryDocument,
            ChunkDocument,
            SearchLogDocument,
            DependencyGraphDocument,
            ReviewReportDocument,
            UserDocument,
        ],
    )

    # Verify the connection is reachable
    await _client.admin.command("ping")
    logger.info("MongoDB connection established — database: '{db}'", db=settings.MONGODB_DB_NAME)


async def disconnect_db() -> None:
    """
    Close the Motor connection.
    Called from the FastAPI lifespan shutdown hook.
    """
    global _client, _database

    if _client is not None:
        _client.close()
        _client = None
        _database = None
        logger.info("MongoDB connection closed.")


def get_database() -> AsyncIOMotorDatabase:  # type: ignore[type-arg]
    """
    Return the active database handle.
    Raises RuntimeError if connect_db() has not been called.
    """
    if _database is None:
        raise RuntimeError("Database is not initialised. Call connect_db() first.")
    return _database


def get_collection(name: str):  # type: ignore[return]
    """Convenience shortcut to fetch a raw Motor collection."""
    return get_database()[name]


# ------------------------------------------------------------------ #
# Helpers
# ------------------------------------------------------------------ #

def _redact_uri(uri: str) -> str:
    """Hide credentials from log output."""
    try:
        from urllib.parse import urlparse, urlunparse

        parsed = urlparse(uri)
        if parsed.password:
            netloc = f"{parsed.username}:***@{parsed.hostname}"
            if parsed.port:
                netloc += f":{parsed.port}"
            return urlunparse(parsed._replace(netloc=netloc))
    except Exception:
        pass
    return uri
