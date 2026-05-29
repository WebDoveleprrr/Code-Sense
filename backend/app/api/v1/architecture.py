# backend/app/api/v1/architecture.py
"""
CodeSense — Architecture Router
"""
from typing import Any, Dict, List, Optional
from fastapi import APIRouter, Depends
from pydantic import BaseModel

from app.services.architecture_service import ArchitectureService

router = APIRouter()

class ArchitectureRequest(BaseModel):
    repo_id: str

class ArchitectureResponse(BaseModel):
    success: bool
    repo_name: Optional[str] = None
    summary: Optional[str] = None
    language_breakdown: Optional[Dict[str, int]] = None
    metrics: Optional[Dict[str, Any]] = None
    entry_points: Optional[List[str]] = None
    key_modules: Optional[List[str]] = None
    patterns: Optional[List[str]] = None
    external_deps: Optional[List[str]] = None
    recommendations: Optional[List[str]] = None
    latency_ms: Optional[float] = None

@router.get("/{repo_id}", response_model=ArchitectureResponse)
async def get_architecture(
    repo_id: str,
    provider: Optional[str] = None,
    service: ArchitectureService = Depends(ArchitectureService)
) -> ArchitectureResponse:
    result = await service.summarise(
        repo_id=repo_id,
        provider=provider,
    )
    return ArchitectureResponse(**result)
