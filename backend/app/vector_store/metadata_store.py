# backend/app/vector_store/metadata_store.py
"""
CodeSense — Vector Store Metadata Persistence

Maintains a lightweight JSON sidecar alongside every FAISS index that maps
FAISS integer IDs → chunk metadata (file_path, start_line, end_line, language,
chunk_type, symbol_name).

This enables fast metadata lookups without a MongoDB round-trip during search,
and serves as a fallback when the DB is unavailable.

File layout:
  {VECTOR_STORE_DIR}/{repo_id}/
    index.faiss         ← FAISS binary (managed by FAISSStore)
    index_meta.json     ← FAISS-level metadata (managed by FAISSStore)
    chunk_meta.json     ← per-vector chunk metadata (managed HERE)
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, List, Optional

from app_logger import logger

from app.core.config import get_settings


CHUNK_META_FILE = "chunk_meta.json"


# ---------------------------------------------------------------------------
# MetadataStore
# ---------------------------------------------------------------------------

class MetadataStore:
    """
    Reads and writes chunk_meta.json for a given repository.

    The JSON structure is a list (indexed by FAISS integer ID):
        [
          {
            "faiss_id": 0,
            "chunk_id": "<mongo_id>",
            "file_path": "src/main.py",
            "language": "python",
            "start_line": 1,
            "end_line": 40,
            "chunk_type": "function",
            "symbol_name": "process_files",
          },
          ...
        ]
    """

    def __init__(self, repo_id: str, index_path: Optional[str] = None) -> None:
        self.repo_id = repo_id
        settings = get_settings()
        self._index_dir = Path(index_path or (settings.VECTOR_STORE_DIR / repo_id))
        self._index_dir.mkdir(parents=True, exist_ok=True)
        self._meta_path = self._index_dir / CHUNK_META_FILE
        self._records: List[Dict[str, Any]] = []
        self._loaded = False

    # ------------------------------------------------------------------ #
    # Build
    # ------------------------------------------------------------------ #

    def build_from_chunks(
        self,
        chunks: List[Dict[str, Any]],
        chunk_ids: Optional[List[str]] = None,
    ) -> None:
        """
        Populate in-memory metadata from the chunk dicts produced by
        chunker.py.  Call save() afterwards to persist.

        Args:
            chunks:    List of chunk dicts (same order as vectors in FAISS).
            chunk_ids: Optional list of MongoDB ObjectId strings, one per chunk.
                       If omitted, chunk_id fields will be left empty.
        """
        self._records = []
        for faiss_id, chunk in enumerate(chunks):
            record: Dict[str, Any] = {
                "faiss_id": faiss_id,
                "chunk_id": chunk_ids[faiss_id] if chunk_ids else "",
                "file_path": chunk.get("file_path", ""),
                "language": chunk.get("language", "unknown"),
                "start_line": chunk.get("start_line", 0),
                "end_line": chunk.get("end_line", 0),
                "chunk_type": chunk.get("chunk_type", "window"),
                "symbol_name": chunk.get("symbol_name"),
                "chunk_index": chunk.get("chunk_index", faiss_id),
                "token_count": chunk.get("token_count", 0),
            }
            self._records.append(record)
        self._loaded = True
        logger.info(
            "[{id}] MetadataStore: {n} chunk records built.",
            id=self.repo_id,
            n=len(self._records),
        )

    def patch_chunk_ids(self, chunk_ids: List[str]) -> None:
        """Back-fill MongoDB chunk IDs after insert_many returns them."""
        self._ensure_loaded()
        for i, cid in enumerate(chunk_ids):
            if i < len(self._records):
                self._records[i]["chunk_id"] = cid

    # ------------------------------------------------------------------ #
    # Persist
    # ------------------------------------------------------------------ #

    def save(self) -> None:
        """Write metadata to disk using a streaming approach to prevent OOM."""
        import os
        tmp_path = self._meta_path.with_suffix(".tmp")
        with open(tmp_path, "w", encoding="utf-8") as f:
            f.write("[\n")
            for i, record in enumerate(self._records):
                json.dump(record, f, ensure_ascii=False)
                if i < len(self._records) - 1:
                    f.write(",\n")
                else:
                    f.write("\n")
            f.write("]")
        os.replace(tmp_path, self._meta_path)
            
        logger.info(
            "[{id}] chunk_meta.json saved ({n} records) via stream.",
            id=self.repo_id,
            n=len(self._records),
        )

    def load(self) -> None:
        """Load metadata from disk."""
        if not self._meta_path.exists():
            logger.warning(
                "[{id}] chunk_meta.json not found at {p}.",
                id=self.repo_id,
                p=str(self._meta_path),
            )
            self._records = []
        else:
            with open(self._meta_path, "r", encoding="utf-8") as f:
                self._records = json.load(f)
        self._loaded = True
        logger.info(
            "[{id}] chunk_meta.json loaded ({n} records).",
            id=self.repo_id,
            n=len(self._records),
        )

    def exists(self) -> bool:
        return self._meta_path.exists()

    # ------------------------------------------------------------------ #
    # Lookups
    # ------------------------------------------------------------------ #

    def get_by_faiss_id(self, faiss_id: int) -> Optional[Dict[str, Any]]:
        """Return metadata for a single FAISS integer ID."""
        self._ensure_loaded()
        if 0 <= faiss_id < len(self._records):
            return self._records[faiss_id]
        return None

    def get_many(self, faiss_ids: List[int]) -> List[Optional[Dict[str, Any]]]:
        """Return metadata for a list of FAISS IDs (preserves order, None on miss)."""
        self._ensure_loaded()
        return [self.get_by_faiss_id(fid) for fid in faiss_ids]

    def filter_by_language(
        self,
        faiss_ids: List[int],
        language: str,
    ) -> List[int]:
        """Return only those faiss_ids whose language matches the filter."""
        self._ensure_loaded()
        return [
            fid for fid in faiss_ids
            if self.get_by_faiss_id(fid) is not None
            and self.get_by_faiss_id(fid).get("language") == language
        ]

    def filter_by_chunk_type(
        self,
        faiss_ids: List[int],
        chunk_type: str,
    ) -> List[int]:
        """Return only those faiss_ids of the given chunk type."""
        self._ensure_loaded()
        return [
            fid for fid in faiss_ids
            if self.get_by_faiss_id(fid) is not None
            and self.get_by_faiss_id(fid).get("chunk_type") == chunk_type
        ]

    def all_records(self) -> List[Dict[str, Any]]:
        """Return all metadata records."""
        self._ensure_loaded()
        return list(self._records)

    @property
    def count(self) -> int:
        self._ensure_loaded()
        return len(self._records)

    # ------------------------------------------------------------------ #
    # Internal
    # ------------------------------------------------------------------ #

    def _ensure_loaded(self) -> None:
        if not self._loaded:
            self.load()
