# backend/app/api/v1/explain.py
"""
CodeSense — Explain Code Router
"""
from typing import Any, Dict, List, Optional, Union
from fastapi import APIRouter, Depends, Request
from pydantic import BaseModel, Field

from app.services.explain_service import ExplainService

router = APIRouter()

class ExplainRequest(BaseModel):
    repo_id: str
    file_path: Optional[str] = None
    start_line: Optional[int] = None
    end_line: Optional[int] = None
    code: Optional[Union[str, Dict[str, Any], Any]] = None
    explanation: Optional[Dict[str, Any]] = None

class ExplanationData(BaseModel):
    summary: str = ""
    detailed: str = ""
    complexity: Union[str, Dict[str, str]] = ""
    purpose: str = ""
    inputs: List[str] = Field(default_factory=list)
    outputs: List[str] = Field(default_factory=list)
    side_effects: List[str] = Field(default_factory=list)
    dependencies: List[str] = Field(default_factory=list)
    improvements: List[str] = Field(default_factory=list)

class ExplainResponse(BaseModel):
    success: bool
    explanation: ExplanationData
    language: str = "Unknown"
    latency_ms: float

@router.post("", response_model=ExplainResponse)
async def explain_code(
    request: Request,
    payload: ExplainRequest,
    service: ExplainService = Depends(ExplainService)
) -> ExplainResponse:
    if await request.is_disconnected():
        return ExplainResponse(success=False, explanation=ExplanationData(), latency_ms=0)
        
    code_str = None
    if payload.explanation:
        repo_id = payload.explanation.get("repo_id", payload.repo_id)
        raw_code = payload.explanation.get("code", payload.code)
    else:
        repo_id = payload.repo_id
        raw_code = payload.code
        
    if raw_code is not None:
        code_str = str(raw_code) if not isinstance(raw_code, str) else raw_code

    result = await service.explain(
        repo_id=repo_id,
        file_path=payload.file_path,
        start_line=payload.start_line,
        end_line=payload.end_line,
        code=code_str,
    )
    return ExplainResponse(**result)
