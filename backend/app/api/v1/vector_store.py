# backend/app/api/v1/vector_store.py
"""
CodeSense — Vector Store Management API

Endpoints:
  GET    /api/v1/vector-store/{repo_id}/health   — index health & stats
  POST   /api/v1/vector-store/{repo_id}/rebuild  — re-embed & rebuild index
  DELETE /api/v1/vector-store/{repo_id}          — delete index from disk
  GET    /api/v1/vector-store/{repo_id}/metadata — list chunk metadata records
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, status
from pydantic import BaseModel

from app.core.exceptions import NotFoundError
from app.models.repository import RepositoryDocument, RepoStatus
from app.vector_store.faiss_store import FAISSStore
from app.vector_store.metadata_store import MetadataStore

router = APIRouter()


# ---------------------------------------------------------------------------
# Schemas
# ---------------------------------------------------------------------------

class IndexHealthResponse(BaseModel):
    repo_id: str
    loaded: bool
    on_disk: bool
    total: Optional[int]
    dim: Optional[int]
    index_type: Optional[str]
    model_name: Optional[str]
    created_at: Optional[str]


class RebuildResponse(BaseModel):
    success: bool
    message: str
    repo_id: str


class MetadataListResponse(BaseModel):
    repo_id: str
    count: int
    records: List[Dict[str, Any]]


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------

@router.get(
    "/{repo_id}/health",
    response_model=IndexHealthResponse,
    summary="Vector store health check",
    description="Returns FAISS index stats for the given repository.",
)
async def index_health(repo_id: str) -> IndexHealthResponse:
    repo = await _require_repo(repo_id)
    store = FAISSStore(repo_id=repo_id, index_path=repo.faiss_index_path)
    return IndexHealthResponse(**store.health())


@router.post(
    "/{repo_id}/rebuild",
    response_model=RebuildResponse,
    status_code=status.HTTP_202_ACCEPTED,
    summary="Rebuild FAISS index for a repository",
    description=(
        "Triggers a full re-embedding and FAISS index rebuild in the background. "
        "The repository must already be in READY or FAILED state."
    ),
)
async def rebuild_index(
    repo_id: str,
    background_tasks: BackgroundTasks,
) -> RebuildResponse:
    repo = await _require_repo(repo_id)
    if repo.status == RepoStatus.PROCESSING:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Repository is currently being processed. Wait for it to finish.",
        )

    background_tasks.add_task(_rebuild_task, repo_id)

    return RebuildResponse(
        success=True,
        message="FAISS index rebuild started in the background.",
        repo_id=repo_id,
    )


@router.delete(
    "/{repo_id}",
    summary="Delete FAISS index for a repository",
    description="Removes the index files from disk. The repo record remains in MongoDB.",
)
async def delete_index(repo_id: str) -> Dict[str, Any]:
    repo = await _require_repo(repo_id)
    store = FAISSStore(repo_id=repo_id, index_path=repo.faiss_index_path)
    store.delete()

    meta_store = MetadataStore(repo_id=repo_id, index_path=repo.faiss_index_path)
    if meta_store.exists():
        from pathlib import Path
        meta_path = Path(repo.faiss_index_path or f"./vector_store/indices/{repo_id}") / "chunk_meta.json"
        meta_path.unlink(missing_ok=True)

    return {"success": True, "message": f"FAISS index for repo '{repo_id}' deleted.", "repo_id": repo_id}


@router.get(
    "/{repo_id}/metadata",
    response_model=MetadataListResponse,
    summary="List chunk metadata records",
    description=(
        "Returns all chunk metadata entries stored in the JSON sidecar alongside "
        "the FAISS index. Useful for debugging retrieval behaviour."
    ),
)
async def list_metadata(
    repo_id: str,
    limit: int = 100,
    offset: int = 0,
) -> MetadataListResponse:
    repo = await _require_repo(repo_id)
    meta_store = MetadataStore(repo_id=repo_id, index_path=repo.faiss_index_path)

    if not meta_store.exists():
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"No metadata sidecar found for repo '{repo_id}'.",
        )

    all_records = meta_store.all_records()
    page = all_records[offset: offset + limit]

    return MetadataListResponse(
        repo_id=repo_id,
        count=len(all_records),
        records=page,
    )


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

async def _require_repo(repo_id: str) -> RepositoryDocument:
    repo = await RepositoryDocument.get(repo_id)
    if repo is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Repository '{repo_id}' not found.",
        )
    return repo


async def _rebuild_task(repo_id: str) -> None:
    """Background task: re-run the embedding + FAISS build steps only."""
    from app_logger import logger
    from datetime import datetime
    from app.models.chunk import ChunkDocument

    try:
        repo = await RepositoryDocument.get(repo_id)
        if repo is None:
            logger.error("Rebuild: repo {id} not found.", id=repo_id)
            return

        # Load all chunks from MongoDB
        chunks_cursor = ChunkDocument.find(ChunkDocument.repo_id == repo_id)
        chunk_docs = await chunks_cursor.to_list()

        if not chunk_docs:
            logger.warning("Rebuild: no chunks found for repo {id}.", id=repo_id)
            return

        chunks = [
            {
                "content": c.content,
                "language": c.language,
                "chunk_type": c.chunk_type,
                "symbol_name": c.symbol_name,
                "file_path": c.file_path,
                "start_line": c.start_line,
                "end_line": c.end_line,
                "chunk_index": c.chunk_index,
                "token_count": c.token_count,
            }
            for c in chunk_docs
        ]

        from app.ml.embedding_pipeline import generate_embeddings
        from app.core.config import get_settings

        vectors, stats = generate_embeddings(chunks)
        settings = get_settings()

        store = FAISSStore(
            repo_id=repo_id,
            index_path=str(settings.VECTOR_STORE_DIR / repo_id),
        )
        store.build(vectors, model_name=stats.get("model", ""))
        store.save()

        # Rebuild metadata sidecar
        meta_store = MetadataStore(
            repo_id=repo_id,
            index_path=str(settings.VECTOR_STORE_DIR / repo_id),
        )
        chunk_ids = [str(c.id) for c in chunk_docs]
        meta_store.build_from_chunks(chunks, chunk_ids=chunk_ids)
        meta_store.save()

        # Update FAISS IDs in MongoDB
        for idx, c in enumerate(chunk_docs):
            c.faiss_id = idx
            await c.save()

        repo.faiss_index_path = str(settings.VECTOR_STORE_DIR / repo_id)
        repo.status = RepoStatus.READY
        repo.updated_at = datetime.utcnow()
        await repo.save()

        logger.info(
            "Rebuild complete for repo {id}: {n} vectors.", id=repo_id, n=len(chunks)
        )

    except Exception as exc:
        logger.exception("Rebuild failed for repo {id}: {err}", id=repo_id, err=str(exc))
