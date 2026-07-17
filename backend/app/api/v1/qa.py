# backend/app/api/v1/qa.py
"""
CodeSense — Q&A Router
"""
from typing import Any, Dict, List, Optional
from fastapi import APIRouter, Depends, Request
from pydantic import BaseModel, Field

from app.services.qa_service import QAService

router = APIRouter()

class QARequest(BaseModel):
    repo_id: str
    question: str = Field(..., min_length=5)
    top_k: int = Field(default=8, ge=1, le=20)
    language_filter: Optional[str] = None
    strict_mode: bool = False

class QAResponse(BaseModel):
    success: bool
    question: str
    answer: str
    sources: List[Dict[str, Any]]
    confidence: float = 0.0
    latency_ms: float
    is_fallback: bool = False

@router.post("", response_model=QAResponse)
async def answer_question(
    request: Request,
    payload: QARequest,
    service: QAService = Depends(QAService)
) -> QAResponse:
    if await request.is_disconnected():
        return QAResponse(success=False, question=payload.question, answer="Client disconnected", sources=[], latency_ms=0)
        
    result = await service.answer(
        repo_id=payload.repo_id,
        question=payload.question,
        top_k=payload.top_k,
        language_filter=payload.language_filter,
        strict_mode=payload.strict_mode,
    )
    return QAResponse(**result)
