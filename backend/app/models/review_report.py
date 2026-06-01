# backend/app/models/review_report.py
from __future__ import annotations

from datetime import datetime
from typing import Any, Dict, List

from beanie import Document
from pydantic import Field

class ReviewReportDocument(Document):
    """
    Stores code review reports containing issues found by the Rule Engine + LLM.
    """
    repo_id: str
    issues: List[Dict[str, Any]] = Field(default_factory=list)
    created_at: datetime = Field(default_factory=datetime.utcnow)

    class Settings:
        name = "review_reports"
        indexes = [
            [("repo_id", 1)]
        ]
