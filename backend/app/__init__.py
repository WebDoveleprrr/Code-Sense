# backend/app/vector_store/__init__.py
"""
CodeSense — Vector Store Package

Public exports:
  FAISSStore     — per-repo FAISS index lifecycle (build, save, load, search)
  MetadataStore  — per-repo chunk metadata persistence (JSON sidecar)
"""

from app.vector_store.faiss_store import FAISSStore
from app.vector_store.metadata_store import MetadataStore

__all__ = ["FAISSStore", "MetadataStore"]
