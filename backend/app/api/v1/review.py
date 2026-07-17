# backend/app/api/v1/review.py
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from typing import List, Dict, Any, Optional

from app.services.review_service import ReviewService

router = APIRouter()

class ReviewRequest(BaseModel):
    repo_id: str = Field(..., description="Repository ID to review")

class ReviewIssueItem(BaseModel):
    severity: str
    category: str
    issue: str
    file: str
    line: Optional[int] = None
    why_it_matters: Optional[str] = None
    evidence: Optional[str] = None
    recommendation: str
    confidence: float

class ReviewScores(BaseModel):
    overall: float
    quality: float
    security: float
    maintainability: float
    performance: float

class ReviewResponse(BaseModel):
    success: bool
    repo_id: str
    issues: List[ReviewIssueItem]
    scores: ReviewScores
    summary: str
    recommendations: List[str]
    timestamp: str
    duration_ms: int
    model: str

@router.post("/analyze", response_model=ReviewResponse)
async def analyze_code(
    payload: ReviewRequest,
    service: ReviewService = Depends(ReviewService)
):
    try:
        result = await service.run_review(payload.repo_id)
        return ReviewResponse(
            success=True,
            repo_id=payload.repo_id,
            issues=result["issues"],
            scores=result["scores"],
            summary=result["summary"],
            recommendations=result["recommendations"],
            timestamp=result["timestamp"],
            duration_ms=result["duration_ms"],
            model=result["model"]
        )
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))
