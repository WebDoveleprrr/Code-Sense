# backend/app/services/dependency_service.py
"""
CodeSense — Dependency Graph Service (v2)
Replaces stub in other_services.py — interface identical.
"""

from __future__ import annotations

import time
from typing import Optional

from app_logger import logger

from app.core.exceptions import NotFoundError
from app.models.repository import RepositoryDocument
from app.models.search_log import QueryType, SearchLogDocument


class DependencyService:
    """
    Builds a static dependency graph for a repository.
    Stateless — instantiated per request via FastAPI Depends().
    """

    async def build_graph(self, repo_id: str) -> dict:
        t0 = time.perf_counter()

        repo = await RepositoryDocument.get(repo_id)
        if repo is None:
            raise NotFoundError(f"Repository '{repo_id}' not found.")

        from app.ml.dependency_parser import parse_dependencies

        nodes, edges = await parse_dependencies(repo)
        elapsed_ms = (time.perf_counter() - t0) * 1_000

        logger.info(
            "Dependency graph built for repo {id}: {n} nodes, {e} edges ({ms:.1f}ms)",
            id=repo_id,
            n=len(nodes),
            e=len(edges),
            ms=elapsed_ms,
        )

        import asyncio
        asyncio.create_task(_write_dep_log(repo_id, elapsed_ms))

        return {
            "success": True,
            "repo_id": repo_id,
            "nodes": nodes,
            "edges": edges,
            "latency_ms": round(elapsed_ms, 2),
        }


async def _write_dep_log(repo_id: str, latency_ms: float) -> None:
    try:
        await SearchLogDocument(
            repo_id=repo_id,
            query_type=QueryType.DEPENDENCY,
            query="dependency_graph",
            top_k=0,
            result_count=0,
            result_file_paths=[],
            latency_ms=latency_ms,
        ).insert()
    except Exception as exc:
        logger.warning("Dependency audit log write failed: {err}", err=exc)
