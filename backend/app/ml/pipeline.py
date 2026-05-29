# backend/app/ml/pipeline.py
"""
CodeSense — End-to-End Ingestion Pipeline (v3)

Orchestrates: clone/extract → parse → AST parse → metadata → chunk
              → embed → FAISS index → metadata sidecar → MongoDB persist → repo stats

New in v3
---------
* Delegates embedding to embedding_pipeline.generate_embeddings()
* Persists MetadataStore JSON sidecar alongside FAISS index
* Back-patches MongoDB ChunkDocuments with FAISS integer IDs post-insert
* Passes model_name into FAISSStore.build() for index metadata
"""

from __future__ import annotations

import asyncio
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List

from app_logger import logger

from app.core.config import get_settings
from app.models.chunk import ChunkDocument
from app.models.repository import RepositoryDocument, RepoSource


# ---------------------------------------------------------------------------
# Pipeline entry point
# ---------------------------------------------------------------------------

async def run_ingestion_pipeline(repo: RepositoryDocument) -> None:
    """
    Full ingestion pipeline executed as a background task.

    Steps:
      1. Acquire source   (clone GitHub / extract ZIP)
      2. Parse repository (file traversal + content read)
      3. AST parse        (language-specific symbol extraction)
      4. Metadata build   (per-file + repo-level summaries)
      5. Chunk            (semantic-aware + window fallback)
      6. Embed            (sentence-transformers batch via embedding_pipeline)
      7. FAISS index      (build + persist)
      8. Metadata sidecar (MetadataStore JSON sidecar)
      9. MongoDB persist  (ChunkDocuments with faiss_id)
     10. Repo stats update
    """
    settings = get_settings()
    repo_id = str(repo.id)

    # ---------------------------------------------------------------- #
    # Step 1 — Acquire source
    # ---------------------------------------------------------------- #
    repo_dir = await _acquire_source(repo, settings)
    logger.info("[{id}] Source at {dir}", id=repo_id, dir=str(repo_dir))

    # ---------------------------------------------------------------- #
    # Step 2 — Repository file traversal
    # ---------------------------------------------------------------- #
    from app.ml.repo_parser import parse_repository

    parsed_files = await parse_repository(repo_dir)
    logger.info("[{id}] {n} files collected.", id=repo_id, n=len(parsed_files))

    if not parsed_files:
        raise ValueError("No supported source files found in the repository.")

    # ---------------------------------------------------------------- #
    # Step 3 — AST parsing (language-specific)
    # ---------------------------------------------------------------- #
    from app.ml.parsers import parse_source

    parsed_meta: List[Dict[str, Any]] = []
    for file_dict in parsed_files:
        try:
            ast_result = parse_source(file_dict)
        except Exception as exc:
            logger.warning(
                "[{id}] AST parse failed for {fp}: {err}",
                id=repo_id,
                fp=file_dict["file_path"],
                err=exc,
            )
            ast_result = {
                "language": file_dict["language"],
                "file_path": file_dict["file_path"],
            }
        parsed_meta.append(ast_result)

    logger.info(
        "[{id}] AST parsing complete for {n} files.", id=repo_id, n=len(parsed_meta)
    )

    # ---------------------------------------------------------------- #
    # Step 4 — Metadata generation
    # ---------------------------------------------------------------- #
    from app.ml.metadata_generator import build_file_metadata, build_repo_metadata

    file_metadata_list = [
        build_file_metadata(fd, pm)
        for fd, pm in zip(parsed_files, parsed_meta)
    ]
    repo_metadata = build_repo_metadata(file_metadata_list)
    logger.info(
        "[{id}] Metadata: {funcs} funcs, {cls} classes across {files} files.",
        id=repo_id,
        funcs=repo_metadata["total_functions"],
        cls=repo_metadata["total_classes"],
        files=repo_metadata["total_files"],
    )

    # ---------------------------------------------------------------- #
    # Step 5 — Chunking (semantic-aware)
    # ---------------------------------------------------------------- #
    from app.ml.chunker import chunk_files

    chunks = chunk_files(
        parsed_files=parsed_files,
        chunk_size=settings.CHUNK_SIZE,
        overlap=settings.CHUNK_OVERLAP,
        parsed_meta=file_metadata_list,
    )
    logger.info("[{id}] {n} chunks produced.", id=repo_id, n=len(chunks))

    if not chunks:
        raise ValueError("Chunking produced zero chunks — repository may be empty.")

    # ---------------------------------------------------------------- #
    # Step 6 — Embeddings (via embedding_pipeline)
    # ---------------------------------------------------------------- #
    from app.ml.embedding_pipeline import generate_embeddings
    from app.ml.embedder import get_embedder

    vectors, embed_stats = generate_embeddings(chunks)
    embedder = get_embedder()
    logger.info(
        "[{id}] Embeddings shape: {s}  ({model})",
        id=repo_id,
        s=vectors.shape,
        model=embedder.model_name,
    )

    # ---------------------------------------------------------------- #
    # Step 7 — FAISS index
    # ---------------------------------------------------------------- #
    from app.vector_store.faiss_store import FAISSStore

    index_path = settings.VECTOR_STORE_DIR / repo_id
    store = FAISSStore(repo_id=repo_id, index_path=str(index_path))
    store.build(vectors, model_name=embedder.model_name)
    store.save()
    logger.info("[{id}] FAISS index saved → {path}", id=repo_id, path=str(index_path))

    # ---------------------------------------------------------------- #
    # Step 8 — Metadata sidecar (MetadataStore)
    # ---------------------------------------------------------------- #
    from app.vector_store.metadata_store import MetadataStore

    meta_store = MetadataStore(repo_id=repo_id, index_path=str(index_path))
    meta_store.build_from_chunks(chunks)   # chunk_ids patched after insert

    # ---------------------------------------------------------------- #
    # Step 9 — Persist chunks to MongoDB
    # ---------------------------------------------------------------- #
    chunk_docs = [
        ChunkDocument(
            repo_id=repo_id,
            file_path=c["file_path"],
            language=c.get("language"),
            start_line=c["start_line"],
            end_line=c["end_line"],
            content=c["content"],
            chunk_index=c["chunk_index"],
            token_count=c.get("token_count", 0),
            faiss_id=idx,
            # v2 enriched fields
            chunk_type=c.get("chunk_type", "window"),
            symbol_name=c.get("symbol_name"),
            symbol_metadata=c.get("metadata", {}),
        )
        for idx, c in enumerate(chunks)
    ]
    await ChunkDocument.insert_many(chunk_docs)
    logger.info("[{id}] {n} ChunkDocuments persisted.", id=repo_id, n=len(chunk_docs))

    # Back-fill MongoDB chunk IDs into MetadataStore sidecar
    chunk_ids = [str(doc.id) for doc in chunk_docs]
    meta_store.patch_chunk_ids(chunk_ids)
    meta_store.save()
    logger.info("[{id}] MetadataStore sidecar saved.", id=repo_id)

    # ---------------------------------------------------------------- #
    # Step 10 — Update RepositoryDocument stats
    # ---------------------------------------------------------------- #
    repo.total_files = repo_metadata["total_files"]
    repo.total_chunks = len(chunks)
    repo.total_tokens = sum(c.get("token_count", 0) for c in chunks)
    repo.language_breakdown = repo_metadata["language_breakdown"]
    repo.faiss_index_path = str(index_path)
    repo.updated_at = datetime.utcnow()
    repo.repo_metadata = {
        "total_lines": repo_metadata["total_lines"],
        "total_functions": repo_metadata["total_functions"],
        "total_classes": repo_metadata["total_classes"],
        "total_imports": repo_metadata["total_imports"],
        "files": repo_metadata["files"],
        "embedding_model": embedder.model_name,
        "embedding_dim": embedder.dim,
    }
    await repo.save()

    logger.info(
        "[{id}] Pipeline complete — {files} files, {chunks} chunks, {tokens} tokens.",
        id=repo_id,
        files=repo.total_files,
        chunks=repo.total_chunks,
        tokens=repo.total_tokens,
    )


# ---------------------------------------------------------------------------
# Source acquisition helper
# ---------------------------------------------------------------------------

async def _acquire_source(repo: RepositoryDocument, settings) -> Path:
    if repo.source == RepoSource.GITHUB:
        from app.ml.github_loader import clone_repo
        return await clone_repo(repo.github_url, settings.UPLOAD_DIR / str(repo.id))
    else:
        from app.ml.zip_loader import extract_zip
        return await extract_zip(repo.zip_filename, settings.UPLOAD_DIR / str(repo.id))
