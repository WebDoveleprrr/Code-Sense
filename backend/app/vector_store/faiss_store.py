# backend/app/vector_store/faiss_store.py --- manages the storage of vectors after embedding
from __future__ import annotations

import json
import time
from collections import OrderedDict
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Tuple

import faiss
import numpy as np
from app_logger import logger

from app.core.config import get_settings

INDEX_FILE = "index.faiss"
META_FILE = "index_meta.json"

# Threshold above which an IVF index is preferred for speed
IVF_THRESHOLD = 10_000
# nlist cells for IVF (rule of thumb: sqrt(N))
IVF_NLIST = 100


# Global LRU cache for indices to prevent memory leaks --- Max capacity = 3 repo --- Cache in RAM(fast)
_index_cache: OrderedDict[str, Tuple[faiss.Index, Dict]] = OrderedDict()
MAX_CACHE_SIZE = 3

#Maintain this LRU cache --- when 4th repo is added,remove the first (least recently used(LRU)) repo
def _manage_cache(repo_id: str, index: faiss.Index, meta: Dict) -> None:
    global _index_cache
    if repo_id in _index_cache:
        _index_cache.move_to_end(repo_id)
    _index_cache[repo_id] = (index, meta)
    
    if len(_index_cache) > MAX_CACHE_SIZE:
        evicted_id, _ = _index_cache.popitem(last=False)
        logger.info(f"FAISS cache full (>{MAX_CACHE_SIZE}). Evicted index for repo: {evicted_id}")


