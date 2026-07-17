# backend/app/api/v1/architecture.py
"""
CodeSense — Architecture Router
"""
from typing import Any, Dict, List, Optional
from fastapi import APIRouter, Depends, Request
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
    request: Request,
    repo_id: str,
    provider: Optional[str] = None,
    force_regenerate: bool = False,
    service: ArchitectureService = Depends(ArchitectureService)
) -> ArchitectureResponse:
    if await request.is_disconnected():
        return ArchitectureResponse(success=False, latency_ms=0)
        
    result = await service.summarise(
        repo_id=repo_id,
        provider=provider,
        force_regenerate=force_regenerate,
    )
    return ArchitectureResponse(**result)
