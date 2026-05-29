# backend/app/services/search_service.py
"""
CodeSense — Semantic Search Service (v2)

Thin orchestration layer that:
  1. Delegates retrieval to RetrievalService
  2. Writes a SearchLogDocument (fire-and-forget audit trail)
  3. Returns a response dict matching the SearchResponse schema

Keeping this separate from RetrievalService allows search-specific
concerns (logging, rate-limiting, response shaping) to stay clean.
"""

from __future__ import annotations

import asyncio
import time
from typing import Optional

from app_logger import logger

from app.services.retrieval_service import RetrievalService
from app.models.search_log import QueryType, SearchLogDocument


class SearchService:

    def __init__(self) -> None:
        self._retrieval = RetrievalService()

    async def search(
        self,
        repo_id: str,
        query: str,
        top_k: int = 5,
        language_filter: Optional[str] = None,
        chunk_type_filter: Optional[str] = None,
        min_score: float = 0.0,
    ) -> dict:
        """
        Execute semantic search and return a response dict.
        Audit log is written asynchronously (does not block the response).
        """
        result = await self._retrieval.retrieve(
            repo_id=repo_id,
            query=query,
            top_k=top_k,
            language_filter=language_filter,
            chunk_type_filter=chunk_type_filter,
            min_score=min_score,
        )

        # Fire-and-forget audit log
        asyncio.create_task(
            self._write_audit_log(
                repo_id=repo_id,
                query=query,
                top_k=top_k,
                result=result,
            )
        )

        return result

    @staticmethod
    async def _write_audit_log(
        repo_id: str,
        query: str,
        top_k: int,
        result: dict,
    ) -> None:
        try:
            await SearchLogDocument(
                repo_id=repo_id,
                query_type=QueryType.SEMANTIC_SEARCH,
                query=query,
                top_k=top_k,
                result_count=len(result.get("results", [])),
                result_file_paths=[
                    r["file_path"] for r in result.get("results", [])
                ],
                latency_ms=result.get("latency_ms", 0.0),
            ).insert()
        except Exception as exc:
            logger.warning("Audit log write failed: {err}", err=exc)
