# backend/app/api/v1/search.py
"""
CodeSense — Semantic Code Search API (v2)

Endpoints:
  POST /api/v1/search          — semantic similarity search
  POST /api/v1/search/batch    — multi-query batch search
  GET  /api/v1/search/info     — embedding model info
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel, Field

from app.services.search_service import SearchService
from app.services.retrieval_service import RetrievalService

router = APIRouter()


# ---------------------------------------------------------------------------
# Request / Response schemas
# ---------------------------------------------------------------------------

class SearchRequest(BaseModel):
    repo_id: str = Field(..., description="Repository ID to search within.")
    query: str = Field(..., min_length=1, description="Natural language or code query.")
    top_k: int = Field(default=5, ge=1, le=20, description="Max results to return.")
    language_filter: Optional[str] = Field(
        default=None, description="Filter by language (python, javascript, …)."
    )
    chunk_type_filter: Optional[str] = Field(
        default=None, description="Filter by chunk type: function | class | window."
    )
    min_score: float = Field(
        default=0.0, ge=0.0, le=1.0, description="Minimum cosine similarity score."
    )

    model_config = {
        "json_schema_extra": {
            "example": {
                "repo_id": "664f1a2b3c4d5e6f7a8b9c0d",
                "query": "how are embeddings generated",
                "top_k": 5,
                "language_filter": "python",
            }
        }
    }


class SearchResultItem(BaseModel):
    chunk_id: Optional[str] = None
    faiss_id: Optional[int] = None
    file_path: str
    language: Optional[str] = None
    start_line: int
    end_line: int
    content: str
    chunk_type: str = "window"
    symbol_name: Optional[str] = None
    score: float


class SearchResponse(BaseModel):
    success: bool
    query: str
    repo_id: str
    results: List[SearchResultItem]
    latency_ms: float


class BatchSearchRequest(BaseModel):
    repo_id: str
    queries: List[str] = Field(..., min_length=1, max_length=10)
    top_k: int = Field(default=5, ge=1, le=20)
    language_filter: Optional[str] = None


class BatchSearchResponse(BaseModel):
    success: bool
    repo_id: str
    results_per_query: List[SearchResponse]
    total_latency_ms: float


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------

@router.post(
    "",
    response_model=SearchResponse,
    summary="Semantic code search",
    description=(
        "Embed the query and perform ANN similarity search over the repository's "
        "FAISS index. Returns ranked code chunks with file locations and scores."
    ),
)
async def semantic_search(
    payload: SearchRequest,
    service: SearchService = Depends(SearchService),
) -> SearchResponse:
    result = await service.search(
        repo_id=payload.repo_id,
        query=payload.query,
        top_k=payload.top_k,
        language_filter=payload.language_filter,
        chunk_type_filter=payload.chunk_type_filter,
        min_score=payload.min_score,
    )
    return SearchResponse(**result)


@router.post(
    "/batch",
    response_model=BatchSearchResponse,
    summary="Batch semantic search (multiple queries)",
    description=(
        "Run multiple queries against the same repository in one API call. "
        "Each query is embedded and searched independently."
    ),
)
async def batch_semantic_search(
    payload: BatchSearchRequest,
    service: SearchService = Depends(SearchService),
) -> BatchSearchResponse:
    import asyncio, time

    t0 = time.perf_counter()

    tasks = [
        service.search(
            repo_id=payload.repo_id,
            query=q,
            top_k=payload.top_k,
            language_filter=payload.language_filter,
        )
        for q in payload.queries
    ]
    results = await asyncio.gather(*tasks)

    total_ms = (time.perf_counter() - t0) * 1_000

    return BatchSearchResponse(
        success=True,
        repo_id=payload.repo_id,
        results_per_query=[SearchResponse(**r) for r in results],
        total_latency_ms=round(total_ms, 2),
    )


@router.get(
    "/info",
    summary="Embedding model information",
    description="Returns metadata about the currently loaded embedding model.",
)
async def embedding_info() -> Dict[str, Any]:
    svc = RetrievalService()
    return {"success": True, "embedding_model": svc.embedding_info()}
