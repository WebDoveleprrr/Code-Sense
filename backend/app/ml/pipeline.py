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


# ─────────────────────────────────────────────
# LINES 33-56
# PURPOSE:
# Ranks source files to prioritize indexing important files first.
#
# WHY IT EXISTS:
# For repositories that exceed the maximum file limit (e.g., 1000 files),
# we must ensure that core architectural files (main.py, index.js, /src/)
# are indexed before tests, docs, or generic utility scripts.
#
# INPUT:
# List of parsed file dictionaries containing file paths and sizes.
#
# OUTPUT:
# Sorted list of file dictionaries based on priority score.
#
# USED BY:
# run_ingestion_pipeline (Step 2)
#
# DEPENDS ON:
# Basic Python string matching.
#
# INTERVIEW NOTE:
# "To handle massive monorepos within memory limits, I implemented a heuristic 
# ranking system. It assigns scores based on file names and directory depth,
# ensuring the LLM context is populated with 'entry point' logic first before
# saturating the database with tests or markdown files."
# ─────────────────────────────────────────────

def rank_files(files_list: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    # FUNCTION PURPOSE:
    # Calculates a priority score for a file path to determine its indexing priority.
    #
    # WHEN IT RUNS:
    # During Step 2 of the ingestion pipeline if total files > MAX_INDEXED_FILES.
    #
    # PARAMETERS:
    # files_list: Unsorted list of file metadata dicts.
    #
    # RETURNS:
    # A new list of file metadata dicts sorted by priority.
    #
    # SIDE EFFECTS:
    # None. Pure function.
    
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

# ─────────────────────────────────────────────
# LINES 60-312
# PURPOSE:
# The core background worker that orchestrates the entire AI ingestion process.
#
# WHY IT EXISTS:
# CodeSense needs to convert raw git repositories into semantic vectors.
# This function strings together downloading, parsing, chunking, embedding,
# and database storage into a single robust, asynchronous flow.
#
# ARCHITECTURE NOTE:
# This is the "brain" of the backend ingestion layer. It bridges the pure ML
# modules (`chunker.py`, `embedder.py`) with the Storage layer (`faiss_store.py`, Mongo).
#
# INPUT:
# RepositoryDocument representing the target repository.
#
# OUTPUT:
# None (updates the database asynchronously).
#
# USED BY:
# backend/app/services/repository_service.py (Triggered via API upload).
#
# DEPENDS ON:
# `ml/github_loader.py`, `ml/repo_parser.py`, `ml/parsers.py`, 
# `ml/chunker.py`, `ml/embedding_pipeline.py`, `FAISSStore`.
#
# SCALABILITY NOTE:
# CPU-bound tasks (AST parsing, chunking) use `asyncio.to_thread` to prevent
# blocking the FastAPI event loop. However, running this entirely in-memory
# means multiple concurrent uploads could starve the container. Future 
# iterations should move this to a Celery/Redis worker queue.
#
# DEBUGGING NOTE:
# If ingestion hangs, check the `log_mem` outputs. FAISS and SentenceTransformers
# can cause silent OOM (Out of Memory) kills in Docker/Render environments.
# ─────────────────────────────────────────────

async def run_ingestion_pipeline(repo: RepositoryDocument) -> None:
    """
    Full ingestion pipeline executed as a background task.
    """
    # FLOW:
    # User Uploads Repo
    #   ↓
    # FastAPI BackgroundTask initiates run_ingestion_pipeline()
    #   ↓
    # 1. Clone Source Code
    #   ↓
    # 2. Extract Files & Filter
    #   ↓
    # 3. Tree-sitter AST Parsing (Extracts functions/classes)
    #   ↓
    # 4. Chunk Generation (Semantic overlapping chunks)
    #   ↓
    # 5. Embeddings Generation (SentenceTransformers)
    #   ↓
    # 6. FAISS Vector Indexing & Local Disk Save
    #   ↓
    # 7. MongoDB Persistence (Batched)
    #   ↓
    # 8. Mark Repo as DONE

    import gc
    from app.models.repository import RepoStatus

    def log_mem(phase: str):
        # FUNCTION PURPOSE:
        # Logs the Resident Set Size (RSS) memory of the current process.
        # WHY IT EXISTS:
        # Critical for tracing memory leaks or identifying exactly which
        # pipeline step causes an OOM termination in production.
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

    # INTERVIEW QUESTION:
    # "What happens if a user uploads a repo with 50,000 files?"
    #
    # GOOD ANSWER:
    # "We enforce a hard cap of 1,000 files. Instead of rejecting the upload, 
    # we use a heuristic ranking algorithm that prioritizes core source code, 
    # routes, and entry points, skipping non-essential files like tests or logs.
    # We record `indexing_mode='prioritized'` so the UI can warn the user."
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
            # This is crucial so we don't block the FastAPI event loop
            # and freeze all other user requests while parsing syntax trees.
            ast_result = await asyncio.to_thread(parse_source, file_dict)
        except Exception as exc:
            logger.warning(
                "[{id}] AST parse failed for {fp}: {err}",
                id=repo_id,
                fp=file_dict["file_path"],
                err=str(exc),
            )
            # Graceful degradation: if Tree-sitter fails, fallback to raw text
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

    # Clean up AST parse memory
    del parsed_meta
    gc.collect()

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

    # Clean up file structures, we only need chunks now
    num_parsed_files = len(parsed_files)
    del parsed_files
    del file_metadata_list
    gc.collect()

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
    # FlatIP calculates Inner Product, which equals Cosine Similarity
    # if the vectors are L2-normalized (which they are).
    store.initialize(embedder.dim, expected_count=len(chunks), model_name=embedder.model_name)

    # We iterate over the generator stream and index directly into FAISS.
    # Using a generator prevents holding all heavy float32 tensors in RAM simultaneously.
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

    # The metadata store is a lightweight JSON sidecar. It holds chunk boundaries
    # so we can map FAISS integer IDs directly back to file logic without hitting MongoDB.
    meta_store = MetadataStore(repo_id=repo_id, index_path=str(index_path))
    meta_store.build_from_chunks(chunks)   # chunk_ids patched after insert

    # ---------------------------------------------------------------- #
    # Step 9 — Persist chunks to MongoDB
    # ---------------------------------------------------------------- #
    logger.info("[{id}] MONGODB UPDATE START", id=repo_id)
    
    # INTERVIEW NOTE:
    # "During load testing on Render's 512MB RAM tier, storing 5000 ChunkDocument
    # Pydantic models in memory simultaneously caused OOM crashes. I implemented 
    # batch persistence (BATCH_SIZE = 500) combined with explicit `gc.collect()` 
    # to flatline the memory profile during this database phase."
    BATCH_SIZE = 500
    chunk_ids = []
    
    for i in range(0, len(chunks), BATCH_SIZE):
        batch_chunks = chunks[i : i + BATCH_SIZE]
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
                faiss_id=idx + i,
                # v2 enriched fields
                chunk_type=c.get("chunk_type", "window"),
                symbol_name=c.get("symbol_name"),
                symbol_metadata=c.get("metadata", {}),
            )
            for idx, c in enumerate(batch_chunks)
        ]
        
        # Insert batch
        await ChunkDocument.insert_many(chunk_docs)
        chunk_ids.extend([str(doc.id) for doc in chunk_docs])
        
        logger.info("[{id}] Inserted {n} ChunkDocuments (batch {batch}).", id=repo_id, n=len(chunk_docs), batch=i // BATCH_SIZE + 1)
        
        # Free memory explicitly
        del batch_chunks
        del chunk_docs
        import gc
        gc.collect()

    logger.info("[{id}] Total {n} ChunkDocuments persisted.", id=repo_id, n=len(chunk_ids))

    # Back-fill MongoDB chunk IDs into MetadataStore sidecar
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
    
    # Clean up chunks
    del chunks
    gc.collect()
    
    # Store extended metadata
    repo.indexed_files = num_parsed_files
    repo.skipped_files = skipped_files
    repo.indexing_mode = indexing_mode
    
    repo.repo_metadata = {
        "total_lines": repo_metadata["total_lines"],
        "total_functions": repo_metadata["total_functions"],
        "total_classes": repo_metadata["total_classes"],
        "total_imports": repo_metadata["total_imports"],
        "files": repo_metadata["files"],
        "embedding_model": embedder.model_name,
        "indexed_files": num_parsed_files,
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


# ─────────────────────────────────────────────
# LINES 315-322
# PURPOSE:
# Abstraction for retrieving the raw source code from either GitHub or a Zip upload.
#
# WHY IT EXISTS:
# Centralizes the downloading/extraction logic so the rest of the pipeline
# treats local directories interchangeably regardless of origin.
# ─────────────────────────────────────────────

async def _acquire_source(repo: RepositoryDocument, settings) -> Path:
    # FUNCTION PURPOSE:
    # Routes the download request to the correct loader.
    if repo.source == RepoSource.GITHUB:
        from app.ml.github_loader import clone_repo
        return await clone_repo(repo.github_url, settings.UPLOAD_DIR / str(repo.id))
    else:
        from app.ml.zip_loader import extract_zip
        return await extract_zip(repo.zip_filename, settings.UPLOAD_DIR / str(repo.id))
