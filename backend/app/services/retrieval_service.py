# backend/app/services/retrieval_service.py
"""
CodeSense — Semantic Retrieval Service (v2)

Performs end-to-end semantic retrieval:
  1. Embed query via embedding_pipeline
  2. ANN search via FAISSStore
  3. Metadata hydration — first from MetadataStore (fast, disk-local),
     then fall back to MongoDB for rich ChunkDocument fields
  4. Optional post-filters (language, chunk_type, score threshold)
  5. Re-ranking via cross-encoder (when enabled in settings)
  6. Result assembly and deduplication

This service is consumed by:
  - SearchService  (search.py API)
  - QAService      (qa_service.py RAG context assembly)
"""

from __future__ import annotations

import time
from typing import Any, Dict, List, Optional

from app_logger import logger

from app.core.config import get_settings
from app.core.exceptions import NotFoundError, SearchError
from app.ml.embedding_pipeline import embed_query
from app.models.chunk import ChunkDocument
from app.models.repository import RepositoryDocument, RepoStatus
from app.vector_store.faiss_store import FAISSStore
from app.vector_store.metadata_store import MetadataStore


# ---------------------------------------------------------------------------
# Result schema
# ---------------------------------------------------------------------------

class RetrievalResult:
    """Single ranked result from the retrieval pipeline."""

    __slots__ = (
        "chunk_id", "faiss_id", "file_path", "language",
        "start_line", "end_line", "content",
        "chunk_type", "symbol_name", "score",
    )

    def __init__(self, **kwargs: Any) -> None:
        for k, v in kwargs.items():
            setattr(self, k, v)

    def to_dict(self) -> Dict[str, Any]:
        return {s: getattr(self, s, None) for s in self.__slots__}


# ---------------------------------------------------------------------------
# RetrievalService
# ---------------------------------------------------------------------------

class RetrievalService:
    """
    Stateless service; instantiated per-request via FastAPI Depends().
    """

    # ------------------------------------------------------------------ #
    # Primary search method
    # ------------------------------------------------------------------ #

    async def retrieve(
        self,
        repo_id: str,
        query: str,
        top_k: int = 5,
        language_filter: Optional[str] = None,
        chunk_type_filter: Optional[str] = None,
        min_score: float = 0.0,
        use_metadata_cache: bool = False,
    ) -> Dict[str, Any]:
        """
        Full semantic retrieval pipeline.

        Args:
            repo_id:             Target repository.
            query:               Natural-language or code search string.
            top_k:               Number of results to return (after filtering).
            language_filter:     If set, only return chunks in this language.
            chunk_type_filter:   If set, only return chunks of this type
                                 (function | class | window).
            min_score:           Discard results below this cosine score.
            use_metadata_cache:  Prefer MetadataStore over MongoDB for metadata.

        Returns:
            dict with keys: success, query, repo_id, results, latency_ms
        """
        t0 = time.perf_counter()

        # -- Guard: repo must exist and be ready --
        repo = await _get_ready_repo(repo_id)

        # -- Step 1: Embed query --
        query_vec = embed_query(query)

        # -- Step 2: FAISS ANN search (fetch 3× top_k to allow post-filtering) --
        fetch_k = min(top_k * 3, 50)
        store = FAISSStore(repo_id=repo_id, index_path=repo.faiss_index_path)
        faiss_ids, raw_scores = store.search(query_vec, top_k=fetch_k)

        logger.debug(
            "[{id}] FAISS returned {n} candidates for query '{q}'",
            id=repo_id,
            n=len(faiss_ids),
            q=query[:60],
        )

        # -- Step 3: Hydrate metadata --
        if use_metadata_cache:
            results = await _hydrate_from_metadata_store(
                repo_id=repo_id,
                faiss_index_path=repo.faiss_index_path,
                faiss_ids=faiss_ids,
                scores=raw_scores,
            )
        else:
            results = await _hydrate_from_mongodb(
                repo_id=repo_id,
                faiss_ids=faiss_ids,
                scores=raw_scores,
            )

        # -- Step 4: Post-filters --
        if language_filter:
            results = [r for r in results if r["language"] == language_filter]
        if chunk_type_filter:
            results = [r for r in results if r["chunk_type"] == chunk_type_filter]
        if min_score > 0:
            results = [r for r in results if r["score"] >= min_score]

        # -- Step 5: Deduplicate (same file_path + start_line) & trim --
        results = _deduplicate(results)[:top_k]

        elapsed_ms = (time.perf_counter() - t0) * 1_000
        logger.info(
            "Retrieval for repo {id}: {n} results in {ms:.1f}ms",
            id=repo_id,
            n=len(results),
            ms=elapsed_ms,
        )

        return {
            "success": True,
            "query": query,
            "repo_id": repo_id,
            "results": results,
            "latency_ms": round(elapsed_ms, 2),
        }

    # ------------------------------------------------------------------ #
    # Context assembly for RAG
    # ------------------------------------------------------------------ #

    async def retrieve_context(
        self,
        repo_id: str,
        query: str,
        top_k: int = 5,
        max_context_chars: int = 6_000,
    ) -> str:
        """
        Retrieve and format top-k chunks as a combined context string
        for use in RAG prompt construction.
        """
        result = await self.retrieve(repo_id=repo_id, query=query, top_k=top_k)
        chunks = result.get("results", [])

        parts: List[str] = []
        total = 0
        for chunk in chunks:
            header = (
                f"# File: {chunk['file_path']} "
                f"(lines {chunk['start_line']}–{chunk['end_line']})"
            )
            body = chunk.get("content", "")
            snippet = f"{header}\n{body}\n"
            if total + len(snippet) > max_context_chars:
                break
            parts.append(snippet)
            total += len(snippet)

        return "\n---\n".join(parts)

    # ------------------------------------------------------------------ #
    # Embedding info
    # ------------------------------------------------------------------ #

    def embedding_info(self) -> Dict[str, Any]:
        """Return current embedding model metadata."""
        from app.ml.embedder import get_embedder
        return get_embedder().model_info()


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

