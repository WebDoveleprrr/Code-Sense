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
from app.db.ml.context_ranker import apply_ranking
from app.db.ml.rag import build_rag_context, generate_answer


# ---------------------------------------------------------------------------
# Config defaults
# ---------------------------------------------------------------------------

DEFAULT_TOP_K: int = 8
DEFAULT_MAX_CONTEXT_CHARS: int = 6_000
DEFAULT_MIN_SCORE: float = 0.10


async def expand_query(question: str, provider: Optional[str] = None) -> str:
    """Expand the user query using LLM for better retrieval recall."""
    from app.db.ml.llm_client import complete
    system_prompt = (
        "You are a search query expansion assistant for codebase search. "
        "Generate 3-4 alternative search terms, synonyms, functions, or concepts "
        "related to the query. Keep it extremely brief and output only the expanded terms space-separated."
    )
    try:
        expansion = await complete(
            system_prompt=system_prompt,
            user_prompt=f"Expand this codebase search query: {question}",
            provider=provider
        )
        expanded = f"{question} {expansion.strip()}"
        return expanded
    except Exception as e:
        logger.warning("Query expansion failed: {err}", err=str(e))
        return question


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
        strict_mode: bool = False,
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
            strict_mode:       If True, prevent LLM hallucination when context is missing.

        Returns:
            dict matching the QAResponse schema.
        """
        t0 = time.perf_counter()
        logger.info("[QA] Request received for repo {id} - query: '{q}'", id=repo_id, q=question)

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
        # Step 0: Query expansion
        # ---------------------------------------------------------------- #
        expanded_query = await expand_query(question, provider=provider)
        t_expansion = time.perf_counter()
        logger.info("[QA] Query expansion time: {ms:.1f}ms (Expanded: '{eq}')", ms=(t_expansion - t0) * 1000, eq=expanded_query)

        # ---------------------------------------------------------------- #
        # Step 1: Semantic retrieval
        # (retrieval_service handles internal over-fetching and cross-encoder re-ranking)
        # ---------------------------------------------------------------- #
        retrieval_svc = RetrievalService()
        retrieval_result = await retrieval_svc.retrieve(
            repo_id=repo_id,
            query=expanded_query,
            top_k=top_k,
            language_filter=language_filter,
            min_score=min_score,
        )

        candidates = retrieval_result.get("results", [])
        
        t_retrieval = time.perf_counter()
        logger.info(
            "[QA] {n} ranked candidates retrieved for repo {id} in {ms:.1f}ms",
            n=len(candidates),
            id=repo_id,
            ms=(t_retrieval - t_expansion) * 1000,
        )

        ranked_chunks = candidates

        # ---------------------------------------------------------------- #
        # Step 3: Context assembly
        # ---------------------------------------------------------------- #
        context = build_rag_context(ranked_chunks, max_chars=max_context_chars)

        if not ranked_chunks or not context.strip():
            logger.warning("[QA] Empty context for repo {id} — question: {q}", id=repo_id, q=question)
            answer_text = "I couldn't find evidence in the indexed repository."
            return {
                "success": True,
                "question": question,
                "answer": answer_text,
                "sources": [],
                "confidence": 0,
                "latency_ms": round((time.perf_counter() - t0) * 1000, 2),
                "is_fallback": False,
            }

        t_assembly = time.perf_counter()

        # Calculate overall QA confidence from max chunk confidence
        overall_confidence = max([c.get("confidence", 0) for c in ranked_chunks]) if ranked_chunks else 0

        # ---------------------------------------------------------------- #
        # Step 4: LLM answer generation
        # ---------------------------------------------------------------- #
        is_fallback = False
        try:
            answer_text = await generate_answer(
                question=question,
                context=context,
                provider=provider,
                strict_mode=strict_mode,
            )
            t_llm = time.perf_counter()
            logger.info("[QA] LLM generation time: {ms:.1f}ms", ms=(t_llm - t_assembly) * 1000)
        except Exception as exc:
            from app.db.ml.llm_client import LLMUnavailableError
            if isinstance(exc, LLMUnavailableError):
                logger.warning(f"[QA] LLM Provider Unavailable: {str(exc)}")
                answer_text = f"**Note: The LLM provider is currently unavailable ({str(exc)}).**\n\n" + _fallback_qa(question, ranked_chunks)
                is_fallback = True
            else:
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
            "({n} context chunks, {a} chars, confidence {c}%)",
            id=repo_id,
            ms=elapsed_ms,
            n=len(ranked_chunks),
            a=len(answer_text),
            c=overall_confidence,
        )

        return {
            "success": True,
            "question": question,
            "answer": answer_text,
            "sources": ranked_chunks,
            "confidence": overall_confidence,
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
