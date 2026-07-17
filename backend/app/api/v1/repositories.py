# backend/app/api/v1/repositories.py --- Repository Management API Layer
from __future__ import annotations
"""
CodeSense — Repository Management Endpoints (v2)
  POST   /repositories/github          — ingest from GitHub URL
  POST   /repositories/upload          — ingest from ZIP file
  GET    /repositories                  — list all repositories
  GET    /repositories/{repo_id}        — get repository details (with parse stats)
  GET    /repositories/{repo_id}/files  — list parsed files with symbol counts
  GET    /repositories/{repo_id}/chunks — list chunk documents
  DELETE /repositories/{repo_id}        — delete repository and all data

Its job is to expose HTTP endpoints that allow the frontend to:

Upload repositories
Connect GitHub repositories
View repository status
View repository metadata
View parsed files
View chunks
Check repository health
Delete repositories
"""

from typing import List, Optional # Used for: List[ChunkResponse] ---- Array of ChunkResponse objects

from pydantic import BaseModel
from fastapi import APIRouter, BackgroundTasks, Depends, File, Query, UploadFile, status, HTTPException
#APIRouter --- Creates route groups Without it: All endpoints would be dumped into main.py
#backgroundtasks --- Allows work after response. Important for ingestion.

from app.core.exceptions import NotFoundError, UploadError
from app.models.chunk import ChunkDocument
from app.models.repository import RepositoryDocument, RepoStatus, RepoSource
from app.schemas.ingestion import (
    ChunkResponse,
    GitHubIngestRequest,
    IngestStartedResponse,
    RepoDetailResponse,
    RepoMetadataSchema,
    RepoSummaryResponse,
)
from app.services.ingestion_service import IngestionService
from app.core.auth import get_current_user #JWT authentication
from app.models.user import UserDocument #Represents authenticated use

router = APIRouter() #Creates route group --- Later mounted in main.py.


#Convert: RepositoryDocument into: RepoSummaryResponse --- Used in repository listing.
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

#Detailed repository response --- Used by: GET /repositories/{id}
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

#Convert: ChunkDocument to ChunkResponse --- Used by: GET /chunks
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


#Creates: POST /repositories/github
@router.post(
    "/github",
    status_code=status.HTTP_202_ACCEPTED,
    response_model=IngestStartedResponse,
    summary="Ingest a GitHub repository",
)
async def ingest_github_repo(
    payload: GitHubIngestRequest, #GitHubIngestRequest --- Contains:{"github_url": "...","branch": "..."}
    background_tasks: BackgroundTasks, #Without it: request blocks,User waits,Possible timeout
    service: IngestionService = Depends(IngestionService), #FastAPI automatically creates service instance
    current_user: UserDocument = Depends(get_current_user),
) -> IngestStartedResponse:
    repo_doc = await service.create_github_repo_record(
        github_url=payload.github_url,
        branch=payload.branch,
        user_id=str(current_user.id),
        overwrite=payload.overwrite,
    )
    background_tasks.add_task(service.process_github_repo, str(repo_doc.id)) #Allows: Immediate response,Long-running ingestion
    return IngestStartedResponse(
        message="Repository ingestion started.",
        repo_id=str(repo_doc.id),
    )

#ZIP upload ingestion
@router.post(
    "/upload",
    status_code=status.HTTP_202_ACCEPTED,
    response_model=IngestStartedResponse,
    summary="Ingest a ZIP repository upload",
)
async def ingest_zip_repo(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
    overwrite: bool = Query(False, description="Overwrite if exists"),
    service: IngestionService = Depends(IngestionService),
    current_user: UserDocument = Depends(get_current_user),
) -> IngestStartedResponse:
    if not file.filename or not file.filename.endswith(".zip"): #check if zip or not
        raise UploadError("Only .zip archives are accepted.")

    #Validation moved to background task --- Avoid memory exhaustion
    
    repo_doc = await service.create_zip_repo_record(file, user_id=str(current_user.id), overwrite=overwrite)
    background_tasks.add_task(service.process_zip_repo, str(repo_doc.id))
    return IngestStartedResponse(
        message="ZIP repository ingestion started.",
        repo_id=str(repo_doc.id),
    )

#GET /repositories --- Repository dashboard
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

