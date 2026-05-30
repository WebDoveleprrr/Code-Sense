# backend/app/services/explain_service.py
"""
CodeSense — Function / Code Explanation Service (v2)

Replaces the stub in other_services.py with a full implementation:
  1. Read raw code from disk via code_reader
  2. Optionally retrieve semantic context for the function
  3. Generate explanation via rag.generate_explanation (LLM-backed)
  4. Return structured ExplainResponse-compatible dict
  5. Write audit log

Drop-in replacement — interface identical to v1 stub.
"""

from __future__ import annotations

import time
from typing import Optional

from app_logger import logger

from app.core.exceptions import NotFoundError
from app.models.repository import RepositoryDocument, RepoStatus
from app.models.search_log import QueryType, SearchLogDocument
from app.ml.rag import generate_explanation


class ExplainService:
    """
    Explains code snippets from a repository using LLM-backed generation.
    Stateless — instantiated per request via FastAPI Depends().
    """

    async def explain(
        self,
        repo_id: str,
        file_path: str,
        start_line: int,
        end_line: int,
        *,
        provider: Optional[str] = None,
    ) -> dict:
        """
        Explain a code range from a repository file.

        Args:
            repo_id:    Target repository ID.
            file_path:  Relative path to the source file.
            start_line: First line of the range (1-indexed).
            end_line:   Last line of the range (1-indexed, inclusive).
            provider:   LLM provider override.

        Returns:
            dict matching the ExplainResponse schema.
        """
        t0 = time.perf_counter()

        # ---------------------------------------------------------------- #
        # Validate repository
        # ---------------------------------------------------------------- #
        repo = await RepositoryDocument.get(repo_id)
        if repo is None:
            raise NotFoundError(f"Repository '{repo_id}' not found.")

        # ---------------------------------------------------------------- #
        # Read raw source lines
        # ---------------------------------------------------------------- #
        from app.ml.code_reader import read_lines

        code_snippet = await read_lines(
            repo=repo,
            file_path=file_path,
            start_line=start_line,
            end_line=end_line,
        )

        # ---------------------------------------------------------------- #
        # Infer language from extension
        # ---------------------------------------------------------------- #
        ext = file_path.rsplit(".", 1)[-1].lower() if "." in file_path else "text"
        language = _ext_to_language(ext)

        # ---------------------------------------------------------------- #
        # Infer symbol name from chunk metadata (optional enrichment)
        # ---------------------------------------------------------------- #
        symbol_name = await _find_symbol_name(
            repo_id=repo_id,
            file_path=file_path,
            start_line=start_line,
            end_line=end_line,
        )

        # ---------------------------------------------------------------- #
        # LLM-backed explanation
        # ---------------------------------------------------------------- #
        is_fallback = False
        try:
            explanation = await generate_explanation(
                code_snippet=code_snippet,
                language=language,
                file_path=file_path,
                symbol_name=symbol_name,
                provider=provider,
            )
        except Exception as exc:
            from app.ml.llm_client import LLMUnavailableError
            if isinstance(exc, LLMUnavailableError):
                raise
            logger.warning("LLM failure for explain, falling back: {err}", err=str(exc))
            explanation = _fallback_explain(code_snippet, language, file_path, symbol_name)
            is_fallback = True

        elapsed_ms = (time.perf_counter() - t0) * 1_000

        # ---------------------------------------------------------------- #
        # Audit log (fire-and-forget)
        # ---------------------------------------------------------------- #
        import asyncio

        asyncio.create_task(
            _write_explain_log(
                repo_id=repo_id,
                file_path=file_path,
                latency_ms=elapsed_ms,
            )
        )

        logger.info(
            "Explanation generated | repo={id} file={fp} lines={s}-{e} ({ms:.1f}ms)",
            id=repo_id,
            fp=file_path,
            s=start_line,
            e=end_line,
            ms=elapsed_ms,
        )

        return {
            "success": True,
            "file_path": file_path,
            "code_snippet": code_snippet,
            "explanation": explanation,
            "latency_ms": round(elapsed_ms, 2),
            "is_fallback": is_fallback,
        }

    # ---------------------------------------------------------------------- #
    # Explain by symbol name (alternative entry point)
    # ---------------------------------------------------------------------- #

    async def explain_symbol(
        self,
        repo_id: str,
        symbol_name: str,
        *,
        provider: Optional[str] = None,
    ) -> dict:
        """
        Find and explain a named symbol (function/class) by searching the
        MetadataStore / MongoDB for an exact symbol name match.
        """
        from app.models.chunk import ChunkDocument

        chunk = await ChunkDocument.find_one(
            ChunkDocument.repo_id == repo_id,
            ChunkDocument.symbol_name == symbol_name,
        )
        if chunk is None:
            raise NotFoundError(
                f"Symbol '{symbol_name}' not found in repository '{repo_id}'."
            )

        return await self.explain(
            repo_id=repo_id,
            file_path=chunk.file_path,
            start_line=chunk.start_line,
            end_line=chunk.end_line,
            provider=provider,
        )


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

