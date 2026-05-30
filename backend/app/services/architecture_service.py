# backend/app/services/architecture_service.py
"""
CodeSense — Architecture Summariser Service (v2)

Replaces the stub in other_services.py with a RAG-enhanced implementation:
  1. Compute structural metrics from RepositoryDocument metadata
  2. Retrieve a broad code sample via semantic search ("architecture entry points")
  3. Feed metadata + code samples to rag.generate_architecture_summary
  4. Return enriched ArchitectureSummaryResponse-compatible dict
  5. Audit log

Drop-in replacement — interface identical to v1 stub.
"""

from __future__ import annotations

import time
from pathlib import Path
from typing import Dict, List, Optional, Any

from app_logger import logger

from app.core.config import get_settings
from app.core.exceptions import NotFoundError
from app.models.repository import RepositoryDocument
from app.models.search_log import QueryType, SearchLogDocument
from app.ml.rag import generate_architecture_summary


# Architecture seed queries used to pull representative code samples
ARCHITECTURE_SEED_QUERIES = [
    "application entry point main function",
    "configuration settings environment variables",
    "database connection models schema",
    "API routes endpoints handlers",
    "service layer business logic",
]


class ArchitectureService:
    """
    Generates AI-powered architecture summaries.
    Stateless — instantiated per request via FastAPI Depends().
    """

    async def summarise(
        self,
        repo_id: str,
        *,
        provider: Optional[str] = None,
    ) -> dict:
        """
        Generate a comprehensive architecture summary for a repository.

        Args:
            repo_id:  Target repository ID.
            provider: LLM provider override.

        Returns:
            dict matching the ArchitectureSummaryResponse schema.
        """
        t0 = time.perf_counter()

        # ---------------------------------------------------------------- #
        # Load repo
        # ---------------------------------------------------------------- #
        repo = await RepositoryDocument.get(repo_id)
        if repo is None:
            raise NotFoundError(f"Repository '{repo_id}' not found.")

        # ---------------------------------------------------------------- #
        # Structural metrics from stored metadata
        # ---------------------------------------------------------------- #
        raw_meta = repo.repo_metadata or {}
        total_functions = raw_meta.get("total_functions", 0)
        total_classes = raw_meta.get("total_classes", 0)
        total_lines = raw_meta.get("total_lines", 0)
        file_list = [f.get("file_path", "") for f in raw_meta.get("files", [])]

        # ---------------------------------------------------------------- #
        # Static analysis (entry points, key components)
        # ---------------------------------------------------------------- #
        entry_points, key_components = _extract_structural_info(repo)

        # ---------------------------------------------------------------- #
        # RAG: retrieve code samples from representative areas
        # ---------------------------------------------------------------- #
        code_samples = await _retrieve_code_samples(repo_id=repo_id)

        # ---------------------------------------------------------------- #
        # LLM-backed architecture summary
        # ---------------------------------------------------------------- #
        is_fallback = False
        try:
            summary_text = await generate_architecture_summary(
                repo_name=repo.name,
                language_breakdown=repo.language_breakdown,
                total_files=repo.total_files,
                total_functions=total_functions,
                total_classes=total_classes,
                entry_points=entry_points,
                key_components=key_components,
                sample_files=file_list,
                code_samples=code_samples,
                provider=provider,
            )
        except Exception as exc:
            from app.ml.llm_client import LLMUnavailableError
            if isinstance(exc, LLMUnavailableError):
                raise
            logger.warning("LLM failure for architecture, falling back: {err}", err=str(exc))
            summary_text = _fallback_architecture(repo.name, repo.language_breakdown, entry_points, key_components)
            is_fallback = True

        elapsed_ms = (time.perf_counter() - t0) * 1_000

        # ---------------------------------------------------------------- #
        # Audit log
        # ---------------------------------------------------------------- #
        import asyncio

        asyncio.create_task(
            _write_arch_log(
                repo_id=repo_id,
                latency_ms=elapsed_ms,
            )
        )

        logger.info(
            "Architecture summary generated for repo {id} in {ms:.1f}ms",
            id=repo_id,
            ms=elapsed_ms,
        )

        return {
            "success": True,
            "repo_name": repo.name,
            "summary": summary_text,
            "language_breakdown": repo.language_breakdown,
            "metrics": {
                "total_files": repo.total_files,
                "total_functions": total_functions,
                "total_classes": total_classes,
                "total_lines": total_lines,
                "total_imports": raw_meta.get("total_imports", 0),
                "total_chunks": getattr(repo, "total_chunks", 0),
            },
            "entry_points": entry_points,
            "key_modules": key_components,
            "patterns": [],
            "external_deps": [],
            "recommendations": [],
            "latency_ms": round(elapsed_ms, 2),
            "is_fallback": is_fallback,
        }


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

