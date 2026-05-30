# backend/app/services/qa_service.py
"""
CodeSense — Retrieval-Augmented Q&A Service (v2)

Replaces the stub qa_service.py with a full RAG pipeline:
  1. Semantic retrieval via RetrievalService
  2. Cross-encoder re-ranking via context_ranker
  3. Context window assembly with budget management
  4. Answer generation via rag.generate_answer (LLM-backed)
  5. Response formatting + audit logging

Drop-in replacement — interface is identical to v1.
"""

from __future__ import annotations

import time
from typing import Any, Dict, List, Optional

from app_logger import logger

from app.core.exceptions import NotFoundError, RAGError
from app.models.repository import RepositoryDocument, RepoStatus
from app.models.search_log import QueryType, SearchLogDocument
from app.services.retrieval_service import RetrievalService
from app.ml.context_ranker import apply_ranking
from app.ml.rag import build_rag_context, generate_answer


# ---------------------------------------------------------------------------
# Config defaults
# ---------------------------------------------------------------------------

DEFAULT_TOP_K: int = 8
DEFAULT_MAX_CONTEXT_CHARS: int = 6_000
DEFAULT_MIN_SCORE: float = 0.10


class QAService:
    """
    Orchestrates the full RAG pipeline for repository Q&A.
    Stateless — instantiated per request via FastAPI Depends().
    """

    async def answer(
        self,
        repo_id: str,
        question: str,
        top_k: int = DEFAULT_TOP_K,
        min_score: float = DEFAULT_MIN_SCORE,
        max_context_chars: int = DEFAULT_MAX_CONTEXT_CHARS,
        use_cross_encoder: bool = True,
        language_filter: Optional[str] = None,
        provider: Optional[str] = None,
    ) -> dict:
        """
        Execute the full RAG pipeline and return a response dict.

        Args:
            repo_id:           Target repository.
            question:          Developer's natural-language question.
            top_k:             Number of context chunks to retrieve.
            min_score:         Drop chunks below this cosine similarity.
            max_context_chars: Hard cap on context size sent to the LLM.
            use_cross_encoder: Whether to apply cross-encoder re-ranking.
            language_filter:   Optionally restrict context to one language.
            provider:          LLM provider override ("openai" | "anthropic").

        Returns:
            dict matching the QAResponse schema.
        """
        t0 = time.perf_counter()

        # ---------------------------------------------------------------- #
        # Guard: repo must exist and be READY
        # ---------------------------------------------------------------- #
        repo = await RepositoryDocument.get(repo_id)
        if repo is None:
            raise NotFoundError(f"Repository '{repo_id}' not found.")
        if repo.status != RepoStatus.READY:
            raise RAGError(
                f"Repository '{repo_id}' is not ready (status: {repo.status}). "
                "Wait for ingestion to complete."
            )

        # ---------------------------------------------------------------- #
        # Step 1: Semantic retrieval (fetch extra candidates for re-ranking)
        # ---------------------------------------------------------------- #
        retrieval_k = min(top_k * 3, 30)  # fetch 3× for re-ranker
        retrieval_svc = RetrievalService()
        retrieval_result = await retrieval_svc.retrieve(
            repo_id=repo_id,
            query=question,
            top_k=retrieval_k,
            language_filter=language_filter,
            min_score=min_score,
        )

        candidates = retrieval_result.get("results", [])
        logger.info(
            "[QA] {n} candidates retrieved for repo {id}",
            n=len(candidates),
            id=repo_id,
        )

        # ---------------------------------------------------------------- #
        # Step 2: Cross-encoder re-ranking
        # ---------------------------------------------------------------- #
        if candidates and use_cross_encoder:
            ranked_result = apply_ranking(
                query=question,
                retrieval_result=retrieval_result,
                use_cross_encoder=True,
            )
            ranked_chunks = ranked_result["results"][:top_k]
            # Use composite_score as the display score
            for c in ranked_chunks:
                c["score"] = c.get("composite_score", c.get("score", 0.0))
        else:
            ranked_chunks = candidates[:top_k]

        # ---------------------------------------------------------------- #
        # Step 3: Context assembly
        # ---------------------------------------------------------------- #
        context = build_rag_context(ranked_chunks, max_chars=max_context_chars)

        if not context.strip():
            logger.warning("[QA] Empty context for repo {id} — question: {q}", id=repo_id, q=question)

        # ---------------------------------------------------------------- #
        # Step 4: LLM answer generation
        # ---------------------------------------------------------------- #
        is_fallback = False
        try:
            answer_text = await generate_answer(
                question=question,
                context=context,
                provider=provider,
            )
        except Exception as exc:
            from app.ml.llm_client import LLMUnavailableError
            if isinstance(exc, LLMUnavailableError):
                raise
            logger.warning("[QA] LLM failure, falling back to extractive mode: {err}", err=str(exc))
            answer_text = _fallback_qa(question, ranked_chunks)
            is_fallback = True

        elapsed_ms = (time.perf_counter() - t0) * 1_000

        # ---------------------------------------------------------------- #
        # Step 5: Audit log (fire-and-forget)
        # ---------------------------------------------------------------- #
        import asyncio
        asyncio.create_task(
            _write_qa_log(
                repo_id=repo_id,
                question=question,
                top_k=top_k,
                chunks=ranked_chunks,
                answer=answer_text,
                latency_ms=elapsed_ms,
            )
        )

        logger.info(
            "[QA] Answer generated for repo {id} in {ms:.1f}ms "
            "({n} context chunks, {a} chars)",
            id=repo_id,
            ms=elapsed_ms,
            n=len(ranked_chunks),
            a=len(answer_text),
        )

        return {
            "success": True,
            "question": question,
            "answer": answer_text,
            "context_chunks": ranked_chunks,
            "latency_ms": round(elapsed_ms, 2),
            "is_fallback": is_fallback,
        }


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _fallback_qa(question: str, chunks: List[Dict[str, Any]]) -> str:
    """Generate a lightweight extractive fallback answer when the LLM is unavailable."""
    if not chunks:
        return "No relevant code context was found for this question."
    
    lines = [
        f"**Extracted {len(chunks)} relevant code chunk(s)** based on your query.",
        "",
        "Please review the sources below for details.",
        "",
        "### Top Matches:"
    ]
    for c in chunks[:3]:
        fp = c.get("file_path", "Unknown")
        sl = c.get("start_line", "")
        lines.append(f"- `{fp}` (Line {sl})")
        
    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Audit log helper
# ---------------------------------------------------------------------------

async def _write_qa_log(
    repo_id: str,
    question: str,
    top_k: int,
    chunks: List[Dict[str, Any]],
    answer: str,
    latency_ms: float,
) -> None:
    try:
        await SearchLogDocument(
            repo_id=repo_id,
            query_type=QueryType.QA,
            query=question,
            top_k=top_k,
            result_count=len(chunks),
            result_file_paths=[c["file_path"] for c in chunks],
            answer=answer,
            context_chunks_used=len(chunks),
            latency_ms=latency_ms,
        ).insert()
    except Exception as exc:
        logger.warning("QA audit log write failed: {err}", err=str(exc))