class FAISSStore:
    #Prepare storage location
    def __init__(self, repo_id: str, index_path: Optional[str] = None) -> None:
        self.repo_id = repo_id
        settings = get_settings()
        self._index_dir = Path(index_path or (settings.VECTOR_STORE_DIR / repo_id))
        self._index_dir.mkdir(parents=True, exist_ok=True)
        self._index: Optional[faiss.Index] = None
        self._meta: Dict = {}

    #Input: vectors --- Shape: (N, dimension) --- Example: 500 chunks,384 dimensions
    def build(self, vectors: np.ndarray, model_name: str = "") -> None:
        if vectors.ndim != 2:
            raise ValueError(f"Expected 2-D array, got shape {vectors.shape}")

        vectors = _to_float32(vectors)
        n, dim = vectors.shape

        self.initialize(dim, expected_count=n, model_name=model_name)
        
        if n >= IVF_THRESHOLD:
            # Rebuild properly for IVF if necessary
            self._index = _build_ivf_index(vectors, dim)
            self._meta["index_type"] = "IVFFlat"
        else:
            self._index.add(vectors)
            
        self._meta["ntotal"] = self._index.ntotal

        logger.info(
            "[{id}] FAISS {type} index built — {n} vectors (dim={d}).",
            id=self.repo_id,
            type=self._meta["index_type"],
            n=n,
            d=dim,
        )

    #Create empty FAISS index
    def initialize(self, dim: int, expected_count: int = 0, model_name: str = "") -> None:
        self._index = faiss.IndexFlatIP(dim)
        index_type = "FlatIP"
        
        self._meta = {
            "repo_id": self.repo_id,
            "dim": dim,
            "ntotal": 0,
            "index_type": index_type,
            "model_name": model_name,
            "created_at": datetime.utcnow().isoformat(),
        }
        logger.info("[{id}] FAISS initialized {type} index (dim={d}).", id=self.repo_id, type=index_type, d=dim)
    
    #Append vectors progressively to the initialized index
    def add_vectors(self, vectors: np.ndarray) -> None:
        if self._index is None:
            raise RuntimeError("Index not initialized.")
            
        vectors = _to_float32(vectors)
        self._index.add(vectors)
        self._meta["ntotal"] = self._index.ntotal

    #Atomically write the FAISS index + metadata sidecar to disk
    def save(self) -> None:
        if self._index is None:
            raise RuntimeError("Cannot save: index has not been built or loaded.")

        index_path = self._index_dir / INDEX_FILE
        meta_path = self._index_dir / META_FILE

        # Write to a temp file then replace (atomic on POSIX, overwrites on Windows)
        tmp_index = index_path.with_suffix(".tmp")
        faiss.write_index(self._index, str(tmp_index))
        import os
        if index_path.exists():
            try:
                index_path.unlink()
            except OSError:
                pass
        os.replace(str(tmp_index), str(index_path))

        meta_path.write_text(json.dumps(self._meta, indent=2))
        
        # Cache globally with LRU management
        _manage_cache(self.repo_id, self._index, self._meta)
        
        logger.info(
            "[{id}] FAISS index saved → {path}  ({n} vectors).",
            id=self.repo_id,
            path=str(index_path),
            n=self._meta.get("ntotal", "?"),
        )

    #Load the FAISS index (and metadata sidecar) from disk or memory cache
    def load(self) -> None:
        global _index_cache
        
        if self.repo_id in _index_cache:
            _index_cache.move_to_end(self.repo_id)
            self._index, self._meta = _index_cache[self.repo_id]
            logger.info("[{id}] FAISS index loaded from memory cache.", id=self.repo_id)
            return

        index_path = self._index_dir / INDEX_FILE
        meta_path = self._index_dir / META_FILE

        if not index_path.exists():
            raise FileNotFoundError(
                f"FAISS index not found at {index_path}. "
                "Run ingestion first, or check VECTOR_STORE_DIR config."
            )

        self._index = faiss.read_index(str(index_path))

        if meta_path.exists():
            self._meta = json.loads(meta_path.read_text())
        _manage_cache(self.repo_id, self._index, self._meta)

        logger.info(
            "[{id}] FAISS index loaded — {n} vectors.",
            id=self.repo_id,
            n=self._index.ntotal,
        )

    #Return True if an index file exists on disk for this repo
    def exists(self) -> bool:
        return (self._index_dir / INDEX_FILE).exists()

    #Remove all index files from disk and clean memory cache
    def delete(self) -> None:
        global _index_cache
        import shutil
        if self._index_dir.exists():
            shutil.rmtree(self._index_dir, ignore_errors=True)
        _index_cache.pop(self.repo_id, None)
        self._index = None
        self._meta = {}
        logger.info("[{id}] FAISS index deleted.", id=self.repo_id)

    #Most important retrieval function(ssingle query search) --- Returns (faiss_ids, scores) sorted by descending score --- Loads the index from disk automatically if not in memory.
    def search(
        self,
        query_vec: np.ndarray,
        top_k: int = 5,
    ) -> Tuple[List[int], List[float]]:
        self._ensure_loaded()
        query_vec = _to_float32(query_vec)
        if query_vec.ndim == 1:
            query_vec = query_vec.reshape(1, -1)

        actual_k = min(top_k, self._index.ntotal)
        scores, ids = self._index.search(query_vec, actual_k)

        return ids[0].tolist(), scores[0].tolist()

    #Multi-query search(more efficient) --- Returns (all_ids, all_scores) each of length len(query_vecs)
    def batch_search(
        self,
        query_vecs: np.ndarray,
        top_k: int = 5,
    ) -> Tuple[List[List[int]], List[List[float]]]:
        self._ensure_loaded()
        query_vecs = _to_float32(query_vecs)
        if query_vecs.ndim == 1:
            query_vecs = query_vecs.reshape(1, -1)

        actual_k = min(top_k, self._index.ntotal)
        scores, ids = self._index.search(query_vecs, actual_k)

        return ids.tolist(), scores.tolist()

    #Number of vectors stored in the index
    @property
    def total(self) -> int:
        if self._index is None:
            if self.exists():
                self.load()
            else:
                return 0
        return self._index.ntotal

    #Embedding dimension, or None if not yet built/loaded
    @property
    def dim(self) -> Optional[int]:
        if self._index is not None:
            return self._index.d
        return self._meta.get("dim")

    #Return a health dict describing the index state
    def health(self) -> Dict:
        loaded = self._index is not None
        on_disk = self.exists()
        return {
            "repo_id": self.repo_id,
            "loaded": loaded,
            "on_disk": on_disk,
            "total": self._index.ntotal if loaded else None,
            "dim": self.dim,
            "index_type": self._meta.get("index_type"),
            "model_name": self._meta.get("model_name"),
            "created_at": self._meta.get("created_at"),
        }

    #Lazy loading --- Instead of Load Every Index At Startup,Load Only When Needed --- Saves memory
    def _ensure_loaded(self) -> None:
        if self._index is None:
            self.load()


#Advanced optimization --- Faster Search on huge datasets
def _build_ivf_index(vectors: np.ndarray, dim: int) -> faiss.Index:
    nlist = min(IVF_NLIST, len(vectors) // 10 or 1)
    quantiser = faiss.IndexFlatIP(dim)
    index = faiss.IndexIVFFlat(quantiser, dim, nlist, faiss.METRIC_INNER_PRODUCT)
    index.train(vectors)
    index.add(vectors)
    return index


def _to_float32(arr: np.ndarray) -> np.ndarray:
    if arr.dtype != np.float32:
        return arr.astype(np.float32)
    return arr
