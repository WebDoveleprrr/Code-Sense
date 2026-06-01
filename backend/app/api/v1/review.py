# backend/app/api/v1/review.py
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from typing import List, Dict, Any

from app.services.review_service import ReviewService

router = APIRouter()

class ReviewRequest(BaseModel):
    repo_id: str = Field(..., description="Repository ID to review")

class ReviewIssueItem(BaseModel):
    severity: str
    category: str
    issue: str
    file: str
    recommendation: str
    confidence: float

class ReviewResponse(BaseModel):
    success: bool
    repo_id: str
    issues: List[ReviewIssueItem]

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
            issues=result["issues"]
        )
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))
