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
        file_path: Optional[str] = None,
        start_line: Optional[int] = None,
        end_line: Optional[int] = None,
        code: Optional[str] = None,
        *,
        provider: Optional[str] = None,
    ) -> dict:
        """
        Explain a code range from a repository file or a raw code snippet.
        """
        t0 = time.perf_counter()

        # ---------------------------------------------------------------- #
        # Validate repository
        # ---------------------------------------------------------------- #
        repo = await RepositoryDocument.get(repo_id)
        if repo is None:
            raise NotFoundError(f"Repository '{repo_id}' not found.")

        # ---------------------------------------------------------------- #
        # Read raw source lines or use provided code
        # ---------------------------------------------------------------- #
        if code:
            code_snippet = code
            file_path = file_path or "snippet.txt"
        else:
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
        symbol_name = None
        if not code and file_path and start_line:
            symbol_name = await _find_symbol_name(
                repo_id=repo_id,
                file_path=file_path,
                start_line=start_line,
                end_line=end_line,
            )

        # ---------------------------------------------------------------- #
        # Tree-Sitter AST context extraction
        # ---------------------------------------------------------------- #
        parsed_metadata = {}
        if not code and file_path:
            full_content = ""
            try:
                from app.core.config import get_settings
                settings = get_settings()
                repo_dir = settings.UPLOAD_DIR / str(repo.id)
                full_path_obj = repo_dir / file_path
                if full_path_obj.exists():
                    full_content = full_path_obj.read_text(encoding="utf-8", errors="replace")
            except Exception:
                pass

            if not full_content:
                full_content = code_snippet

            from app.ml.parsers import parse_source
            try:
                parsed_metadata = parse_source({
                    "file_path": file_path,
                    "content": full_content,
                    "language": language
                })
            except Exception as exc:
                logger.warning("Tree-sitter parse failed during explain context generation: {err}", err=str(exc))

        # ---------------------------------------------------------------- #
        # LLM-backed explanation
        # ---------------------------------------------------------------- #
        is_fallback = False
        try:
            explanation_str = await generate_explanation(
                code_snippet=code_snippet,
                language=language,
                file_path=file_path,
                symbol_name=symbol_name,
                metadata=parsed_metadata,
                provider=provider,
            )
            import json, re
            clean_response = re.sub(r"^```json\s*", "", explanation_str, flags=re.IGNORECASE)
            clean_response = re.sub(r"\s*```$", "", clean_response, flags=re.IGNORECASE).strip()
            explanation = json.loads(clean_response)
            
            # Defensive Parsing
            for key in ["inputs", "outputs", "dependencies", "improvements"]:
                val = explanation.get(key)
                if not isinstance(val, list):
                    explanation[key] = []
                    
            comp = explanation.get("complexity")
            if isinstance(comp, dict):
                explanation["complexity"] = "\n".join(f"{k}: {v}" for k, v in comp.items())
            elif not isinstance(comp, str):
                explanation["complexity"] = str(comp or "")
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

        if not code and file_path:
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
            "explanation": explanation,
            "latency_ms": round(elapsed_ms, 2)
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


def _fallback_explain(code_snippet: str, language: str, file_path: str, symbol_name: Optional[str]) -> dict:
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
            
    summary = f"**Extractive Mode Analysis** for `{file_path}`. This snippet contains {num_lines} lines of {language} code."
    
    detailed = "Identified structures:\n"
    if imports:
        detailed += f"- **Imports:** Found {len(imports)} import statements.\n"
    if classes:
        detailed += f"- **Classes:** Found {len(classes)} class definition(s).\n"
    if functions:
        detailed += f"- **Functions:** Found {len(functions)} function definition(s).\n"
        
    return {
        "summary": summary,
        "detailed": detailed,
        "complexity": "Unknown (Fallback Mode)",
        "purpose": "Static structural extraction fallback.",
        "inputs": [],
        "outputs": [],
        "dependencies": imports,
        "improvements": ["Connect an LLM provider for deep analysis."]
    }


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