#GET /repositories/{repo_id} --- Detailed repository view
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
    if doc is None or doc.user_id != str(current_user.id):  #Prevents: User A viewing User B repository
        raise NotFoundError(f"Repository '{repo_id}' not found.")
    return _doc_to_detail(doc)

#GET /repositories/{repo_id}/files --- Return parsed file metadata
@router.get(
    "/{repo_id}/files",
    summary="List parsed file summaries for a repository",
)
async def list_repo_files(
    repo_id: str,
    q: Optional[str] = Query(None, description="Prefix or partial path to filter files"),
    limit: int = Query(50, ge=1, le=500),
    current_user: UserDocument = Depends(get_current_user),
):
    doc = await RepositoryDocument.get(repo_id)
    if doc is None or doc.user_id != str(current_user.id):
        raise NotFoundError(f"Repository '{repo_id}' not found.")
    files = (doc.repo_metadata or {}).get("files", [])
    
    if q:
        q_lower = q.lower()
        files = [f for f in files if q_lower in (f.get("file_path", "") if isinstance(f, dict) else f).lower()]
        
    # Return at most 'limit' results to keep autocomplete fast
    files = files[:limit]
    
    return {"repo_id": repo_id, "total": len(files), "files": files}

#GET /repositories/{repo_id}/chunks --- Inspect chunk database --- Useful for: Debugging,Search verification,Chunk analysis
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


#Verify repository integrity --- Checks: MongoDB record,FAISS index file,Metadata sidecar file
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
        if not store.exists():  #Verifies: FAISS index still exists on disk
            health_status["is_healthy"] = False
            health_status["issues"].append("FAISS index file missing from disk.")
            
        # Check MetadataStore
        meta_store = MetadataStore(repo_id=repo_id, index_path=doc.faiss_index_path)
        if not meta_store.exists():
            health_status["issues"].append("Metadata sidecar (chunk_meta.json) missing from disk.")
            
    return health_status

#POST /repositories/{repo_id}/reindex --- Re-run indexing for an existing repo
@router.post(
    "/{repo_id}/reindex",
    status_code=status.HTTP_202_ACCEPTED,
    response_model=IngestStartedResponse,
    summary="Re-index an existing repository",
)
async def reindex_repository(
    repo_id: str,
    background_tasks: BackgroundTasks,
    service: IngestionService = Depends(IngestionService),
    current_user: UserDocument = Depends(get_current_user),
) -> IngestStartedResponse:
    doc = await RepositoryDocument.get(repo_id)
    if doc is None or doc.user_id != str(current_user.id):
        raise NotFoundError(f"Repository '{repo_id}' not found.")
        
    if doc.source == RepoSource.GITHUB:
        background_tasks.add_task(service.process_github_repo, repo_id)
    else:
        background_tasks.add_task(service.process_zip_repo, repo_id)
        
    return IngestStartedResponse(
        message="Repository re-indexing started.",
        repo_id=repo_id,
    )

#DELETE /repositories/{repo_id} --- Remove repository completely
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

class RenameRepoRequest(BaseModel):
    new_name: str

@router.patch(
    "/{repo_id}/rename",
    status_code=status.HTTP_200_OK,
    summary="Rename an existing repository",
)
async def rename_repository(
    repo_id: str,
    payload: RenameRepoRequest,
    current_user: UserDocument = Depends(get_current_user),
):
    if not payload.new_name or not payload.new_name.strip():
        raise HTTPException(status_code=400, detail="Repository name cannot be empty.")
    
    new_name = payload.new_name.strip()
    # Check duplicate
    duplicate = await RepositoryDocument.find_one(
        RepositoryDocument.user_id == str(current_user.id),
        RepositoryDocument.name == new_name
    )
    if duplicate and str(duplicate.id) != repo_id:
        raise HTTPException(status_code=400, detail=f"Repository '{new_name}' already exists.")

    doc = await RepositoryDocument.get(repo_id)
    if doc is None or doc.user_id != str(current_user.id):
        raise NotFoundError(f"Repository '{repo_id}' not found.")

    doc.name = new_name
    from datetime import datetime
    doc.updated_at = datetime.utcnow()
    await doc.save()
    
    # Invalidate caching if necessary, or let frontend handle it
    return {"success": True, "message": "Repository renamed.", "repo_id": repo_id, "new_name": new_name}