EXTENSION_MAP = {
    "py": "python",
    "js": "javascript",
    "ts": "typescript",
    "jsx": "javascript",
    "tsx": "typescript",
    "java": "java",
    "go": "go",
    "rs": "rust",
    "cpp": "cpp",
    "cc": "cpp",
    "c": "c",
    "cs": "csharp",
    "rb": "ruby",
    "php": "php",
    "swift": "swift",
    "kt": "kotlin",
    "sh": "bash",
    "yaml": "yaml",
    "yml": "yaml",
    "json": "json",
    "md": "markdown",
    "html": "html",
    "css": "css",
    "sql": "sql",
}


def _ext_to_language(ext: str) -> str:
    return EXTENSION_MAP.get(ext.lstrip("."), ext or "text")


def _fallback_explain(code_snippet: str, language: str, file_path: str, symbol_name: Optional[str]) -> str:
    """Generate a heuristic explanation of the code snippet when LLM is unavailable."""
    lines = code_snippet.splitlines()
    num_lines = len(lines)
    
    imports = []
    classes = []
    functions = []
    
    for line in lines:
        line_s = line.strip()
        if line_s.startswith("import ") or line_s.startswith("from "):
            imports.append(line_s)
        elif line_s.startswith("class "):
            classes.append(line_s)
        elif line_s.startswith("def ") or line_s.startswith("function "):
            functions.append(line_s)
            
    summary = [
        f"**Extractive Mode Analysis** for `{file_path}`",
        "",
        f"This snippet contains {num_lines} lines of {language} code.",
    ]
    if symbol_name:
        summary.append(f"Target symbol: `{symbol_name}`.")
        
    summary.append("")
    summary.append("### Identified Structures")
    
    if imports:
        summary.append(f"- **Imports:** Found {len(imports)} import statements.")
    if classes:
        summary.append(f"- **Classes:** Found {len(classes)} class definition(s).")
    if functions:
        summary.append(f"- **Functions:** Found {len(functions)} function definition(s).")
        
    if not (imports or classes or functions):
        summary.append("- No top-level functions, classes, or imports identified heuristically.")
        
    return "\n".join(summary)


async def _find_symbol_name(
    repo_id: str,
    file_path: str,
    start_line: int,
    end_line: int,
) -> Optional[str]:
    """Look up the chunk document to find a stored symbol name."""
    try:
        from app.models.chunk import ChunkDocument

        chunk = await ChunkDocument.find_one(
            ChunkDocument.repo_id == repo_id,
            ChunkDocument.file_path == file_path,
            ChunkDocument.start_line == start_line,
        )
        if chunk:
            return chunk.symbol_name
    except Exception:
        pass
    return None


async def _write_explain_log(
    repo_id: str,
    file_path: str,
    latency_ms: float,
) -> None:
    try:
        await SearchLogDocument(
            repo_id=repo_id,
            query_type=QueryType.EXPLAIN,
            query=file_path,
            top_k=1,
            result_count=1,
            result_file_paths=[file_path],
            latency_ms=latency_ms,
        ).insert()
    except Exception as exc:
        logger.warning("Explain audit log write failed: {err}", err=str(exc))
