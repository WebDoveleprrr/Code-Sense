# backend/app/api/v1/impact.py
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from typing import List, Dict, Any, Optional

from app.services.impact_service import ImpactService

router = APIRouter()

class ImpactRequest(BaseModel):
    repo_id: str = Field(..., description="Repository ID")
    file_path: str = Field(..., description="Target file path to analyze")
    symbol_name: Optional[str] = Field(default=None, description="Optional symbol name inside the file")
    algorithm: Optional[str] = Field(default="bfs", description="Traversal algorithm: bfs or dfs")

class ImpactResponse(BaseModel):
    success: bool
    affected_files: List[str]
    affected_functions: List[str]
    dependency_chain: List[List[str]]
    risk_score: float

@router.post("/analyze", response_model=ImpactResponse)
async def analyze_impact(
    payload: ImpactRequest,
    service: ImpactService = Depends(ImpactService)
):
    try:
        graph = await service.get_or_build_graph(payload.repo_id)
        result = service.analyze_impact(
            graph=graph,
            file_path=payload.file_path,
            symbol_name=payload.symbol_name,
            algorithm=payload.algorithm or "bfs"
        )
        return ImpactResponse(
            success=True,
            affected_files=result["affected_files"],
            affected_functions=result["affected_functions"],
            dependency_chain=result["dependency_chain"],
            risk_score=result["risk_score"]
        )
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))

@router.post("/rebuild", response_model=Dict[str, Any])
async def rebuild_graph(
    repo_id: str,
    service: ImpactService = Depends(ImpactService)
):
    try:
        await service.build_and_save_graph(repo_id)
        return {"success": True, "message": "Graph rebuilt successfully."}
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))
