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

# Global cache: repo_id -> (updated_at_timestamp, BM25Okapi, list of ChunkDocument)
_bm25_cache: Dict[str, tuple] = {}

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
            faiss_results = await _hydrate_from_metadata_store(
                repo_id=repo_id,
                faiss_index_path=repo.faiss_index_path,
                faiss_ids=faiss_ids,
                scores=raw_scores,
            )
        else:
            faiss_results = await _hydrate_from_mongodb(
                repo_id=repo_id,
                faiss_ids=faiss_ids,
                scores=raw_scores,
            )

        # -- Step 3.5: BM25 Retrieval --
        cached_val = _bm25_cache.get(repo_id)
        if cached_val and cached_val[0] == repo.updated_at:
            bm25, all_chunks = cached_val[1], cached_val[2]
        else:
            all_chunks = await ChunkDocument.find(ChunkDocument.repo_id == repo_id).to_list()
            tokenized_corpus = [c.content.lower().split() for c in all_chunks]
            if tokenized_corpus:
                from rank_bm25 import BM25Okapi
                bm25 = BM25Okapi(tokenized_corpus)
                _bm25_cache[repo_id] = (repo.updated_at, bm25, all_chunks)
            else:
                bm25 = None

        tokenized_query = query.lower().split()
        bm25_results = []
        if bm25 and tokenized_query:
            bm25_scores = bm25.get_scores(tokenized_query)
            
            for chunk_idx, score in enumerate(bm25_scores):
                if score > 0:
                    chunk = all_chunks[chunk_idx]
                    bm25_results.append({
                        "chunk_id": str(chunk.id),
                        "faiss_id": chunk.faiss_id,
                        "file_path": chunk.file_path,
                        "language": chunk.language,
                        "start_line": chunk.start_line,
                        "end_line": chunk.end_line,
                        "content": chunk.content,
                        "chunk_type": chunk.chunk_type,
                        "symbol_name": chunk.symbol_name,
                        "score": float(score),
                    })
            bm25_results.sort(key=lambda x: x["score"], reverse=True)
            bm25_results = bm25_results[:fetch_k]

        # -- Step 4: Reciprocal Rank Fusion (RRF) & Candidate Merge --
        faiss_ranks = {r.get("chunk_id") or str(r.get("faiss_id")): idx + 1 for idx, r in enumerate(faiss_results)}
        bm25_ranks = {r.get("chunk_id") or str(r.get("faiss_id")): idx + 1 for idx, r in enumerate(bm25_results)}

        merged_candidates = {}
        max_faiss_score = max([r["score"] for r in faiss_results]) if faiss_results else 1.0
        max_bm25_score = max([r["score"] for r in bm25_results]) if bm25_results else 1.0

        for r in faiss_results:
            cid = r.get("chunk_id") or str(r.get("faiss_id"))
            normalized_semantic = r["score"] / (max_faiss_score or 1.0)
            merged_candidates[cid] = {
                **r,
                "lexical_score": 0.0,
                "semantic_score": float(r["score"]),
                "normalized_semantic": normalized_semantic,
                "normalized_lexical": 0.0,
            }

        for r in bm25_results:
            cid = r.get("chunk_id") or str(r.get("faiss_id"))
            normalized_lexical = r["score"] / (max_bm25_score or 1.0)
            if cid in merged_candidates:
                merged_candidates[cid]["lexical_score"] = float(r["score"])
                merged_candidates[cid]["normalized_lexical"] = normalized_lexical
            else:
                merged_candidates[cid] = {
                    **r,
                    "lexical_score": float(r["score"]),
                    "semantic_score": 0.0,
                    "normalized_semantic": 0.0,
                    "normalized_lexical": normalized_lexical,
                }

        # Calculate RRF Score
        rrf_k = 60
        for cid, c in merged_candidates.items():
            rank_semantic = faiss_ranks.get(cid)
            rank_lexical = bm25_ranks.get(cid)
            rrf_score = 0.0
            if rank_semantic is not None:
                rrf_score += 1.0 / (rrf_k + rank_semantic)
            if rank_lexical is not None:
                rrf_score += 1.0 / (rrf_k + rank_lexical)
            c["rrf_score"] = rrf_score

        # Sort by RRF score to select top candidates for cross-encoder re-ranking
        unique_candidates = list(merged_candidates.values())
        unique_candidates.sort(key=lambda x: x.get("rrf_score", 0.0), reverse=True)

        settings = get_settings()
        enable_reranking = getattr(settings, "ENABLE_RERANKING", True)

        if enable_reranking and unique_candidates:
            try:
                from sentence_transformers import CrossEncoder
                import math
                global _cross_encoder
                if "_cross_encoder" not in globals() or _cross_encoder is None:
                    # Upgrade from ms-marco-MiniLM-L-6-v2 to BAAI/bge-reranker-base
                    _cross_encoder = CrossEncoder("BAAI/bge-reranker-base")
                
                # Re-rank only the top candidates to optimize performance
                rerank_candidates = unique_candidates[:top_k * 3]
                pairs = [(query, c["content"]) for c in rerank_candidates]
                rerank_scores = _cross_encoder.predict(pairs)
                
                for idx, score in enumerate(rerank_scores):
                    # Sigmoid function to normalize the score to [0, 1] range
                    sig_score = 1.0 / (1.0 + math.exp(-float(score)))
                    c = rerank_candidates[idx]
                    c["rerank_score"] = float(score)
                    c["final_score"] = sig_score
                    c["score"] = sig_score
                    c["ranking_explanation"] = (
                        f"RRF score: {c.get('rrf_score', 0.0):.4f}. "
                        f"Re-ranked using BAAI/bge-reranker-base."
                    )
                    c["source_citation"] = f"File: {c['file_path']}, lines {c['start_line']}–{c['end_line']}"
                
                # Sort by new rerank scores
                rerank_candidates.sort(key=lambda x: x.get("score", 0.0), reverse=True)
                # Keep re-ranked candidates plus rest of unique candidates
                unique_candidates = rerank_candidates + unique_candidates[top_k * 3:]
            except Exception as e:
                logger.error(f"Re-ranking failed: {e}. Falling back to combined scores.")
                for c in unique_candidates:
                    c["rerank_score"] = 0.0
                    c["final_score"] = c["rrf_score"]
                    c["score"] = c["final_score"]
                    c["ranking_explanation"] = f"Fallback RRF score (RRF score: {c.get('rrf_score', 0.0):.4f})."
                    c["source_citation"] = f"File: {c['file_path']}, lines {c['start_line']}–{c['end_line']}"
        else:
            for c in unique_candidates:
                c["rerank_score"] = 0.0
                c["final_score"] = c["rrf_score"]
                c["score"] = c["final_score"]
                c["ranking_explanation"] = f"Reciprocal Rank Fusion score (RRF score: {c.get('rrf_score', 0.0):.4f})."
                c["source_citation"] = f"File: {c['file_path']}, lines {c['start_line']}–{c['end_line']}"

        results = unique_candidates

        # -- Step 4.5: Post-filters --
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
        
    store = FAISSStore(repo_id=repo_id, index_path=repo.faiss_index_path)
    if not store.exists():
        repo.status = RepoStatus.DEGRADED
        repo.error_message = "FAISS index missing. Data may have been lost during server restart."
        await repo.save()
        logger.error("[{id}] Marked repo DEGRADED. FAISS index missing at {p}", id=repo_id, p=repo.faiss_index_path)
        raise SearchError(
            f"Repository '{repo_id}' data was lost during server restart. "
            "Please re-ingest the repository."
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