ENTRY_NAMES = {
    "main.py", "app.py", "server.py", "index.js", "index.ts",
    "main.go", "main.rs", "Program.cs", "app.js", "app.ts",
    "__main__.py",
}

CONFIG_NAMES = {
    "pyproject.toml", "setup.py", "setup.cfg",
    "package.json", "Cargo.toml", "go.mod", "pom.xml",
    "requirements.txt", "Pipfile", "poetry.lock",
    "docker-compose.yml", "Dockerfile", ".env.example",
}


def _extract_structural_info(repo: RepositoryDocument):
    """
    Walk the stored file list to identify entry points and config files.
    Returns (entry_points, key_components).
    """
    raw_meta = repo.repo_metadata or {}
    files = [f.get("file_path", "") for f in raw_meta.get("files", [])]

    entry_points: List[str] = []
    key_components: List[str] = []

    for fp in files:
        name = Path(fp).name
        if name in ENTRY_NAMES:
            entry_points.append(fp)
        if name in CONFIG_NAMES:
            key_components.append(name)

    return entry_points[:5], list(set(key_components))[:10]


def _fallback_architecture(
    repo_name: str,
    language_breakdown: Dict[str, Any],
    entry_points: List[str],
    key_components: List[str]
) -> str:
    """Generate a heuristic architecture summary when LLM is unavailable."""
    lines = [
        f"**Local Structural Analysis Mode** for `{repo_name}`",
        "",
        "The AI provider is currently unavailable. This is an extractive architecture summary based on static heuristics.",
        "",
        "### High-Level Structure"
    ]
    
    if language_breakdown:
        top_langs = sorted(language_breakdown.items(), key=lambda x: x[1], reverse=True)[:3]
        lang_str = ", ".join(f"{lang}" for lang, _ in top_langs)
        lines.append(f"- **Primary Languages:** {lang_str}")
        
    if entry_points:
        lines.append("- **Detected Entry Points:** " + ", ".join(f"`{ep}`" for ep in entry_points))
    else:
        lines.append("- **Detected Entry Points:** None found heuristically.")
        
    if key_components:
        lines.append("- **Key Configuration/Components:** " + ", ".join(f"`{kc}`" for kc in key_components))
        
    return "\n".join(lines)


async def _retrieve_code_samples(repo_id: str, max_chars: int = 3_000) -> Optional[str]:
    """
    Use semantic search to pull representative code samples across several
    architectural seed queries. Returns a compact formatted context string.
    """
    try:
        from app.services.retrieval_service import RetrievalService
        from app.ml.prompt_templates import format_retrieved_context

        svc = RetrievalService()
        all_chunks: List[Dict[str, Any]] = []
        seen_files = set()

        for seed in ARCHITECTURE_SEED_QUERIES:
            result = await svc.retrieve(
                repo_id=repo_id,
                query=seed,
                top_k=2,
                use_metadata_cache=False,
            )
            for chunk in result.get("results", []):
                fp = chunk.get("file_path", "")
                if fp not in seen_files:
                    all_chunks.append(chunk)
                    seen_files.add(fp)

        if not all_chunks:
            return None

        return format_retrieved_context(all_chunks, max_chars=max_chars)

    except Exception as exc:
        logger.warning("Architecture code sample retrieval failed: {err}", err=str(exc))
        return None


def _lang_to_ext(lang: str) -> str:
    mapping = {
        "python": "py", "javascript": "js", "typescript": "ts",
        "java": "java", "go": "go", "rust": "rs", "cpp": "cpp",
        "csharp": "cs", "ruby": "rb",
    }
    return mapping.get(lang.lower(), lang.lower())


async def _write_arch_log(repo_id: str, latency_ms: float) -> None:
    try:
        await SearchLogDocument(
            repo_id=repo_id,
            query_type=QueryType.ARCHITECTURE,
            query="architecture_summary",
            top_k=0,
            result_count=0,
            result_file_paths=[],
            latency_ms=latency_ms,
        ).insert()
    except Exception as exc:
        logger.warning("Architecture audit log write failed: {err}", err=str(exc))
