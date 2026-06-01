# backend/app/api/router.py
"""
CodeSense — Master API Router (v2)
All feature routers are registered here and mounted under /api/v1.
"""

from fastapi import APIRouter

from app.api.v1 import (
    repositories,
    search,
    qa,
    explain,
    dependency,
    architecture,
    health,
    vector_store,
    impact,
    review,
    auth,
)

api_router = APIRouter(prefix="/api/v1")

# ------------------------------------------------------------------ #
# Feature Routes
# ------------------------------------------------------------------ #
api_router.include_router(
    health.router,
    prefix="/health",
    tags=["Health"],
)

api_router.include_router(
    repositories.router,
    prefix="/repositories",
    tags=["Repositories"],
)

api_router.include_router(
    search.router,
    prefix="/search",
    tags=["Semantic Search"],
)

api_router.include_router(
    qa.router,
    prefix="/qa",
    tags=["Repository Q&A"],
)

api_router.include_router(
    explain.router,
    prefix="/explain",
    tags=["Function Explanation"],
)

api_router.include_router(
    dependency.router,
    prefix="/dependency",
    tags=["Dependency Graph"],
)

api_router.include_router(
    architecture.router,
    prefix="/architecture",
    tags=["Architecture Summary"],
)

api_router.include_router(
    vector_store.router,
    prefix="/vector-store",
    tags=["Vector Store"],
)

api_router.include_router(
    impact.router,
    prefix="/impact",
    tags=["Impact Analysis"],
)

api_router.include_router(
    review.router,
    prefix="/review",
    tags=["AI Code Review"],
)

api_router.include_router(
    auth.router,
    prefix="/auth",
    tags=["Authentication"],
)
