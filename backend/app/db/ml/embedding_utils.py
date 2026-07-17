# backend/app/ml/embedding_utils.py
"""
CodeSense — Embedding Utility Functions

Standalone helpers that operate on raw numpy vectors:
  - L2 normalisation
  - Cosine similarity (single and matrix)
  - Similarity ranking
  - Vector serialisation / deserialisation (for MongoDB storage)
  - Dimensionality checks
"""

from __future__ import annotations

from typing import List, Tuple

import numpy as np


# ---------------------------------------------------------------------------
# Normalisation
# ---------------------------------------------------------------------------

def l2_normalize(vec: np.ndarray) -> np.ndarray:
    """
    L2-normalise a 1-D or 2-D float32 array in-place equivalent.
    Returns a new array; input is not modified.
    """
    vec = np.asarray(vec, dtype=np.float32)
    if vec.ndim == 1:
        norm = np.linalg.norm(vec)
        return vec / (norm + 1e-10)
    # 2-D: normalise each row
    norms = np.linalg.norm(vec, axis=1, keepdims=True)
    return vec / (norms + 1e-10)


def is_normalised(vec: np.ndarray, tol: float = 1e-4) -> bool:
    """Return True if all rows of vec have unit L2 norm (within tolerance)."""
    if vec.ndim == 1:
        return abs(np.linalg.norm(vec) - 1.0) < tol
    norms = np.linalg.norm(vec, axis=1)
    return bool(np.all(np.abs(norms - 1.0) < tol))


# ---------------------------------------------------------------------------
# Similarity
# ---------------------------------------------------------------------------

def cosine_similarity(a: np.ndarray, b: np.ndarray) -> float:
    """
    Cosine similarity between two 1-D vectors.
    Assumes L2-normalised inputs (inner product == cosine sim).
    """
    a = l2_normalize(np.asarray(a, dtype=np.float32))
    b = l2_normalize(np.asarray(b, dtype=np.float32))
    return float(np.dot(a, b))


def cosine_matrix(query: np.ndarray, corpus: np.ndarray) -> np.ndarray:
    """
    Compute cosine similarity between a query vector and a corpus matrix.

    Args:
        query:  shape (dim,)
        corpus: shape (N, dim)

    Returns:
        shape (N,) — similarity score per corpus vector
    """
    q = l2_normalize(query.reshape(-1))
    c = l2_normalize(corpus)
    return c @ q


def top_k_indices(scores: np.ndarray, k: int) -> np.ndarray:
    """Return indices of the top-k scores (descending order)."""
    k = min(k, len(scores))
    return np.argsort(scores)[::-1][:k]


def rank_by_similarity(
    query: np.ndarray,
    corpus: np.ndarray,
    k: int = 5,
) -> List[Tuple[int, float]]:
    """
    Return (index, score) tuples for the top-k most similar corpus vectors.

    Args:
        query:  shape (dim,)
        corpus: shape (N, dim)
        k:      number of results

    Returns:
        List of (idx, score) sorted by descending score.
    """
    scores = cosine_matrix(query, corpus)
    indices = top_k_indices(scores, k)
    return [(int(i), float(scores[i])) for i in indices]


# ---------------------------------------------------------------------------
# Serialisation helpers
# ---------------------------------------------------------------------------

def vec_to_list(vec: np.ndarray) -> List[float]:
    """Convert a float32 numpy vector to a Python list (for JSON / MongoDB)."""
    return vec.astype(np.float32).tolist()


def list_to_vec(lst: List[float]) -> np.ndarray:
    """Convert a Python list back to a float32 numpy vector."""
    return np.array(lst, dtype=np.float32)


# ---------------------------------------------------------------------------
# Dimension helpers
# ---------------------------------------------------------------------------

def assert_dim(vec: np.ndarray, expected_dim: int, name: str = "vector") -> None:
    """Raise ValueError if vec does not have expected_dim dimensions."""
    actual = vec.shape[-1] if vec.ndim > 0 else 0
    if actual != expected_dim:
        raise ValueError(
            f"{name} has dimension {actual}, expected {expected_dim}."
        )


def pad_or_truncate(vec: np.ndarray, target_dim: int) -> np.ndarray:
    """Pad with zeros or truncate a 1-D vector to target_dim."""
    current_dim = vec.shape[0]
    if current_dim == target_dim:
        return vec
    if current_dim > target_dim:
        return vec[:target_dim]
    # pad
    return np.concatenate([vec, np.zeros(target_dim - current_dim, dtype=vec.dtype)])
