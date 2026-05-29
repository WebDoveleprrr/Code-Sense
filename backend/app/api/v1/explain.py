# backend/app/api/v1/explain.py
"""
CodeSense — Explain Code Router
"""
from typing import Any, Dict, List, Optional
from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field

from app.services.explain_service import ExplainService

router = APIRouter()

class ExplainRequest(BaseModel):
    repo_id: str
    file_path: str
    start_line: int
    end_line: int

class ExplainResponse(BaseModel):
    success: bool
    explanation: str
    latency_ms: float

@router.post("", response_model=ExplainResponse)
async def explain_code(
    payload: ExplainRequest,
    service: ExplainService = Depends(ExplainService)
) -> ExplainResponse:
    result = await service.explain(
        repo_id=payload.repo_id,
        file_path=payload.file_path,
        start_line=payload.start_line,
        end_line=payload.end_line,
    )
    return ExplainResponse(**result)
