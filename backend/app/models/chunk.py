# backend/app/models/chunk.py
"""
CodeSense — Code Chunk Beanie Document Model (v2)
Adds chunk_type, symbol_name, symbol_metadata for richer semantic search.
"""

from __future__ import annotations

from datetime import datetime
from typing import Any, Dict, List, Optional

from beanie import Document
from pydantic import Field


class ChunkDocument(Document):
    """
    A single semantic chunk extracted from a repository file.
    Each chunk is associated with exactly one repository and has
    a corresponding embedding stored in FAISS.
    """

    # Foreign key
    repo_id: str                        # str(RepositoryDocument.id)

    # Source location
    file_path: str                      # relative path inside repo
    language: Optional[str] = None      # python, javascript, typescript, cpp, …
    start_line: int = 0
    end_line: int = 0

    # Content
    content: str                        # raw source text of the chunk
    chunk_index: int = 0               # position within the file
    token_count: int = 0

    # v2 — Chunk classification
    chunk_type: str = "window"          # "function" | "class" | "window" | "symbol_header"
    symbol_name: Optional[str] = None   # populated for function/class chunks
    symbol_metadata: Dict[str, Any] = Field(default_factory=dict)
    # e.g. {"args": [...], "decorators": [...], "docstring": "...", "bases": [...]}

    # FAISS back-reference
    faiss_id: Optional[int] = None      # integer ID in the FAISS index

    # Timestamps
    created_at: datetime = Field(default_factory=datetime.utcnow)

    class Settings:
        name = "chunks"
        indexes = [
            [("repo_id", 1)],
            [("repo_id", 1), ("file_path", 1)],
            [("faiss_id", 1)],
            [("chunk_type", 1)],
            [("symbol_name", 1)],
        ]
