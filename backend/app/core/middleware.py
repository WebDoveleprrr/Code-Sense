# backend/app/core/middleware.py
"""
CodeSense — Custom Middleware Stack
  • Request ID injection
  • Request/response timing
  • Structured access logging
"""

from __future__ import annotations

import time
import uuid

from fastapi import FastAPI, Request, Response
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.trustedhost import TrustedHostMiddleware
from app_logger import logger
from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint

from app.core.config import get_settings


# ------------------------------------------------------------------ #
# Request-ID + Timing Middleware
# ------------------------------------------------------------------ #

class RequestContextMiddleware(BaseHTTPMiddleware):
    """
    Injects X-Request-ID header, measures latency, and emits a
    structured access-log entry for every request.
    """

    async def dispatch(self, request: Request, call_next: RequestResponseEndpoint) -> Response:
        request_id = str(uuid.uuid4())
        start = time.perf_counter()

        # Make request_id available downstream via request.state
        request.state.request_id = request_id

        response: Response = await call_next(request)

        elapsed_ms = (time.perf_counter() - start) * 1_000
        response.headers["X-Request-ID"] = request_id
        response.headers["X-Response-Time"] = f"{elapsed_ms:.2f}ms"

        logger.info(
            "{method} {path} → {status} ({elapsed:.1f}ms) [{rid}]",
            method=request.method,
            path=request.url.path,
            status=response.status_code,
            elapsed=elapsed_ms,
            rid=request_id,
        )

        return response


# ------------------------------------------------------------------ #
# Upload Size Guard Middleware
# ------------------------------------------------------------------ #

class MaxUploadSizeMiddleware(BaseHTTPMiddleware):
    """
    Reject multipart uploads that exceed MAX_UPLOAD_SIZE_BYTES before
    the body is read into memory.
    """

    async def dispatch(self, request: Request, call_next: RequestResponseEndpoint) -> Response:
        settings = get_settings()
        content_length = request.headers.get("content-length")

        if content_length and int(content_length) > settings.MAX_UPLOAD_SIZE_BYTES:
            from fastapi.responses import JSONResponse

            return JSONResponse(
                status_code=413,
                content={
                    "success": False,
                    "error": {
                        "code": "UPLOAD_TOO_LARGE",
                        "message": (
                            f"Upload exceeds the maximum allowed size of "
                            f"{settings.MAX_UPLOAD_SIZE_MB} MB."
                        ),
                    },
                },
            )

        return await call_next(request)


# ------------------------------------------------------------------ #
# Registration helper
# ------------------------------------------------------------------ #

def register_middleware(app: FastAPI) -> None:
    """Attach all middleware to the FastAPI application (order matters)."""
    settings = get_settings()

    # 4. Request context / access logging (innermost)
    app.add_middleware(RequestContextMiddleware)

    # 3. Max upload size guard
    app.add_middleware(MaxUploadSizeMiddleware)

    # 2. Trusted-host guard (production only)
    if settings.is_production:
        app.add_middleware(TrustedHostMiddleware, allowed_hosts=["*"])

    # 1. CORS — must be outermost
    app.add_middleware(
        CORSMiddleware,
        allow_origins=[
            "http://localhost:5173",
            "http://127.0.0.1:5173",
            "http://localhost:5174",
            "http://127.0.0.1:5174",
            "http://localhost:3000",
            "http://127.0.0.1:3000",
        ],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
