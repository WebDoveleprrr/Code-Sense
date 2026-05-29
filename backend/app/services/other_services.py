# backend/app/services/explain_service.py
"""
CodeSense — Code Explanation Service
"""
from __future__ import annotations
import time
from app.core.exceptions import NotFoundError
from app.models.repository import RepositoryDocument, RepoStatus


class ExplainService:

    async def explain(self, repo_id: str, file_path: str, start_line: int, end_line: int) -> dict:
        t0 = time.perf_counter()

        repo = await RepositoryDocument.get(repo_id)
        if repo is None:
            raise NotFoundError(f"Repository '{repo_id}' not found.")

        # Extract raw code from the stored chunk or source file
        from app.ml.code_reader import read_lines

        code_snippet = await read_lines(repo, file_path, start_line, end_line)

        from app.ml.rag import generate_explanation

        explanation = await generate_explanation(code_snippet=code_snippet, language=file_path.rsplit(".", 1)[-1])

        elapsed_ms = (time.perf_counter() - t0) * 1_000
        return {
            "success": True,
            "file_path": file_path,
            "code_snippet": code_snippet,
            "explanation": explanation,
            "latency_ms": elapsed_ms,
        }


# -------------------------------------------------------------------------

# backend/app/services/dependency_service.py
"""
CodeSense — Dependency Graph Service
"""
from __future__ import annotations
import time
from app.core.exceptions import NotFoundError
from app.models.repository import RepositoryDocument


class DependencyService:

    async def build_graph(self, repo_id: str) -> dict:
        t0 = time.perf_counter()

        repo = await RepositoryDocument.get(repo_id)
        if repo is None:
            raise NotFoundError(f"Repository '{repo_id}' not found.")

        from app.ml.dependency_parser import parse_dependencies

        nodes, edges = await parse_dependencies(repo)
        elapsed_ms = (time.perf_counter() - t0) * 1_000

        return {
            "success": True,
            "repo_id": repo_id,
            "nodes": nodes,
            "edges": edges,
            "latency_ms": elapsed_ms,
        }


# -------------------------------------------------------------------------

# backend/app/services/architecture_service.py
"""
CodeSense — Architecture Summariser Service
"""
from __future__ import annotations
import time
from app.core.exceptions import NotFoundError
from app.models.repository import RepositoryDocument


class ArchitectureService:

    async def summarise(self, repo_id: str) -> dict:
        t0 = time.perf_counter()

        repo = await RepositoryDocument.get(repo_id)
        if repo is None:
            raise NotFoundError(f"Repository '{repo_id}' not found.")

        from app.ml.architecture_analyser import analyse_architecture

        result = await analyse_architecture(repo)
        elapsed_ms = (time.perf_counter() - t0) * 1_000

        return {
            "success": True,
            "repo_id": repo_id,
            **result,
            "latency_ms": elapsed_ms,
        }
