# backend/app/schemas/ingestion.py
"""
CodeSense — Ingestion & Parsing Pydantic Schemas
Request/response models for the repository ingestion API surface.
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field, HttpUrl


# ------------------------------------------------------------------ #
# Request schemas
# ------------------------------------------------------------------ #

class GitHubIngestRequest(BaseModel):
    """Payload for POST /repositories/github"""

    github_url: str = Field(..., examples=["https://github.com/owner/repo"])
    branch: str = Field(default="main", examples=["main", "master", "develop"])

    model_config = {"json_schema_extra": {"example": {"github_url": "https://github.com/owner/repo", "branch": "main"}}}


# ------------------------------------------------------------------ #
# Parse result schemas (nested, returned inside repo detail)
# ------------------------------------------------------------------ #

class FunctionSchema(BaseModel):
    name: str
    lineno: int
    end_lineno: Optional[int] = None
    is_async: bool = False
    args: List[Dict[str, Any]] = Field(default_factory=list)
    returns: Optional[str] = None
    decorators: List[str] = Field(default_factory=list)
    docstring: Optional[str] = None


class ClassSchema(BaseModel):
    name: str
    lineno: int
    end_lineno: Optional[int] = None
    bases: List[str] = Field(default_factory=list)
    decorators: List[str] = Field(default_factory=list)
    docstring: Optional[str] = None
    methods: List[FunctionSchema] = Field(default_factory=list)


class ImportSchema(BaseModel):
    type: str           # "import" | "from_import" | "es_import" | "require" | "include"
    module: str
    names: List[str] = Field(default_factory=list)
    lineno: int = 0


class CommentSchema(BaseModel):
    type: str = "inline"   # "inline" | "block" | "jsdoc"
    text: str
    lineno: int = 0


class ParsedFileSchema(BaseModel):
    file_path: str
    language: str
    line_count: int
    function_count: int
    class_count: int
    import_count: int
    comment_count: int
    functions: List[FunctionSchema] = Field(default_factory=list)
    classes: List[ClassSchema] = Field(default_factory=list)
    imports: List[ImportSchema] = Field(default_factory=list)
    docstring: Optional[str] = None


# ------------------------------------------------------------------ #
# Repository response schemas
# ------------------------------------------------------------------ #

class RepoMetadataSchema(BaseModel):
    """Aggregated code statistics stored in RepositoryDocument.repo_metadata"""

    total_lines: int = 0
    total_functions: int = 0
    total_classes: int = 0
    total_imports: int = 0
    files: List[Dict[str, Any]] = Field(default_factory=list)


class RepoSummaryResponse(BaseModel):
    id: str
    name: str
    owner: Optional[str] = None
    source: str
    status: str
    total_files: int
    indexed_files: int = 0
    skipped_files: int = 0
    indexing_mode: str = "standard"
    total_chunks: int
    created_at: str


class RepoDetailResponse(RepoSummaryResponse):
    language_breakdown: Dict[str, int]
    total_tokens: int
    faiss_index_path: Optional[str] = None
    github_url: Optional[str] = None
    zip_filename: Optional[str] = None
    error_message: Optional[str] = None
    indexed_at: Optional[str] = None
    repo_metadata: RepoMetadataSchema = Field(default_factory=RepoMetadataSchema)


# ------------------------------------------------------------------ #
# Chunk response schema
# ------------------------------------------------------------------ #

class ChunkResponse(BaseModel):
    """Returned by the chunk list / search result endpoints."""

    id: str
    repo_id: str
    file_path: str
    language: Optional[str] = None
    start_line: int
    end_line: int
    content: str
    chunk_index: int
    token_count: int
    chunk_type: str = "window"
    symbol_name: Optional[str] = None
    symbol_metadata: Dict[str, Any] = Field(default_factory=dict)
    faiss_id: Optional[int] = None


# ------------------------------------------------------------------ #
# Ingestion status response
# ------------------------------------------------------------------ #

class IngestStartedResponse(BaseModel):
    success: bool = True
    message: str
    repo_id: str
