# backend/app/ml/embedding_pipeline.py
"""
CodeSense — Embedding Generation Pipeline (v2)

Orchestrates:
  1. Text preparation (code chunk pre-processing & truncation)
  2. Batch embedding via the Embedder singleton
  3. Vector validation & normalisation sanity checks
  4. Per-chunk embedding metadata attachment

This module is called directly by pipeline.py during ingestion.
"""

from __future__ import annotations

import time
from typing import Any, Dict, List, Optional, Tuple

import numpy as np
from app_logger import logger

from app.ml.embedder import get_embedder


# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

# Hard cap on characters fed to the model (prevents silently truncated vecs).
# all-MiniLM-L6-v2: 256 tokens ≈ ~1 000 chars.
# codebert-base:    512 tokens ≈ ~2 000 chars.
MAX_CHARS_PER_CHUNK = 2_000


# ---------------------------------------------------------------------------
# Text preparation helpers
# ---------------------------------------------------------------------------

def _prepare_text(chunk: Dict[str, Any]) -> str:
    """
    Build a text representation of a code chunk for embedding.

    Strategy:
      - For function/class chunks include the symbol name as a header
        so the model can associate the name with the body.
      - Window chunks are embedded as-is.
      - All texts are truncated to MAX_CHARS_PER_CHUNK to keep
        token budgets within the model's context window.
    """
    content: str = chunk.get("content", "")
    chunk_type: str = chunk.get("chunk_type", "window")
    symbol_name: Optional[str] = chunk.get("symbol_name")
    language: Optional[str] = chunk.get("language")

    parts: List[str] = []

    if language and language not in {"unknown", "other"}:
        parts.append(f"[{language}]")

    if chunk_type in {"function", "class"} and symbol_name:
        parts.append(f"{chunk_type}: {symbol_name}")

    parts.append(content)

    text = "\n".join(parts)
    # Truncate — avoid feeding entire files into one chunk by mistake
    return text[:MAX_CHARS_PER_CHUNK]


def prepare_texts(chunks: List[Dict[str, Any]]) -> List[str]:
    """Return a list of embedding-ready strings, one per chunk."""
    return [_prepare_text(c) for c in chunks]


# ---------------------------------------------------------------------------
# Core pipeline function
# ---------------------------------------------------------------------------

def generate_embeddings(
    chunks: List[Dict[str, Any]],
    show_progress: Optional[bool] = None,
) -> Tuple[np.ndarray, Dict[str, Any]]:
    """
    Generate embeddings for a list of chunk dicts.

    Args:
        chunks:        List of chunk dicts as produced by chunker.py.
        show_progress: Override progress-bar display. None = auto.

    Returns:
        (vectors, stats) where:
          vectors — float32 array of shape (N, dim)
          stats   — dict with timing, shape, model info
    """
    if not chunks:
        logger.warning("generate_embeddings called with empty chunk list.")
        embedder = get_embedder()
        return np.empty((0, embedder.dim), dtype=np.float32), {"count": 0}

    embedder = get_embedder()
    t0 = time.perf_counter()

    texts = prepare_texts(chunks)
    logger.info(
        "Embedding pipeline: {n} chunks, model={m}",
        n=len(texts),
        m=embedder.model_name,
    )

    vectors = embedder.embed_batch(texts, normalize=True, show_progress=show_progress)

    elapsed = time.perf_counter() - t0

    # Sanity checks
    assert vectors.shape == (len(chunks), embedder.dim), (
        f"Unexpected vector shape {vectors.shape}, expected ({len(chunks)}, {embedder.dim})"
    )
    assert vectors.dtype == np.float32, "Embeddings must be float32"

    stats: Dict[str, Any] = {
        "count": len(chunks),
        "dim": embedder.dim,
        "model": embedder.model_name,
        "elapsed_s": round(elapsed, 3),
        "throughput_per_s": round(len(chunks) / max(elapsed, 1e-6), 1),
        "shape": list(vectors.shape),
    }
    logger.info(
        "Embedding complete: {n} vectors in {t:.2f}s ({tp:.1f}/s)",
        n=stats["count"],
        t=stats["elapsed_s"],
        tp=stats["throughput_per_s"],
    )

    return vectors, stats


# ---------------------------------------------------------------------------
# Convenience: embed a single query string
# ---------------------------------------------------------------------------

def embed_query(query: str) -> np.ndarray:
    """
    Embed a user search query for retrieval.
    Strips leading/trailing whitespace and applies L2 normalisation.
    Returns shape (dim,), float32.
    """
    embedder = get_embedder()
    cleaned = query.strip()
    if not cleaned:
        logger.warning("embed_query received an empty string.")
        return np.zeros(embedder.dim, dtype=np.float32)
    return embedder.embed_text(cleaned, normalize=True)
