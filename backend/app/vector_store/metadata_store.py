# backend/app/vector_store/metadata_store.py --- Stores information about the embedded vectors
from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, List, Optional

from app_logger import logger

from app.core.config import get_settings


CHUNK_META_FILE = "chunk_meta.json"


#Manage one repository's metadata --- One Repository -> One MetadataStore Object -> One chunk_meta.json
class MetadataStore:
    def __init__(self, repo_id: str, index_path: Optional[str] = None) -> None: #contains All Metadata in memory
        self.repo_id = repo_id
        settings = get_settings()
        self._index_dir = Path(index_path or (settings.VECTOR_STORE_DIR / repo_id))
        self._index_dir.mkdir(parents=True, exist_ok=True)
        self._meta_path = self._index_dir / CHUNK_META_FILE
        self._records: List[Dict[str, Any]] = []
        self._loaded = False

    
    def build_from_chunks( #Create metadata after chunking --- output:chunk_meta.json
        self,
        chunks: List[Dict[str, Any]],
        chunk_ids: Optional[List[str]] = None,
    ) -> None:
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
    #Back-fill MongoDB chunk IDs after insert_many returns them
    def patch_chunk_ids(self, chunk_ids: List[str]) -> None:
        self._ensure_loaded()
        for i, cid in enumerate(chunk_ids):
            if i < len(self._records):
                self._records[i]["chunk_id"] = cid

    #Write metadata to disk using a streaming approach to prevent OOM
    def save(self) -> None:
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
        if self._meta_path.exists():
            try:
                self._meta_path.unlink()
            except OSError:
                pass
        os.replace(tmp_path, self._meta_path)
            
        logger.info(
            "[{id}] chunk_meta.json saved ({n} records) via stream.",
            id=self.repo_id,
            n=len(self._records),
        )
    #Load metadata from disk
    def load(self) -> None:
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

    #Return metadata for a single FAISS integer ID
    def get_by_faiss_id(self, faiss_id: int) -> Optional[Dict[str, Any]]:
        self._ensure_loaded()
        if 0 <= faiss_id < len(self._records):
            return self._records[faiss_id]
        return None
    #Return metadata for a list of FAISS IDs (preserves order, None on miss)
    def get_many(self, faiss_ids: List[int]) -> List[Optional[Dict[str, Any]]]:
        self._ensure_loaded()
        return [self.get_by_faiss_id(fid) for fid in faiss_ids]
    #Return only those faiss_ids whose language matches the filte
    def filter_by_language(
        self,
        faiss_ids: List[int],
        language: str,
    ) -> List[int]:
        self._ensure_loaded()
        return [
            fid for fid in faiss_ids
            if self.get_by_faiss_id(fid) is not None
            and self.get_by_faiss_id(fid).get("language") == language
        ]
    #Return only those faiss_ids of the given chunk type
    def filter_by_chunk_type(
        self,
        faiss_ids: List[int],
        chunk_type: str,
    ) -> List[int]:
        self._ensure_loaded()
        return [
            fid for fid in faiss_ids
            if self.get_by_faiss_id(fid) is not None
            and self.get_by_faiss_id(fid).get("chunk_type") == chunk_type
        ]
    #Return all metadata records
    def all_records(self) -> List[Dict[str, Any]]:
        self._ensure_loaded()
        return list(self._records)
    #total chunks
    @property
    def count(self) -> int:
        self._ensure_loaded()
        return len(self._records)

    #Lazy Loading --- Don't load something until it is actually needed
    def _ensure_loaded(self) -> None:
        if not self._loaded:
            self.load()
