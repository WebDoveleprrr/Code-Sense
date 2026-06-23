# backend/app/ml/pipeline.py
"""
CodeSense — End-to-End Ingestion Pipeline (v3)

Orchestrates: clone/extract → parse → AST parse → metadata → chunk
              → embed → FAISS index → metadata sidecar → MongoDB persist → repo stats

New in v3 (Streaming Architecture)
----------------------------------
* Completely lazy evaluation: files are read, parsed, chunked, and embedded one by one.
* Bounded memory footprint regardless of repository size.
* Incremental batching into FAISS and MongoDB.
"""

from __future__ import annotations

import asyncio
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List

from app_logger import logger

from app.core.config import get_settings
from app.models.chunk import ChunkDocument
from app.models.repository import RepositoryDocument, RepoSource, RepoStatus


def rank_files(files_list: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    def get_score(path_str: str) -> int:
        path_lower = path_str.lower()
        if any(path_lower.endswith(name) for name in ["main.py", "app.py", "server.py", "index.js", "index.ts"]):
            return 100
        if any(f"/{d}/" in f"/{path_lower}" or path_lower.startswith(f"{d}/") for d in ["src", "api", "routes", "controllers", "services", "models", "schemas"]):
            return 80
        if any(f"/{d}/" in f"/{path_lower}" or path_lower.startswith(f"{d}/") for d in ["config", "utils", "helpers"]):
            return 50
        if any(f"/{d}/" in f"/{path_lower}" or path_lower.startswith(f"{d}/") for d in ["tests", "docs", "examples"]):
            return 10
        return 30

    return sorted(files_list, key=lambda f: (
        -get_score(f["file_path"]),
        f["file_path"].count("/"),
        0 if f.get("language") else 1,
        f.get("size_bytes", 0)
    ))


async def run_ingestion_pipeline(repo: RepositoryDocument) -> None:
    """
    Full ingestion pipeline executed as a streaming background task.
    """
    import gc
    import traceback
    import sys
    import os
    import psutil
    
    settings = get_settings()
    repo_id = str(repo.id)

    def log_mem(phase: str):
        try:
            process = psutil.Process(os.getpid())
            mem_mb = process.memory_info().rss / (1024 * 1024)
            logger.info("[Memory Check] [{id}] Phase={phase} | RSS={mem:.2f}MB", id=repo_id, phase=phase, mem=mem_mb)
            sys.stdout.flush()
            sys.stderr.flush()
        except Exception:
            pass

    try:
        log_mem("Startup")
        repo_dir = await _acquire_source(repo, settings)
        logger.info("[{id}] Source at {dir}", id=repo_id, dir=str(repo_dir))

        repo.status = RepoStatus.PARSING
        await repo.save()

        from app.ml.repo_parser import parse_repository, read_and_decode_file
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

        repo.status = RepoStatus.CHUNKING
        await repo.save()

        # Prepare Stores
        from app.ml.embedder import get_embedder
        from app.vector_store.faiss_store import FAISSStore
        from app.vector_store.metadata_store import MetadataStore
        
        log_mem("Before get_embedder()")
        embedder = get_embedder()
        log_mem("After get_embedder()")
        
        index_path = settings.VECTOR_STORE_DIR / repo_id
        store = FAISSStore(repo_id=repo_id, index_path=str(index_path))
        # Give an arbitrary expected count; it can grow dynamically
        store.initialize(embedder.dim, expected_count=len(parsed_files)*10, model_name=embedder.model_name)
        meta_store = MetadataStore(repo_id=repo_id, index_path=str(index_path))

        chunks_buffer: List[Dict[str, Any]] = []
        BATCH_SIZE = 50
        
        # Aggregated stats
        total_lines = 0
        total_functions = 0
        total_classes = 0
        total_imports = 0
        language_breakdown: Dict[str, int] = {}
        files_metadata_summary = []
        
        faiss_idx_offset = 0
        total_chunks_processed = 0
        total_tokens = 0

        from app.ml.parsers import parse_source
        from app.ml.metadata_generator import build_file_metadata, _file_summary
        from app.ml.chunker import chunk_files
        from app.ml.embedding_pipeline import prepare_texts

        async def process_batch():
            nonlocal chunks_buffer, faiss_idx_offset, total_chunks_processed, total_tokens
            if not chunks_buffer:
                return
            
            log_mem("Before embedding")
            batch_texts = prepare_texts(chunks_buffer)
            # we run it in a thread so it doesn't block the event loop
            batch_vectors = await asyncio.to_thread(embedder.embed_batch, batch_texts, True, False)
            log_mem("After embedding")
            
            log_mem("Before FAISS insertion")
            store.add_vectors(batch_vectors)
            log_mem("After FAISS insertion")
            
            log_mem("Before Mongo insertion")
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
                    faiss_id=faiss_idx_offset + idx,
                    chunk_type=c.get("chunk_type", "window"),
                    symbol_name=c.get("symbol_name"),
                    symbol_metadata=c.get("metadata", {}),
                )
                for idx, c in enumerate(chunks_buffer)
            ]
            await ChunkDocument.insert_many(chunk_docs)
            chunk_ids = [str(doc.id) for doc in chunk_docs]
            log_mem("After Mongo insertion")
            
            # Since we append incrementally, we must load the existing records
            if meta_store.exists() and meta_store.count == 0:
                meta_store.load()
                
            for faiss_id_local, chunk in enumerate(chunks_buffer):
                record = {
                    "faiss_id": faiss_idx_offset + faiss_id_local,
                    "chunk_id": chunk_ids[faiss_id_local],
                    "file_path": chunk.get("file_path", ""),
                    "language": chunk.get("language", "unknown"),
                    "start_line": chunk.get("start_line", 0),
                    "end_line": chunk.get("end_line", 0),
                    "chunk_type": chunk.get("chunk_type", "window"),
                    "symbol_name": chunk.get("symbol_name"),
                    "chunk_index": chunk.get("chunk_index", faiss_idx_offset + faiss_id_local),
                    "token_count": chunk.get("token_count", 0),
                }
                meta_store._records.append(record)
            
            faiss_idx_offset += len(chunks_buffer)
            total_chunks_processed += len(chunks_buffer)
            total_tokens += sum(c.get("token_count", 0) for c in chunks_buffer)
            
            chunks_buffer.clear()
            del batch_texts
            del batch_vectors
            del chunk_docs
            gc.collect()
            log_mem("After gc.collect()")

        for file_meta in parsed_files:
            log_mem(f"Before file processing: {file_meta['file_path']}")
            path = repo_dir / file_meta["file_path"]
            content = await asyncio.to_thread(read_and_decode_file, path)
            if not content:
                continue
                
            file_meta["content"] = content
            file_meta["line_count"] = content.count("\n") + 1
            
            try:
                ast_result = await asyncio.to_thread(parse_source, file_meta)
            except Exception as exc:
                logger.warning("[{id}] AST parse failed for {fp}: {err}", id=repo_id, fp=file_meta["file_path"], err=str(exc))
                ast_result = {"language": file_meta["language"], "file_path": file_meta["file_path"]}

            enriched_meta = build_file_metadata(file_meta, ast_result)
            
            log_mem("Before chunking")
            file_chunks = await asyncio.to_thread(
                chunk_files,
                parsed_files=[file_meta],
                chunk_size=settings.CHUNK_SIZE,
                overlap=settings.CHUNK_OVERLAP,
                parsed_meta=[enriched_meta]
            )
            log_mem("After chunking")
            
            if file_chunks:
                chunks_buffer.extend(file_chunks)
                
            # Aggregate stats incrementally
            lang = enriched_meta.get("language") or "unknown"
            language_breakdown[lang] = language_breakdown.get(lang, 0) + 1
            total_lines += enriched_meta.get("line_count", 0)
            total_functions += enriched_meta.get("function_count", 0)
            total_classes += enriched_meta.get("class_count", 0)
            total_imports += enriched_meta.get("import_count", 0)
            files_metadata_summary.append(_file_summary(enriched_meta))
            
            del file_meta["content"]
            del content
            del ast_result
            del enriched_meta
            log_mem(f"After file processing: {file_meta['file_path']}")
            
            if len(chunks_buffer) >= BATCH_SIZE:
                await process_batch()
                
        # Process remaining chunks
        if chunks_buffer:
            await process_batch()

        await asyncio.to_thread(store.save)
        await asyncio.to_thread(meta_store.save)
        
        # Step 10 — Update RepositoryDocument stats
        repo.total_files = total_files
        repo.total_chunks = total_chunks_processed
        repo.total_tokens = total_tokens
        repo.language_breakdown = language_breakdown
        repo.faiss_index_path = str(index_path)
        repo.updated_at = datetime.utcnow()
        repo.indexed_files = len(files_metadata_summary)
        repo.skipped_files = skipped_files
        repo.indexing_mode = indexing_mode
        repo.repo_metadata = {
            "total_lines": total_lines,
            "total_functions": total_functions,
            "total_classes": total_classes,
            "total_imports": total_imports,
            "files": files_metadata_summary,
            "embedding_model": embedder.model_name,
            "indexed_files": len(files_metadata_summary),
            "skipped_files": skipped_files,
            "indexing_mode": indexing_mode,
            "embedding_dim": embedder.dim,
        }
        repo.status = RepoStatus.READY
        await repo.save()
        logger.info("[{id}] STATUS READY. Pipeline complete.", id=repo_id)
        
    except Exception as exc:
        err_msg = str(exc)
        logger.error("[{id}] Pipeline crashed: {err}\n{tb}", id=repo_id, err=err_msg, tb=traceback.format_exc())
        repo.status = RepoStatus.FAILED
        repo.error_message = err_msg
        repo.updated_at = datetime.utcnow()
        await repo.save()
    finally:
        if 'repo_dir' in locals() and repo_dir.exists():
            import shutil
            shutil.rmtree(repo_dir, ignore_errors=True)
            logger.info("[{id}] Source directory {dir} successfully cleaned up.", id=repo_id, dir=str(repo_dir))


async def _acquire_source(repo: RepositoryDocument, settings) -> Path:
    if repo.source == RepoSource.GITHUB:
        from app.ml.github_loader import clone_repo
        return await clone_repo(repo.github_url, settings.UPLOAD_DIR / str(repo.id))
    else:
        from app.ml.zip_loader import extract_zip
        return await extract_zip(repo.zip_filename, settings.UPLOAD_DIR / str(repo.id))
