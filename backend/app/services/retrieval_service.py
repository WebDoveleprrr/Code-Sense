# backend/app/services/retrieval_service.py --- How do we search an indexed repository --- used by search.py and qa_service.py
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

import time #Measure retrieval time
from typing import Any, Dict, List, Optional #better readability

from app_logger import logger

from app.core.config import get_settings
from app.core.exceptions import NotFoundError, SearchError #Return meaningful API errors
from app.db.ml.embedding_pipeline import embed_query #Query->Embedding
from app.models.chunk import ChunkDocument #MongoDB document --- Used to retrieve: Actual Chunk after FAISS search
from app.models.repository import RepositoryDocument, RepoStatus
from app.vector_store.faiss_store import FAISSStore #semnatic search
from app.vector_store.metadata_store import MetadataStore

from collections import OrderedDict #Used for: BM25 Cache
# Global cache: repo_id -> (updated_at_timestamp, BM25Okapi, list of ChunkDocument)
_bm25_cache: OrderedDict[str, tuple] = OrderedDict()
MAX_CACHE_SIZE = 3


class RetrievalResult: #Represents one search result
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


#Perform complete semantic retrieval
class RetrievalService:
    
    async def retrieve(
        self,
        repo_id: str, #Which repository
        query: str, #User question
        top_k: int = 5, #How many results
        language_filter: Optional[str] = None, #programmong language
        chunk_type_filter: Optional[str] = None, #Only: Functions,Classes,Windows
        min_score: float = 0.0, #Discard weak matches
        use_metadata_cache: bool = False, #Use: MetadataStore instead of MongoDB --- Faster.
    ) -> Dict[str, Any]:
        t0 = time.perf_counter()

        #Guard: repo must exist and be ready
        repo = await _get_ready_repo(repo_id)

        #Embed query
        query_vec = embed_query(query)

        #FAISS ANN search (fetch 3× top_k to allow post-filtering)
        fetch_k = min(top_k * 3, 50)
        store = FAISSStore(repo_id=repo_id, index_path=repo.faiss_index_path)
        faiss_ids, raw_scores = store.search(query_vec, top_k=fetch_k) #Input: Query Vector --- Output: FAISS IDs + Similarity Scores

        t_faiss = time.perf_counter()
        logger.info(
            "[{id}] FAISS returned {n} candidates for query '{q}' in {ms:.1f}ms",
            id=repo_id,
            n=len(faiss_ids),
            q=query[:60],
            ms=(t_faiss - t0) * 1000,
        )

        #Hydrate metadata --- vector converting to code
        if use_metadata_cache: #MetadataStore --- Fast,Disk Local
            faiss_results = await _hydrate_from_metadata_store(
                repo_id=repo_id,
                faiss_index_path=repo.faiss_index_path,
                faiss_ids=faiss_ids,
                scores=raw_scores,
            )
        else: #MongoDB --- Rich Documents,Always Complete
            faiss_results = await _hydrate_from_mongodb(
                repo_id=repo_id,
                faiss_ids=faiss_ids,
                scores=raw_scores,
            )
            
        t_hydrate = time.perf_counter()
        logger.info("[{id}] Metadata hydration time: {ms:.1f}ms", id=repo_id, ms=(t_hydrate - t_faiss) * 1000)

        #BM25 Retrieval(keyword retrieval)
        cached_val = _bm25_cache.get(repo_id)
        if cached_val and str(cached_val[0]) == str(repo.updated_at): #If BM25 already exists: Reuse it
            bm25, all_chunks = cached_val[1], cached_val[2]
            _bm25_cache.move_to_end(repo_id)
        else: #Read Every Chunk -> Tokenize -> Build BM25
            all_chunks = await ChunkDocument.find(ChunkDocument.repo_id == repo_id).to_list()
            tokenized_corpus = [c.content.lower().split() for c in all_chunks] #tokenise
            if tokenized_corpus:
                from rank_bm25 import BM25Okapi
                bm25 = BM25Okapi(tokenized_corpus)
                _bm25_cache[repo_id] = (repo.updated_at, bm25, all_chunks)
                _bm25_cache.move_to_end(repo_id)
                if len(_bm25_cache) > MAX_CACHE_SIZE:
                    evicted_id, _ = _bm25_cache.popitem(last=False)
                    logger.info(f"BM25 cache full (>{MAX_CACHE_SIZE}). Evicted cache for repo: {evicted_id}")
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

        t_bm25 = time.perf_counter()
        logger.info("[{id}] BM25 retrieval time: {ms:.1f}ms", id=repo_id, ms=(t_bm25 - t_hydrate) * 1000)

        #Reciprocal Rank Fusion (RRF) & Candidate Merge
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

        from app.db.ml.context_ranker import apply_ranking

        import re
        
        def extract_highlights(query: str, content: str) -> List[str]:
            words = [w for w in query.lower().split() if len(w) > 2]
            if not words:
                return []
            lines = content.split('\n')
            highlights = []
            for line in lines:
                if any(w in line.lower() for w in words):
                    highlights.append(line.strip())
                    if len(highlights) >= 3:
                        break
            return highlights

        if enable_reranking and unique_candidates:
            # We want context ranker to use the base RRF score
            for c in unique_candidates:
                c["score"] = c.get("rrf_score", 0.0)

            t_before_ce = time.perf_counter()
            ranked_dict = apply_ranking(
                query=query,
                retrieval_result={"results": unique_candidates[:top_k * 3]},
                use_cross_encoder=True
            )
            # Recombine ranked top chunks with the rest
            unique_candidates = ranked_dict["results"] + unique_candidates[top_k * 3:]
            
            # Map composite_score back to score for consistency
            for c in unique_candidates:
                c["score"] = c.get("composite_score", c.get("score", 0.0))
                c["confidence"] = min(100, max(0, int(c["score"] * 100)))
                c["ranking_explanation"] = f"RRF + Cross-encoder score: {c['score']:.4f}"
                c["source_citation"] = f"File: {c['file_path']}, lines {c['start_line']}–{c['end_line']}"
                c["highlights"] = extract_highlights(query, c.get("content", ""))
                
            t_ce = time.perf_counter()
            logger.info("[{id}] Cross encoder time: {ms:.1f}ms", id=repo_id, ms=(t_ce - t_before_ce) * 1000)
        else:
            for c in unique_candidates:
                c["score"] = c.get("rrf_score", 0.0)
                # Map RRF score (which typically ranges 0-0.033 based on k=60) to 0-100
                c["confidence"] = min(100, max(0, int((c["score"] / 0.033) * 100)))
                c["ranking_explanation"] = f"Reciprocal Rank Fusion score (RRF score: {c.get('rrf_score', 0.0):.4f})."
                c["source_citation"] = f"File: {c['file_path']}, lines {c['start_line']}–{c['end_line']}"
                c["highlights"] = extract_highlights(query, c.get("content", ""))

        results = unique_candidates

        #Post-filters 
        if language_filter:
            results = [r for r in results if r["language"] == language_filter]
        if chunk_type_filter:
            results = [r for r in results if r["chunk_type"] == chunk_type_filter]
            
        # Adaptive Thresholding: Drop results significantly worse than the best match
        if results:
            top_score = results[0]["score"]
            
            filtered_results = []
            for r in results:
                raw_semantic = r.get("semantic_score", 0.0)
                # Reject if the cosine similarity is below noise floor (e.g., < 0.25)
                # Meaningless queries usually return < 0.2
                if raw_semantic > 0 and raw_semantic < 0.25:
                    continue
                    
                # RRF score threshold: must be at least 40% of the top score,
                # and at least a base minimum (0.01 ensures it's in the top ranks).
                if r["score"] < max(0.01, top_score * 0.4):
                    continue
                    
                filtered_results.append(r)
                
            results = filtered_results

        #Deduplicate --- remove duplicate
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

    #Retrieve and format top-k chunks as a combined context string for use in RAG prompt construction
    async def retrieve_context(
        self,
        repo_id: str,
        query: str,
        top_k: int = 5,
        max_context_chars: int = 6_000,
    ) -> str:
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

   
    def embedding_info(self) -> Dict[str, Any]:
        """Return current embedding model metadata."""
        from app.db.ml.embedder import get_embedder
        return get_embedder().model_info()



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
    """Resolve chunk metadata from MongoDB using bulk $in query."""
    int_faiss_ids = [int(fid) for fid in faiss_ids]
    chunks = await ChunkDocument.find(
        {"repo_id": repo_id, "faiss_id": {"$in": int_faiss_ids}}
    ).to_list()
    
    chunk_map = {c.faiss_id: c for c in chunks}
    
    results = []
    for faiss_id, score in zip(faiss_ids, scores):
        chunk = chunk_map.get(int(faiss_id))
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
