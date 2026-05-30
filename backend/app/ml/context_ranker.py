# backend/app/ml/context_ranker.py
"""
CodeSense — Context Ranking Pipeline

Re-ranks FAISS ANN results using a combination of:
  1. Cross-encoder score (when cross-encoder model is available)
  2. Chunk-type boosting  (function/class > window)
  3. Symbol-name match   (keyword overlap between query & symbol name)
  4. Position penalty    (prefer earlier lines in a file as a tiebreaker)

The ranker is intentionally lightweight — it runs in-process on CPU
and adds < 50 ms for typical top-k = 15 candidate sets.
"""

from __future__ import annotations

import re
from typing import Any, Dict, List, Optional

from app_logger import logger


# ---------------------------------------------------------------------------
# Scoring weights (tunable via env / config in future iteration)
# ---------------------------------------------------------------------------

WEIGHT_FAISS_SCORE: float = 0.70       # base semantic similarity (cosine)
WEIGHT_CROSS_ENCODER: float = 0.20     # cross-encoder re-rank bonus
WEIGHT_SYMBOL_MATCH: float = 0.07      # symbol-name token overlap
WEIGHT_POSITION: float = 0.03          # file-position tiebreaker

# Chunk-type multipliers applied to the final composite score
CHUNK_TYPE_BOOST: Dict[str, float] = {
    "function": 1.05,
    "class": 1.03,
    "window": 1.00,
}


# ---------------------------------------------------------------------------
# Cross-encoder (optional, lazy-loaded)
# ---------------------------------------------------------------------------

_cross_encoder = None  # loaded once on first call


def _get_cross_encoder():
    """
    Lazy-load a cross-encoder for re-ranking.
    Falls back gracefully if sentence-transformers is not available or
    the model is not cached (CI / lightweight deploys).
    """
    global _cross_encoder
    if _cross_encoder is not None:
        return _cross_encoder

    try:
        from sentence_transformers import CrossEncoder
        _cross_encoder = CrossEncoder(
            "cross-encoder/ms-marco-MiniLM-L-6-v2",
            max_length=512,
        )
        logger.info("Cross-encoder loaded: cross-encoder/ms-marco-MiniLM-L-6-v2")
    except Exception as exc:
        logger.warning(
            "Cross-encoder unavailable ({err}). Using FAISS scores only.", err=str(exc)
        )
        _cross_encoder = None

    return _cross_encoder


# ---------------------------------------------------------------------------
# Token overlap helper (symbol-name relevance)
# ---------------------------------------------------------------------------

def _token_overlap(query: str, text: Optional[str]) -> float:
    """
    Compute normalised Jaccard-like token overlap between query and text.
    Returns 0.0 if text is None or empty.
    """
    if not text:
        return 0.0

    q_tokens = set(re.findall(r"\w+", query.lower()))
    t_tokens = set(re.findall(r"\w+", text.lower()))

    if not q_tokens or not t_tokens:
        return 0.0

    intersection = q_tokens & t_tokens
    union = q_tokens | t_tokens
    return len(intersection) / len(union)


# ---------------------------------------------------------------------------
# Position normalisation helper
# ---------------------------------------------------------------------------

def _normalise_position(start_line: int, max_line: int = 5_000) -> float:
    """
    Map start_line → [0, 1] where 1 = line 0 (top of file), 0 = deep in file.
    """
    if max_line <= 0:
        return 0.5
    normalised = 1.0 - min(start_line, max_line) / max_line
    return normalised


# ---------------------------------------------------------------------------
# Main ranking function
# ---------------------------------------------------------------------------

def rank_chunks(
    query: str,
    chunks: List[Dict[str, Any]],
    use_cross_encoder: bool = True,
) -> List[Dict[str, Any]]:
    """
    Re-rank a list of retrieved chunk dicts.

    Each chunk dict must have at minimum:
        file_path, start_line, content, score (FAISS cosine score),
    and optionally:
        chunk_type, symbol_name, language.

    Args:
        query:             The user's original search / question string.
        chunks:            Candidate chunks from RetrievalService.
        use_cross_encoder: Whether to attempt cross-encoder re-scoring.

    Returns:
        A new list sorted by descending composite_score.
        Each dict gains a 'composite_score' key.
    """
    if not chunks:
        return []

    # ---------------------------------------------------------------- #
    # Optional: cross-encoder scores
    # ---------------------------------------------------------------- #
    ce_scores: List[float] = [0.0] * len(chunks)

    if use_cross_encoder:
        ce_model = _get_cross_encoder()
        if ce_model is not None:
            try:
                pairs = [(query, c.get("content", "")[:512]) for c in chunks]
                raw_ce = ce_model.predict(pairs)
                # Normalise raw logits → [0, 1] via min-max scaling
                min_ce, max_ce = float(min(raw_ce)), float(max(raw_ce))
                spread = max_ce - min_ce or 1.0
                ce_scores = [(float(s) - min_ce) / spread for s in raw_ce]
            except Exception as exc:
                logger.warning("Cross-encoder scoring failed: {err}", err=str(exc))

    # ---------------------------------------------------------------- #
    # Composite scoring
    # ---------------------------------------------------------------- #
    scored: List[Dict[str, Any]] = []

    for chunk, ce_score in zip(chunks, ce_scores):
        faiss_score = float(chunk.get("score", 0.0))

        # Clamp FAISS cosine score to [0, 1] (it can be slightly > 1 due to
        # floating-point in normalised inner-product)
        faiss_score = min(max(faiss_score, 0.0), 1.0)

        symbol_score = _token_overlap(query, chunk.get("symbol_name"))
        position_score = _normalise_position(chunk.get("start_line", 0))

        composite = (
            WEIGHT_FAISS_SCORE * faiss_score
            + WEIGHT_CROSS_ENCODER * ce_score
            + WEIGHT_SYMBOL_MATCH * symbol_score
            + WEIGHT_POSITION * position_score
        )

        # Apply chunk-type boost
        chunk_type = chunk.get("chunk_type", "window")
        boost = CHUNK_TYPE_BOOST.get(chunk_type, 1.0)
        composite *= boost

        chunk = {**chunk, "composite_score": round(composite, 6)}
        scored.append(chunk)

    # Sort descending by composite score
    scored.sort(key=lambda c: c["composite_score"], reverse=True)

    logger.debug(
        "Ranked {n} chunks for query '{q}' (top score: {s:.4f})",
        n=len(scored),
        q=query[:60],
        s=scored[0]["composite_score"] if scored else 0.0,
    )

    return scored


# ---------------------------------------------------------------------------
# Convenience: apply ranking within a retrieval result dict
# ---------------------------------------------------------------------------

def apply_ranking(
    query: str,
    retrieval_result: Dict[str, Any],
    use_cross_encoder: bool = True,
) -> Dict[str, Any]:
    """
    Wrap rank_chunks() to work directly on a RetrievalService result dict.
    Returns a mutated copy with results replaced by ranked results.
    """
    results = retrieval_result.get("results", [])
    ranked = rank_chunks(query, results, use_cross_encoder=use_cross_encoder)
    return {**retrieval_result, "results": ranked}
