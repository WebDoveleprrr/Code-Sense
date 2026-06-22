# backend/app/api/v1/repositories.py
"""
CodeSense — Repository Management Endpoints (v2)
  POST   /repositories/github          — ingest from GitHub URL
  POST   /repositories/upload          — ingest from ZIP file
  GET    /repositories                  — list all repositories
  GET    /repositories/{repo_id}        — get repository details (with parse stats)
  GET    /repositories/{repo_id}/files  — list parsed files with symbol counts
  GET    /repositories/{repo_id}/chunks — list chunk documents
  DELETE /repositories/{repo_id}        — delete repository and all data
"""

from __future__ import annotations

from typing import List, Optional

from fastapi import APIRouter, BackgroundTasks, Depends, File, Query, UploadFile, status

from app.core.exceptions import NotFoundError, UploadError
from app.models.chunk import ChunkDocument
from app.models.repository import RepositoryDocument, RepoStatus
from app.schemas.ingestion import (
    ChunkResponse,
    GitHubIngestRequest,
    IngestStartedResponse,
    RepoDetailResponse,
    RepoMetadataSchema,
    RepoSummaryResponse,
)
from app.services.ingestion_service import IngestionService
from app.core.auth import get_current_user
from app.models.user import UserDocument

router = APIRouter()


# ------------------------------------------------------------------ #
# Conversion helpers
# ------------------------------------------------------------------ #

def _doc_to_summary(doc: RepositoryDocument) -> RepoSummaryResponse:
    return RepoSummaryResponse(
        id=str(doc.id),
        name=doc.name,
        owner=doc.owner,
        source=doc.source.value,
        status=doc.status.value,
        total_files=doc.total_files,
        indexed_files=doc.indexed_files,
        skipped_files=doc.skipped_files,
        indexing_mode=doc.indexing_mode,
        total_chunks=doc.total_chunks,
        created_at=doc.created_at.isoformat(),
    )


def _doc_to_detail(doc: RepositoryDocument) -> RepoDetailResponse:
    raw_meta = doc.repo_metadata or {}
    return RepoDetailResponse(
        id=str(doc.id),
        name=doc.name,
        owner=doc.owner,
        source=doc.source.value,
        status=doc.status.value,
        total_files=doc.total_files,
        indexed_files=doc.indexed_files,
        skipped_files=doc.skipped_files,
        indexing_mode=doc.indexing_mode,
        total_chunks=doc.total_chunks,
        total_tokens=doc.total_tokens,
        language_breakdown=doc.language_breakdown,
        faiss_index_path=doc.faiss_index_path,
        github_url=doc.github_url,
        zip_filename=doc.zip_filename,
        error_message=doc.error_message,
        created_at=doc.created_at.isoformat(),
        indexed_at=doc.indexed_at.isoformat() if doc.indexed_at else None,
        repo_metadata=RepoMetadataSchema(
            total_lines=raw_meta.get("total_lines", 0),
            total_functions=raw_meta.get("total_functions", 0),
            total_classes=raw_meta.get("total_classes", 0),
            total_imports=raw_meta.get("total_imports", 0),
            files=raw_meta.get("files", []),
        ),
    )


def _chunk_to_response(doc: ChunkDocument) -> ChunkResponse:
    return ChunkResponse(
        id=str(doc.id),
        repo_id=doc.repo_id,
        file_path=doc.file_path,
        language=doc.language,
        start_line=doc.start_line,
        end_line=doc.end_line,
        content=doc.content,
        chunk_index=doc.chunk_index,
        token_count=doc.token_count,
        chunk_type=doc.chunk_type,
        symbol_name=doc.symbol_name,
        symbol_metadata=doc.symbol_metadata,
        faiss_id=doc.faiss_id,
    )


# ------------------------------------------------------------------ #
# Routes — ingestion
# ------------------------------------------------------------------ #

@router.post(
    "/github",
    status_code=status.HTTP_202_ACCEPTED,
    response_model=IngestStartedResponse,
    summary="Ingest a GitHub repository",
)
async def ingest_github_repo(
    payload: GitHubIngestRequest,
    background_tasks: BackgroundTasks,
    service: IngestionService = Depends(IngestionService),
    current_user: UserDocument = Depends(get_current_user),
) -> IngestStartedResponse:
    repo_doc = await service.create_github_repo_record(
        github_url=payload.github_url,
        branch=payload.branch,
        user_id=str(current_user.id),
    )
    background_tasks.add_task(service.process_github_repo, str(repo_doc.id))
    return IngestStartedResponse(
        message="Repository ingestion started.",
        repo_id=str(repo_doc.id),
    )


@router.post(
    "/upload",
    status_code=status.HTTP_202_ACCEPTED,
    response_model=IngestStartedResponse,
    summary="Ingest a ZIP repository upload",
)
async def ingest_zip_repo(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
    service: IngestionService = Depends(IngestionService),
    current_user: UserDocument = Depends(get_current_user),
) -> IngestStartedResponse:
    if not file.filename or not file.filename.endswith(".zip"):
        raise UploadError("Only .zip archives are accepted.")

    # The file size is checked by the MaxUploadSizeMiddleware.
    # We remove synchronous zip validation to prevent memory exhaustion and blocking HTTP response.
    # Validation will happen in the background task.

    repo_doc = await service.create_zip_repo_record(file, user_id=str(current_user.id))
    background_tasks.add_task(service.process_zip_repo, str(repo_doc.id))
    return IngestStartedResponse(
        message="ZIP repository ingestion started.",
        repo_id=str(repo_doc.id),
    )


