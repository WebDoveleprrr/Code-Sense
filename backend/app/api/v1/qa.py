# backend/app/api/v1/qa.py
"""
CodeSense — Q&A Router
"""
from typing import Any, Dict, List, Optional
from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field

from app.services.qa_service import QAService

router = APIRouter()

class QARequest(BaseModel):
    repo_id: str
    question: str = Field(..., min_length=5)
    top_k: int = Field(default=8, ge=1, le=20)
    language_filter: Optional[str] = None

class QAResponse(BaseModel):
    success: bool
    question: str
    answer: str
    context_chunks: List[Dict[str, Any]]
    latency_ms: float

@router.post("", response_model=QAResponse)
async def answer_question(
    payload: QARequest,
    service: QAService = Depends(QAService)
) -> QAResponse:
    result = await service.answer(
        repo_id=payload.repo_id,
        question=payload.question,
        top_k=payload.top_k,
        language_filter=payload.language_filter,
    )
    return QAResponse(**result)
