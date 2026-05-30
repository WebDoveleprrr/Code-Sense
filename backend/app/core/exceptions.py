# backend/app/core/exceptions.py
"""
CodeSense — Domain Exception Hierarchy + FastAPI Exception Handlers
"""

from __future__ import annotations

from typing import Any

from fastapi import FastAPI, Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from pydantic import ValidationError as PydanticValidationError
from app_logger import logger


# ------------------------------------------------------------------ #
# Domain Exceptions
# ------------------------------------------------------------------ #

class CodeSenseBaseError(Exception):
    """Root exception for all CodeSense domain errors."""

    status_code: int = status.HTTP_500_INTERNAL_SERVER_ERROR
    error_code: str = "INTERNAL_ERROR"

    def __init__(self, message: str, detail: Any = None) -> None:
        super().__init__(message)
        self.message = message
        self.detail = detail


class NotFoundError(CodeSenseBaseError):
    status_code = status.HTTP_404_NOT_FOUND
    error_code = "NOT_FOUND"


class ValidationError(CodeSenseBaseError):
    status_code = status.HTTP_422_UNPROCESSABLE_ENTITY
    error_code = "VALIDATION_ERROR"


class UploadError(CodeSenseBaseError):
    status_code = status.HTTP_400_BAD_REQUEST
    error_code = "UPLOAD_ERROR"


class EmbeddingError(CodeSenseBaseError):
    status_code = status.HTTP_500_INTERNAL_SERVER_ERROR
    error_code = "EMBEDDING_ERROR"


class VectorStoreError(CodeSenseBaseError):
    status_code = status.HTTP_500_INTERNAL_SERVER_ERROR
    error_code = "VECTOR_STORE_ERROR"


class GitHubError(CodeSenseBaseError):
    status_code = status.HTTP_502_BAD_GATEWAY
    error_code = "GITHUB_ERROR"


class RepositoryParseError(CodeSenseBaseError):
    status_code = status.HTTP_422_UNPROCESSABLE_ENTITY
    error_code = "REPO_PARSE_ERROR"


class SearchError(CodeSenseBaseError):
    status_code = status.HTTP_500_INTERNAL_SERVER_ERROR
    error_code = "SEARCH_ERROR"


class RAGError(CodeSenseBaseError):
    status_code = status.HTTP_500_INTERNAL_SERVER_ERROR
    error_code = "RAG_ERROR"


# ------------------------------------------------------------------ #
# Helper: Build error response body
# ------------------------------------------------------------------ #

def _error_body(
    error_code: str,
    message: str,
    detail: Any = None,
    status_code: int = 500,
) -> dict:
    body: dict[str, Any] = {
        "success": False,
        "error": {
            "code": error_code,
            "message": message,
        },
    }
    if detail is not None:
        body["error"]["detail"] = detail
    return body


# ------------------------------------------------------------------ #
# Exception Handlers
# ------------------------------------------------------------------ #

async def codesense_exception_handler(
    request: Request, exc: CodeSenseBaseError
) -> JSONResponse:
    logger.warning(
        "Domain error [{code}] on {method} {url}: {msg}",
        code=exc.error_code,
        method=request.method,
        url=str(request.url),
        msg=exc.message,
    )
    return JSONResponse(
        status_code=exc.status_code,
        content=_error_body(exc.error_code, exc.message, exc.detail, exc.status_code),
    )


async def validation_exception_handler(
    request: Request, exc: RequestValidationError | PydanticValidationError
) -> JSONResponse:
    errors = exc.errors()
    logger.warning("Validation error on {method} {url}: {errors}", method=request.method, url=str(request.url), errors=errors)
    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        content=_error_body(
            "VALIDATION_ERROR",
            "Request validation failed.",
            errors,
            status.HTTP_422_UNPROCESSABLE_ENTITY,
        ),
    )


async def unhandled_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    logger.exception(
        "Unhandled exception on {method} {url}",
        method=request.method,
        url=str(request.url),
    )
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content=_error_body("INTERNAL_ERROR", "An unexpected error occurred."),
    )


async def llm_unavailable_exception_handler(
    request: Request, exc: Exception
) -> JSONResponse:
    logger.warning(
        "LLM unavailable on {method} {url}: {msg}",
        method=request.method,
        url=str(request.url),
        msg=str(exc),
    )
    return JSONResponse(
        status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
        content={
            "success": False,
            "feature_disabled": True,
            "message": "Local LLM unavailable."
        }
    )


# ------------------------------------------------------------------ #
# Registration helper
# ------------------------------------------------------------------ #

def register_exception_handlers(app: FastAPI) -> None:
    """Attach all exception handlers to the FastAPI application."""
    from app.ml.llm_client import LLMUnavailableError
    app.add_exception_handler(LLMUnavailableError, llm_unavailable_exception_handler)  # type: ignore[arg-type]
    app.add_exception_handler(CodeSenseBaseError, codesense_exception_handler)  # type: ignore[arg-type]
    app.add_exception_handler(RequestValidationError, validation_exception_handler)  # type: ignore[arg-type]
    app.add_exception_handler(PydanticValidationError, validation_exception_handler)  # type: ignore[arg-type]
    app.add_exception_handler(Exception, unhandled_exception_handler)  # type: ignore[arg-type]
