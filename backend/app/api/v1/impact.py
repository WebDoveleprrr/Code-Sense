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
    impact_score: float
    risk_level: str
    affected_files: List[str]
    affected_functions: List[str]
    affected_classes: List[str]
    incoming_dependencies: int
    outgoing_dependencies: int
    dependency_depth: int
    fan_in: int
    fan_out: int
    dependency_chain: List[List[str]]
    score_reason: Optional[str] = Field(default=None)
    traversal_order: Optional[List[str]] = Field(default_factory=list)
    graph_nodes: Optional[List[Dict[str, Any]]] = Field(default_factory=list)
    graph_edges: Optional[List[Dict[str, Any]]] = Field(default_factory=list)

@router.post("/analyze", response_model=ImpactResponse)
async def analyze_impact(
    payload: ImpactRequest,
    service: ImpactService = Depends(ImpactService)
):
    try:
        from app.models.repository import RepositoryDocument
        repo = await RepositoryDocument.get(payload.repo_id)
        if repo:
            files = repo.repo_metadata.get("files", [])
            normalized = payload.file_path.replace('\\', '/').replace('./', '').lstrip('/')
            exists = False
            for f in files:
                f_path = f.get("file_path", "") if isinstance(f, dict) else str(f)
                f_path_norm = f_path.replace('\\', '/')
                if f_path_norm.endswith(normalized) or normalized in f_path_norm:
                    exists = True
                    break
            if not exists:
                return ImpactResponse(
                    success=True, impact_score=0.0, risk_level="Low",
                    affected_files=[], affected_functions=[], affected_classes=[],
                    incoming_dependencies=0, outgoing_dependencies=0, dependency_depth=0,
                    fan_in=0, fan_out=0, dependency_chain=[], score_reason="File not found.",
                    graph_nodes=[], graph_edges=[]
                )

        graph = await service.get_or_build_graph(payload.repo_id)
        result = service.analyze_impact(
            graph=graph,
            file_path=payload.file_path,
            symbol_name=payload.symbol_name,
            algorithm=payload.algorithm or "bfs"
        )
        return ImpactResponse(
            success=True,
            impact_score=result.get("impact_score", 0.0),
            risk_level=result.get("risk_level", "Low"),
            affected_files=result.get("affected_files", []),
            affected_functions=result.get("affected_functions", []),
            affected_classes=result.get("affected_classes", []),
            incoming_dependencies=result.get("incoming_dependencies", 0),
            outgoing_dependencies=result.get("outgoing_dependencies", 0),
            dependency_depth=result.get("dependency_depth", 0),
            fan_in=result.get("fan_in", 0),
            fan_out=result.get("fan_out", 0),
            dependency_chain=result.get("dependency_chain", []),
            score_reason=result.get("score_reason", ""),
            traversal_order=result.get("traversal_order", []),
            graph_nodes=result.get("graph_nodes", []),
            graph_edges=result.get("graph_edges", [])
        )
    except Exception as exc:
        import logging
        logging.getLogger("app").exception(f"Impact analysis error: {str(exc)}")
        raise HTTPException(status_code=500, detail="An unexpected error occurred while analyzing the impact. Please try again.")

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
