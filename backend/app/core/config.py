# backend/app/core/config.py
"""
CodeSense — Centralised Settings
All config is loaded from environment variables / .env file.
"""

from __future__ import annotations

import os
from functools import lru_cache
from pathlib import Path
from typing import List

from pydantic import AnyHttpUrl, Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # ------------------------------------------------------------------ #
    # Application
    # ------------------------------------------------------------------ #
    APP_NAME: str = "CodeSense"
    APP_ENV: str = "development"
    APP_VERSION: str = "1.0.0"
    APP_HOST: str = "0.0.0.0"
    APP_PORT: int = 8000
    DEBUG: bool = True

    # ------------------------------------------------------------------ #
    # MongoDB
    # ------------------------------------------------------------------ #
    MONGODB_URI: str = "mongodb://localhost:27017"
    MONGODB_DB_NAME: str = "codesense"

    # ------------------------------------------------------------------ #
    # GitHub
    # ------------------------------------------------------------------ #
    GITHUB_TOKEN: str = ""

    # ------------------------------------------------------------------ #
    # ML / Embeddings
    # ------------------------------------------------------------------ #
    EMBEDDING_MODEL: str = "all-MiniLM-L6-v2"
    EMBEDDING_DEVICE: str = "cpu"
    EMBEDDING_BATCH_SIZE: int = 32

    # ------------------------------------------------------------------ #
    # FAISS / Vector Store
    # ------------------------------------------------------------------ #
    VECTOR_STORE_DIR: Path = Path("./vector_store/indices")
    VECTOR_DIM: int = 384

    # ------------------------------------------------------------------ #
    # File Uploads
    # ------------------------------------------------------------------ #
    UPLOAD_DIR: Path = Path("./uploads")
    MAX_UPLOAD_SIZE_MB: int = 200

    @property
    def MAX_UPLOAD_SIZE_BYTES(self) -> int:
        return self.MAX_UPLOAD_SIZE_MB * 1024 * 1024

    # ------------------------------------------------------------------ #
    # Chunking
    # ------------------------------------------------------------------ #
    CHUNK_SIZE: int = 512
    CHUNK_OVERLAP: int = 64

    # ------------------------------------------------------------------ #
    # Security
    # ------------------------------------------------------------------ #
    SECRET_KEY: str = "change_this_secret"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60

    # ------------------------------------------------------------------ #
    # CORS
    # ------------------------------------------------------------------ #
    CORS_ORIGINS: str = "http://localhost:3000,http://localhost:5173"

    @property
    def CORS_ORIGINS_LIST(self) -> List[str]:
        return [o.strip() for o in self.CORS_ORIGINS.split(",") if o.strip()]

    # ------------------------------------------------------------------ #
    # Logging
    # ------------------------------------------------------------------ #
    LOG_LEVEL: str = "INFO"
    LOG_FILE: Path = Path("./logs/codesense.log")

    # ------------------------------------------------------------------ #
    # Derived helpers
    # ------------------------------------------------------------------ #
    @property
    def is_production(self) -> bool:
        return self.APP_ENV.lower() == "production"

    @property
    def is_development(self) -> bool:
        return self.APP_ENV.lower() == "development"

    def ensure_dirs(self) -> None:
        """Create required runtime directories if they do not exist."""
        for directory in [self.UPLOAD_DIR, self.VECTOR_STORE_DIR, self.LOG_FILE.parent]:
            Path(directory).mkdir(parents=True, exist_ok=True)


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    """Return a cached singleton Settings instance."""
    settings = Settings()
    settings.ensure_dirs()
    return settings
