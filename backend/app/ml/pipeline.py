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

def rank_files(files_list: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    def get_score(path_str: str) -> int:
        path_lower = path_str.lower()
        # High priority
        if any(path_lower.endswith(name) for name in ["main.py", "app.py", "server.py", "index.js", "index.ts"]):
            return 100
        if any(f"/{d}/" in f"/{path_lower}" or path_lower.startswith(f"{d}/") for d in ["src", "api", "routes", "controllers", "services", "models", "schemas"]):
            return 80
        # Medium priority
        if any(f"/{d}/" in f"/{path_lower}" or path_lower.startswith(f"{d}/") for d in ["config", "utils", "helpers"]):
            return 50
        # Low priority
        if any(f"/{d}/" in f"/{path_lower}" or path_lower.startswith(f"{d}/") for d in ["tests", "docs", "examples"]):
            return 10
        return 30 # Default

    # Tie breaking: score descending, depth ascending, is_source descending, size ascending
    return sorted(files_list, key=lambda f: (
        -get_score(f["file_path"]),
        f["file_path"].count("/"),
        0 if f["language"] else 1,
        f.get("size_bytes", 0)
    ))

async def run_ingestion_pipeline(repo: RepositoryDocument) -> None:
    """
    Full ingestion pipeline executed as a background task.
    """
    import gc
    from app.models.repository import RepoStatus

    def log_mem(phase: str):
        try:
            import os
            import psutil
            process = psutil.Process(os.getpid())
            mem_mb = process.memory_info().rss / (1024 * 1024)
            logger.info("[Memory Check] [{id}] Phase: {phase} | Memory Usage: {mem:.2f} MB", id=repo_id, phase=phase, mem=mem_mb)
        except ImportError:
            pass

    settings = get_settings()
    repo_id = str(repo.id)

    # ---------------------------------------------------------------- #
    # Step 1 — Acquire source
    # ---------------------------------------------------------------- #
    log_mem("Acquiring source")
    repo_dir = await _acquire_source(repo, settings)
    logger.info("[{id}] Source at {dir}", id=repo_id, dir=str(repo_dir))

    # ---------------------------------------------------------------- #
    # Step 2 — Repository file traversal
    # ---------------------------------------------------------------- #
    repo.status = RepoStatus.PARSING
    await repo.save()
    log_mem("File traversal")

    from app.ml.repo_parser import parse_repository
    parsed_files = await parse_repository(repo_dir)
    logger.info("[{id}] {n} files collected.", id=repo_id, n=len(parsed_files))

    total_files = len(parsed_files)
    skipped_files = 0
    indexing_mode = "standard"
    MAX_INDEXED_FILES = 1000

    if total_files > MAX_INDEXED_FILES:
        logger.info("[{id}] Repository exceeds {max} files (found {total}). Applying priority selection.", id=repo_id, max=MAX_INDEXED_FILES, total=total_files)
        ranked_files = rank_files(parsed_files)
        parsed_files = ranked_files[:MAX_INDEXED_FILES]
        skipped_files = total_files - MAX_INDEXED_FILES
        indexing_mode = "prioritized"

    # ---------------------------------------------------------------- #
    # Step 3 — AST parsing (language-specific)
    # ---------------------------------------------------------------- #
    from app.ml.parsers import parse_source

    parsed_meta: List[Dict[str, Any]] = []
    for file_dict in parsed_files:
        try:
            # Delegate CPU-bound AST parsing to thread pool
            ast_result = await asyncio.to_thread(parse_source, file_dict)
        except Exception as exc:
            logger.warning(
                "[{id}] AST parse failed for {fp}: {err}",
                id=repo_id,
                fp=file_dict["file_path"],
                err=str(exc),
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
    repo.status = RepoStatus.CHUNKING
    await repo.save()
    log_mem("Chunking")

    from app.ml.chunker import chunk_files
    # Delegate CPU-bound chunking to thread pool
    chunks = await asyncio.to_thread(
        chunk_files,
        parsed_files=parsed_files,
        chunk_size=settings.CHUNK_SIZE,
        overlap=settings.CHUNK_OVERLAP,
        parsed_meta=file_metadata_list,
    )
    logger.info("[{id}] {n} chunks produced.", id=repo_id, n=len(chunks))

    if not chunks:
        raise ValueError("Chunking produced zero chunks — repository may be empty.")

    if len(chunks) > 5000:
        raise ValueError(
            f"Repository exceeds the maximum limit of 5000 chunks (found {len(chunks)}). "
            "Please upload a smaller repository for the Render free-tier environment."
        )

    # ---------------------------------------------------------------- #
    # Step 6 — Embeddings & Step 7 — FAISS index stream
    # ---------------------------------------------------------------- #
    repo.status = RepoStatus.EMBEDDING
    await repo.save()
    log_mem("Embedding generation & Indexing")
    logger.info("[{id}] START EMBEDDING STREAM", id=repo_id)

    from app.ml.embedding_pipeline import generate_embeddings_stream
    from app.ml.embedder import get_embedder
    from app.vector_store.faiss_store import FAISSStore

    embedder = get_embedder()
    index_path = settings.VECTOR_STORE_DIR / repo_id
    store = FAISSStore(repo_id=repo_id, index_path=str(index_path))
    
    # Initialize FAISS with FlatIP for progressive insertion
    store.initialize(embedder.dim, expected_count=len(chunks), model_name=embedder.model_name)

    # We must consume the generator in a thread if it blocks, but the generator is synchronous.
    # To keep the event loop unblocked, we iterate over it using asyncio.to_thread per batch
    # Or simply run the whole loop in a thread. Since we want to update memory in chunks, 
    # we can run a wrapper function in a thread.
    
    def stream_to_faiss():
        for batch_vectors, indices in generate_embeddings_stream(chunks):
            store.add_vectors(batch_vectors)
            
    await asyncio.to_thread(stream_to_faiss)
    
    logger.info("[{id}] EMBEDDINGS GENERATED AND INDEXED", id=repo_id)
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
    logger.info("[{id}] MONGODB UPDATE START", id=repo_id)
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
    repo.total_files = total_files
    repo.total_chunks = len(chunks)
    repo.total_tokens = sum(c.get("token_count", 0) for c in chunks)
    repo.language_breakdown = repo_metadata["language_breakdown"]
    repo.faiss_index_path = str(index_path)
    repo.updated_at = datetime.utcnow()
    
    # Store extended metadata
    repo.indexed_files = len(parsed_files)
    repo.skipped_files = skipped_files
    repo.indexing_mode = indexing_mode
    
    repo.repo_metadata = {
        "total_lines": repo_metadata["total_lines"],
        "total_functions": repo_metadata["total_functions"],
        "total_classes": repo_metadata["total_classes"],
        "total_imports": repo_metadata["total_imports"],
        "files": repo_metadata["files"],
        "embedding_model": embedder.model_name,
        "indexed_files": len(parsed_files),
        "skipped_files": skipped_files,
        "indexing_mode": indexing_mode,
        "embedding_dim": embedder.dim,
    }
    await repo.save()
    logger.info("[{id}] STATUS READY", id=repo_id)

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
