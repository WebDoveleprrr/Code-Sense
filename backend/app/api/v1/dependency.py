# backend/app/api/v1/dependency.py
"""
CodeSense — Dependency Graph Endpoint
"""
from __future__ import annotations
from typing import Dict, List
from fastapi import APIRouter, Depends
from pydantic import BaseModel
from app.services.dependency_service import DependencyService

router = APIRouter()


class DependencyNode(BaseModel):
    id: str
    label: str
    language: str
    file_path: str


class DependencyEdge(BaseModel):
    source: str
    target: str
    type: str   # import | call | inherit


class DependencyGraphResponse(BaseModel):
    success: bool
    repo_id: str
    nodes: List[DependencyNode]
    edges: List[DependencyEdge]
    latency_ms: float


@router.get(
    "/{repo_id}",
    response_model=DependencyGraphResponse,
    summary="Get dependency graph for a repository",
)
async def get_dependency_graph(
    repo_id: str,
    service: DependencyService = Depends(DependencyService),
) -> DependencyGraphResponse:
    return await service.build_graph(repo_id)
