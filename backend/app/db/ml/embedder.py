# backend/app/ml/embedder.py --- The repository and the user query must be embedded by the same model
from __future__ import annotations

from functools import lru_cache
from typing import List, Optional
import threading

import numpy as np
from app_logger import logger

from app.core.config import get_settings


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


#Wrap SentenceTransformer
class Embedder:
    """
    Thin wrapper around SentenceTransformer supporting batch and single-text
    embedding with optional L2 normalisation for cosine-similarity search.
    """

    def __init__(self, model_name: str, device: str, batch_size: int) -> None:
        self.model_name = model_name
        self._device = device
        self._batch_size = batch_size
        self._model = None
        self._lock = threading.Lock()

    def _load_model(self):
        if self._model is not None:
            return self._model
            
        with self._lock:
            if self._model is not None:
                return self._model
                
            logger.info(
                "Lazy loading embedding model '{model}' on device '{device}' …",
                model=self.model_name,
                device=self._device,
            )
            
            import torch
            torch.set_num_threads(1) #Limit CPU threads
            torch.set_grad_enabled(False) #CodeSense only performs Prediction not Training
            
            from sentence_transformers import SentenceTransformer
            self._model = SentenceTransformer(self.model_name, device=self._device)
            
            logger.info(
                "Embedding model loaded. dim={dim}, max_seq_len={seq}",
                dim=self.dim,
                seq=self.max_seq_length,
            )
            return self._model

    #Embed one string
    def embed_text(self, text: str, normalize: bool = True) -> np.ndarray:
        model = self._load_model()
        vec = model.encode(
            text,
            batch_size=1,
            show_progress_bar=False,
            convert_to_numpy=True,
            normalize_embeddings=normalize,
        )
        return vec.astype(np.float32)

    def embed_batch( #Embed a list of strings --- Neural networks prefer batches --- improves throughput
        self,
        texts: List[str],
        normalize: bool = True,
        show_progress: Optional[bool] = None,
    ) -> np.ndarray:
        if not texts:
            return np.empty((0, self.dim), dtype=np.float32)

        if show_progress is None:
            show_progress = len(texts) > 100

        logger.info(
            "Embedding {n} texts in batches of {b} …",
            n=len(texts),
            b=self._batch_size,
        )
        model = self._load_model()
        vecs = model.encode(
            texts,
            batch_size=self._batch_size,
            show_progress_bar=show_progress,
            convert_to_numpy=True,
            normalize_embeddings=normalize,
        )
        return vecs.astype(np.float32)

    #Embed a code chunk with optional language-prefix --- Language information helps distinguish similar syntax across languages.
    def embed_code_chunk(self, content: str, language: Optional[str] = None) -> np.ndarray:
        if language and language not in {"unknown", "other"}:
            text = f"{language}: {content}"
        else:
            text = content
        return self.embed_text(text)

   #Returns Embedding dimension
    @property
    def dim(self) -> int:
        """Embedding dimension for this model."""
        if self.model_name in SUPPORTED_MODELS:
            return SUPPORTED_MODELS[self.model_name]["dim"]
        model = self._load_model()
        return model.get_sentence_embedding_dimension()

    #Returns Maximum tokens
    @property
    def max_seq_length(self) -> int:
        if self.model_name in SUPPORTED_MODELS:
            return SUPPORTED_MODELS[self.model_name]["max_seq_length"]
        model = self._load_model()
        return model.max_seq_length

    #Useful for Health APIs,Debugging,Logging
    def model_info(self) -> dict:
        return {
            "model_name": self.model_name,
            "dim": self.dim,
            "max_seq_length": self.max_seq_length,
            "device": self._device,
            "batch_size": self._batch_size,
        }


#Return the global cached Embedder instance (loaded once per process)
@lru_cache(maxsize=1)
def get_embedder() -> Embedder:
    settings = get_settings()
    return Embedder(
        model_name=settings.EMBEDDING_MODEL,
        device=settings.EMBEDDING_DEVICE,
        batch_size=settings.EMBEDDING_BATCH_SIZE,
    )
