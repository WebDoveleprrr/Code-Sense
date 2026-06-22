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


# ─────────────────────────────────────────────
# LINES 39-72
# PURPOSE:
# Prepares the raw code text for the embedding model by injecting metadata
# (language, symbol name) directly into the string.
#
# WHY IT EXISTS:
# Dense retrieval models (like SentenceTransformers) only understand flat strings.
# If a chunk of code is just `return x + y`, the model has no idea this belongs
# to `calculate_total` in `Python`. By prefixing the chunk with `[Python]\nfunction: calculate_total\n`,
# we inject semantic context into the vector itself. This dramatically improves
# search relevance when a user asks "how is the total calculated?".
#
# INTERVIEW QUESTION:
# "How do you handle metadata during vector retrieval?"
#
# GOOD ANSWER:
# "We use a hybrid approach. Hard filters (like repo_id or language) are handled
# by the vector database's metadata filtering (FAISS or MongoDB). Soft semantic
# metadata (like function names) are concatenated into the actual text string
# before embedding, ensuring the model's spatial mapping groups related concepts."
# ─────────────────────────────────────────────

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
    # FUNCTION PURPOSE:
    # Formats a single dictionary into an embedding-optimized string.
    
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
    
    # Truncate — avoid feeding entire files into one chunk by mistake.
    # The SentenceTransformer tokenizer truncates anyway, but doing it here
    # saves CPU cycles and string allocation memory.
    return text[:MAX_CHARS_PER_CHUNK]


def prepare_texts(chunks: List[Dict[str, Any]]) -> List[str]:
    """Return a list of embedding-ready strings, one per chunk."""
    return [_prepare_text(c) for c in chunks]


# ─────────────────────────────────────────────
# LINES 79-135
# PURPOSE:
# A generator that batches text preparation and embedding.
#
# WHY IT EXISTS:
# In earlier versions, we tried to embed 5,000 chunks by passing the entire
# list to `embedder.embed_batch`. This caused a massive RAM spike (holding
# 5,000 long strings + 5,000 float32 vectors + intermediate tokenizer tensors
# simultaneously) resulting in Render container crashes.
# 
# ARCHITECTURE NOTE:
# Using the `yield` generator pattern forces Python to process, yield, and
# garbage collect one batch (e.g., 32 vectors) at a time, completely flatlining
# the memory footprint regardless of repository size.
# 
# USED BY:
# `pipeline.py` (Step 6)
# ─────────────────────────────────────────────

def generate_embeddings_stream(
    chunks: List[Dict[str, Any]],
    show_progress: Optional[bool] = None,
):
    """
    Generate embeddings for a list of chunk dicts progressively.

    Args:
        chunks:        List of chunk dicts as produced by chunker.py.
        show_progress: Override progress-bar display. None = auto.

    Yields:
        (batch_vectors, batch_indices) where:
          batch_vectors — float32 array of shape (batch_size, dim)
          batch_indices — list of indices for this batch
    """
    import gc
    if not chunks:
        logger.warning("generate_embeddings_stream called with empty chunk list.")
        return

    embedder = get_embedder()
    t0 = time.perf_counter()

    logger.info(
        "Embedding pipeline: {n} chunks, model={m}, batch_size={b}",
        n=len(chunks),
        m=embedder.model_name,
        b=embedder._batch_size,
    )

    batch_size = embedder._batch_size

    for i in range(0, len(chunks), batch_size):
        batch_chunks = chunks[i : i + batch_size]
        
        # CPU-bound text concatenation
        batch_texts = prepare_texts(batch_chunks)
        
        # Heavy ML tensor computation (SentenceTransformers/PyTorch)
        # Note: normalize=True is critical. Without L2 normalization,
        # FAISS inner product search will not equal Cosine Similarity.
        batch_vectors = embedder.embed_batch(batch_texts, normalize=True, show_progress=False)
        
        # Sanity checks
        assert batch_vectors.dtype == np.float32, "Embeddings must be float32"
        
        # Yield to allow `pipeline.py` to insert into FAISS
        yield batch_vectors, list(range(i, i + len(batch_texts)))
        
        # Free memory explicitly after each batch.
        # This prevents the generator from keeping references to tensors alive.
        del batch_texts
        del batch_chunks
        del batch_vectors
        gc.collect()

    elapsed = time.perf_counter() - t0
    logger.info(
        "Embedding stream complete: {n} vectors in {t:.2f}s ({tp:.1f}/s)",
        n=len(chunks),
        t=elapsed,
        tp=len(chunks) / max(elapsed, 1e-6),
    )


# ---------------------------------------------------------------------------
# Convenience: embed a single query string
# ---------------------------------------------------------------------------

def embed_query(query: str) -> np.ndarray:
    """
    Embed a user search query for retrieval.
    Strips leading/trailing whitespace and applies L2 normalisation.
    Returns shape (dim,), float32.
    """
    # FUNCTION PURPOSE:
    # Used during search/RAG to convert a user's typed question into a vector.
    # Must use the exact same embedder instance and normalization flag as the pipeline.
    
    embedder = get_embedder()
    cleaned = query.strip()
    if not cleaned:
        logger.warning("embed_query received an empty string.")
        return np.zeros(embedder.dim, dtype=np.float32)
    return embedder.embed_text(cleaned, normalize=True)
