# backend/app/models/search_log.py
"""
CodeSense — Search / Q&A Audit Log Document Model
"""

from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional

from beanie import Document
from pydantic import Field


class QueryType(str, Enum):
    SEMANTIC_SEARCH = "semantic_search"
    QA = "qa"
    EXPLAIN = "explain"
    DEPENDENCY = "dependency"
    ARCHITECTURE = "architecture"


class SearchLogDocument(Document):
    """Audit trail for every query processed by CodeSense."""

    repo_id: str
    query_type: QueryType
    query: str

    # Results summary
    top_k: int = 5
    result_count: int = 0
    result_file_paths: List[str] = Field(default_factory=list)

    # Q&A fields (populated when query_type == QA)
    answer: Optional[str] = None
    context_chunks_used: int = 0

    # Performance
    latency_ms: float = 0.0

    # Timestamps
    created_at: datetime = Field(default_factory=datetime.utcnow)

    class Settings:
        name = "search_logs"
        indexes = [
            [("repo_id", 1)],
            [("query_type", 1)],
            [("created_at", -1)],
        ]
