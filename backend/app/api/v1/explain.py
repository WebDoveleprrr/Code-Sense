# backend/app/api/v1/explain.py
"""
CodeSense — Explain Code Router
"""
from typing import Any, Dict, List, Optional, Union
from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field

from app.services.explain_service import ExplainService

router = APIRouter()

class ExplainRequest(BaseModel):
    repo_id: str
    file_path: Optional[str] = None
    start_line: Optional[int] = None
    end_line: Optional[int] = None
    code: Optional[str] = None

class ExplanationData(BaseModel):
    summary: str = ""
    detailed: str = ""
    complexity: Union[str, Dict[str, str]] = ""
    purpose: str = ""
    inputs: List[str] = Field(default_factory=list)
    outputs: List[str] = Field(default_factory=list)
    dependencies: List[str] = Field(default_factory=list)
    improvements: List[str] = Field(default_factory=list)

class ExplainResponse(BaseModel):
    success: bool
    explanation: ExplanationData
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
        code=payload.code,
    )
    return ExplainResponse(**result)
