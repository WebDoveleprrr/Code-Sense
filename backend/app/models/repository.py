# backend/app/models/repository.py
"""
CodeSense — Repository Beanie Document Model (v2)
Adds repo_metadata field for storing aggregated parse statistics.
"""

from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional

from beanie import Document, Indexed
from pydantic import Field


class RepoSource(str, Enum):
    GITHUB = "github"
    ZIP = "zip"


class RepoStatus(str, Enum):
    PENDING = "pending"
    PROCESSING = "processing"
    READY = "ready"
    FAILED = "failed"


class RepositoryDocument(Document):
    """Persisted metadata for every repository ingested into CodeSense."""

    # Identifiers
    name: str
    owner: Optional[str] = None
    source: RepoSource
    github_url: Optional[str] = None
    zip_filename: Optional[str] = None

    # Processing state
    status: RepoStatus = RepoStatus.PENDING
    error_message: Optional[str] = None

    # Derived metadata
    language_breakdown: Dict[str, int] = Field(default_factory=dict)
    total_files: int = 0
    total_chunks: int = 0
    total_tokens: int = 0
    faiss_index_path: Optional[str] = None

    # v2 — Aggregated parse statistics
    # {total_lines, total_functions, total_classes, total_imports, files: [...]}
    repo_metadata: Dict[str, Any] = Field(default_factory=dict)

    # Timestamps
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    indexed_at: Optional[datetime] = None

    class Settings:
        name = "repositories"
        indexes = [
            [("name", 1), ("owner", 1)],
            [("status", 1)],
            [("created_at", -1)],
        ]