# ------------------------------------------------------------------ #
# Routes — listing / detail
# ------------------------------------------------------------------ #

@router.get(
    "",
    response_model=List[RepoSummaryResponse],
    summary="List all repositories",
)
async def list_repositories(
    status_filter: Optional[str] = Query(None, alias="status"),
    current_user: UserDocument = Depends(get_current_user),
) -> List[RepoSummaryResponse]:
    query = RepositoryDocument.find(RepositoryDocument.user_id == str(current_user.id))
    if status_filter:
        try:
            s = RepoStatus(status_filter)
            query = RepositoryDocument.find(
                RepositoryDocument.user_id == str(current_user.id),
                RepositoryDocument.status == s
            )
        except ValueError:
            pass
    docs = await query.sort("-created_at").to_list()
    return [_doc_to_summary(d) for d in docs]


@router.get(
    "/{repo_id}",
    response_model=RepoDetailResponse,
    summary="Get repository details including parse statistics",
)
async def get_repository(
    repo_id: str,
    current_user: UserDocument = Depends(get_current_user),
) -> RepoDetailResponse:
    doc = await RepositoryDocument.get(repo_id)
    if doc is None or doc.user_id != str(current_user.id):
        raise NotFoundError(f"Repository '{repo_id}' not found.")
    return _doc_to_detail(doc)


# ------------------------------------------------------------------ #
# Routes — file / chunk inspection
# ------------------------------------------------------------------ #

@router.get(
    "/{repo_id}/files",
    summary="List parsed file summaries for a repository",
)
async def list_repo_files(
    repo_id: str,
    current_user: UserDocument = Depends(get_current_user),
):
    doc = await RepositoryDocument.get(repo_id)
    if doc is None or doc.user_id != str(current_user.id):
        raise NotFoundError(f"Repository '{repo_id}' not found.")
    files = (doc.repo_metadata or {}).get("files", [])
    return {"repo_id": repo_id, "total": len(files), "files": files}


@router.get(
    "/{repo_id}/chunks",
    response_model=List[ChunkResponse],
    summary="List chunk documents for a repository",
)
async def list_repo_chunks(
    repo_id: str,
    file_path: Optional[str] = Query(None, description="Filter by file path"),
    chunk_type: Optional[str] = Query(None, description="Filter by chunk_type"),
    limit: int = Query(50, ge=1, le=500),
    skip: int = Query(0, ge=0),
    current_user: UserDocument = Depends(get_current_user),
) -> List[ChunkResponse]:
    doc = await RepositoryDocument.get(repo_id)
    if doc is None or doc.user_id != str(current_user.id):
        raise NotFoundError(f"Repository '{repo_id}' not found.")

    query = ChunkDocument.find(ChunkDocument.repo_id == repo_id)
    if file_path:
        query = query.find(ChunkDocument.file_path == file_path)
    if chunk_type:
        query = query.find(ChunkDocument.chunk_type == chunk_type)

    chunks = await query.skip(skip).limit(limit).to_list()
    return [_chunk_to_response(c) for c in chunks]


# ------------------------------------------------------------------ #
# Routes — deletion
# ------------------------------------------------------------------ #

@router.get(
    "/{repo_id}/health",
    summary="Check repository health (missing index, metadata, corruption)",
)
async def check_repo_health(
    repo_id: str,
    current_user: UserDocument = Depends(get_current_user),
):
    doc = await RepositoryDocument.get(repo_id)
    if doc is None or doc.user_id != str(current_user.id):
        raise NotFoundError(f"Repository '{repo_id}' not found.")
        
    health_status = {
        "status": doc.status.value,
        "is_healthy": True,
        "issues": []
    }
    
    if doc.status == RepoStatus.READY:
        from app.vector_store.faiss_store import FAISSStore
        from app.vector_store.metadata_store import MetadataStore
        
        # Check FAISS index
        store = FAISSStore(repo_id=repo_id, index_path=doc.faiss_index_path)
        if not store.exists():
            health_status["is_healthy"] = False
            health_status["issues"].append("FAISS index file missing from disk.")
            
        # Check MetadataStore
        meta_store = MetadataStore(repo_id=repo_id, index_path=doc.faiss_index_path)
        if not meta_store.exists():
            health_status["issues"].append("Metadata sidecar (chunk_meta.json) missing from disk.")
            
    return health_status


@router.delete(
    "/{repo_id}",
    status_code=status.HTTP_200_OK,
    summary="Delete a repository and all its associated data",
)
async def delete_repository(
    repo_id: str,
    service: IngestionService = Depends(IngestionService),
    current_user: UserDocument = Depends(get_current_user),
):
    doc = await RepositoryDocument.get(repo_id)
    if doc is None or doc.user_id != str(current_user.id):
        raise NotFoundError(f"Repository '{repo_id}' not found.")
    await service.delete_repo(repo_id)
    return {"success": True, "message": f"Repository '{repo_id}' deleted."}