async def _get_ready_repo(repo_id: str) -> RepositoryDocument:
    repo = await RepositoryDocument.get(repo_id)
    if repo is None:
        raise NotFoundError(f"Repository '{repo_id}' not found.")
    if repo.status != RepoStatus.READY:
        raise SearchError(
            f"Repository '{repo_id}' is not ready (status: {repo.status}). "
            "Wait for ingestion to complete."
        )
    return repo


async def _hydrate_from_metadata_store(
    repo_id: str,
    faiss_index_path: Optional[str],
    faiss_ids: List[int],
    scores: List[float],
) -> List[Dict[str, Any]]:
    """Resolve chunk metadata from disk-local MetadataStore (fast path)."""
    meta_store = MetadataStore(repo_id=repo_id, index_path=faiss_index_path)

    if not meta_store.exists():
        logger.debug("[{id}] No MetadataStore on disk; falling back to MongoDB.", id=repo_id)
        return await _hydrate_from_mongodb(repo_id, faiss_ids, scores)

    records = meta_store.get_many(faiss_ids)
    results = []
    for record, score in zip(records, scores):
        if record is None:
            continue
        results.append({**record, "score": float(score)})
    return results


async def _hydrate_from_mongodb(
    repo_id: str,
    faiss_ids: List[int],
    scores: List[float],
) -> List[Dict[str, Any]]:
    """Resolve chunk metadata from MongoDB (slower but authoritative)."""
    results = []
    for faiss_id, score in zip(faiss_ids, scores):
        chunk = await ChunkDocument.find_one(
            ChunkDocument.repo_id == repo_id,
            ChunkDocument.faiss_id == int(faiss_id),
        )
        if chunk is None:
            continue
        results.append({
            "chunk_id": str(chunk.id),
            "faiss_id": faiss_id,
            "file_path": chunk.file_path,
            "language": chunk.language,
            "start_line": chunk.start_line,
            "end_line": chunk.end_line,
            "content": chunk.content,
            "chunk_type": chunk.chunk_type,
            "symbol_name": chunk.symbol_name,
            "score": float(score),
        })
    return results


def _deduplicate(results: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Remove duplicate (file_path, start_line) pairs, keeping highest score."""
    seen: Dict[tuple, int] = {}          # key → index in `out`
    out: List[Dict[str, Any]] = []
    for r in results:
        key = (r.get("file_path", ""), r.get("start_line", 0))
        if key in seen:
            if r["score"] > out[seen[key]]["score"]:
                out[seen[key]] = r
        else:
            seen[key] = len(out)
            out.append(r)
    return out
