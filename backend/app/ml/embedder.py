# backend/app/ml/embedder.py
"""
CodeSense — Sentence-Transformer Embedding Engine (v2)

Supports:
  - all-MiniLM-L6-v2  (fast, 384-dim, general-purpose)
  - microsoft/codebert-base  (code-optimised, 768-dim)
  - any other sentence-transformers-compatible model

Singleton pattern: the model is loaded once and reused across requests.
"""

from __future__ import annotations

from functools import lru_cache
from typing import List, Optional

import numpy as np
from app_logger import logger
from sentence_transformers import SentenceTransformer
import torch

torch.set_num_threads(1)
torch.set_grad_enabled(False)

from app.core.config import get_settings


# ---------------------------------------------------------------------------
# Supported model catalogue
# ---------------------------------------------------------------------------

SUPPORTED_MODELS = {
    # Fast, compact — default for most use-cases
    "all-MiniLM-L6-v2": {
        "dim": 384,
        "description": "Fast, general-purpose semantic model (384-dim)",
        "max_seq_length": 256,
    },
    # Code-optimised (larger but better for code semantics)
    "microsoft/codebert-base": {
        "dim": 768,
        "description": "Code-specific BERT model by Microsoft (768-dim)",
        "max_seq_length": 512,
    },
    # Balanced — good on code + natural language
    "all-mpnet-base-v2": {
        "dim": 768,
        "description": "High-quality general model (768-dim)",
        "max_seq_length": 384,
    },
}


# ---------------------------------------------------------------------------
# Embedder class
# ---------------------------------------------------------------------------

class Embedder:
    """
    Thin wrapper around SentenceTransformer supporting batch and single-text
    embedding with optional L2 normalisation for cosine-similarity search.
    """

    def __init__(self, model_name: str, device: str, batch_size: int) -> None:
        self.model_name = model_name
        self._device = device
        self._batch_size = batch_size

        logger.info(
            "Loading embedding model '{model}' on device '{device}' …",
            model=model_name,
            device=device,
        )
        self._model = SentenceTransformer(model_name, device=device)
        logger.info(
            "Embedding model loaded. dim={dim}, max_seq_len={seq}",
            dim=self.dim,
            seq=self._model.max_seq_length,
        )

    # ------------------------------------------------------------------ #
    # Core encode methods
    # ------------------------------------------------------------------ #

    def embed_text(self, text: str, normalize: bool = True) -> np.ndarray:
        """
        Embed a single string.
        Returns shape (dim,), dtype float32.
        """
        vec = self._model.encode(
            text,
            batch_size=1,
            show_progress_bar=False,
            convert_to_numpy=True,
            normalize_embeddings=normalize,
        )
        return vec.astype(np.float32)

    @torch.inference_mode()
    def embed_batch(
        self,
        texts: List[str],
        normalize: bool = True,
        show_progress: Optional[bool] = None,
    ) -> np.ndarray:
        """
        Embed a list of strings.
        Returns shape (N, dim), dtype float32.
        """
        if not texts:
            return np.empty((0, self.dim), dtype=np.float32)

        if show_progress is None:
            show_progress = len(texts) > 100

        logger.info(
            "Embedding {n} texts in batches of {b} …",
            n=len(texts),
            b=self._batch_size,
        )
        vecs = self._model.encode(
            texts,
            batch_size=self._batch_size,
            show_progress_bar=show_progress,
            convert_to_numpy=True,
            normalize_embeddings=normalize,
        )
        return vecs.astype(np.float32)

    def embed_code_chunk(self, content: str, language: Optional[str] = None) -> np.ndarray:
        """
        Embed a code chunk with optional language-prefix prompting.
        Prepends '<lang>:' for improved semantic discrimination when using
        models that benefit from instruction-style prefixes.
        """
        if language and language not in {"unknown", "other"}:
            text = f"{language}: {content}"
        else:
            text = content
        return self.embed_text(text)

    # ------------------------------------------------------------------ #
    # Utilities
    # ------------------------------------------------------------------ #

    @property
    def dim(self) -> int:
        """Embedding dimension for this model."""
        return self._model.get_sentence_embedding_dimension()

    @property
    def max_seq_length(self) -> int:
        return self._model.max_seq_length

    def model_info(self) -> dict:
        return {
            "model_name": self.model_name,
            "dim": self.dim,
            "max_seq_length": self.max_seq_length,
            "device": self._device,
            "batch_size": self._batch_size,
        }


# ---------------------------------------------------------------------------
# Singleton factory
# ---------------------------------------------------------------------------

@lru_cache(maxsize=1)
def get_embedder() -> Embedder:
    """Return the global cached Embedder instance (loaded once per process)."""
    settings = get_settings()
    return Embedder(
        model_name=settings.EMBEDDING_MODEL,
        device=settings.EMBEDDING_DEVICE,
        batch_size=settings.EMBEDDING_BATCH_SIZE,
    )
