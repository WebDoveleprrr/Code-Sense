# backend/app/services/ingestion_service.py
"""
CodeSense — Ingestion Service
Handles GitHub repo ingestion, ZIP upload ingestion, and cleanup.
Heavy processing (cloning, parsing, embedding) runs in background tasks.
"""

from __future__ import annotations

import shutil
from datetime import datetime
from pathlib import Path

import aiofiles
from fastapi import UploadFile
from app_logger import logger

from app.core.config import get_settings
from app.core.exceptions import GitHubError, NotFoundError, RepositoryParseError, UploadError
from app.models.chunk import ChunkDocument
from app.models.repository import RepositoryDocument, RepoSource, RepoStatus


class IngestionService:
    """Orchestrates end-to-end repository ingestion pipelines."""

    def __init__(self) -> None:
        self.settings = get_settings()

    # ---------------------------------------------------------------- #
    # GitHub Ingestion
    # ---------------------------------------------------------------- #

    async def create_github_repo_record(
        self, github_url: str, branch: str = "main"
    ) -> RepositoryDocument:
        """Persist a pending RepositoryDocument for a GitHub URL."""
        try:
            owner, name = self._parse_github_url(github_url)
        except ValueError as exc:
            raise GitHubError(str(exc)) from exc

        doc = RepositoryDocument(
            name=name,
            owner=owner,
            source=RepoSource.GITHUB,
            github_url=github_url,
            status=RepoStatus.PENDING,
        )
        await doc.insert()
        logger.info("Created GitHub repo record: {owner}/{name} [{id}]", owner=owner, name=name, id=str(doc.id))
        return doc

    async def process_github_repo(self, repo_id: str) -> None:
        """
        Background task: clone → parse → chunk → embed → index.
        Implemented in detail in the ML pipeline module.
        """
        from app.ml.pipeline import run_ingestion_pipeline

        doc = await RepositoryDocument.get(repo_id)
        if doc is None:
            logger.error("process_github_repo: repo {id} not found", id=repo_id)
            return

        await self._set_status(doc, RepoStatus.PROCESSING)
        try:
            await run_ingestion_pipeline(doc)
            await self._set_status(doc, RepoStatus.READY, indexed_at=datetime.utcnow())
        except Exception as exc:
            logger.exception("Ingestion failed for repo {id}", id=repo_id)
            await self._set_status(doc, RepoStatus.FAILED, error=str(exc))

    # ---------------------------------------------------------------- #
    # ZIP Ingestion
    # ---------------------------------------------------------------- #

    async def create_zip_repo_record(self, file: UploadFile) -> RepositoryDocument:
        """Save the uploaded ZIP and create a pending RepositoryDocument."""
        upload_path = self.settings.UPLOAD_DIR / (file.filename or "upload.zip")

        try:
            async with aiofiles.open(upload_path, "wb") as f:
                content = await file.read()
                await f.write(content)
        except Exception as exc:
            raise UploadError(f"Failed to save uploaded file: {exc}") from exc

        name = Path(file.filename or "repo").stem
        doc = RepositoryDocument(
            name=name,
            source=RepoSource.ZIP,
            zip_filename=str(upload_path),
            status=RepoStatus.PENDING,
        )
        await doc.insert()
        logger.info("Created ZIP repo record: {name} [{id}]", name=name, id=str(doc.id))
        return doc

    async def process_zip_repo(self, repo_id: str) -> None:
        """Background task: extract ZIP → parse → chunk → embed → index."""
        from app.ml.pipeline import run_ingestion_pipeline

        doc = await RepositoryDocument.get(repo_id)
        if doc is None:
            logger.error("process_zip_repo: repo {id} not found", id=repo_id)
            return

        await self._set_status(doc, RepoStatus.PROCESSING)
        try:
            await run_ingestion_pipeline(doc)
            await self._set_status(doc, RepoStatus.READY, indexed_at=datetime.utcnow())
        except Exception as exc:
            logger.exception("ZIP ingestion failed for repo {id}", id=repo_id)
            await self._set_status(doc, RepoStatus.FAILED, error=str(exc))

    # ---------------------------------------------------------------- #
    # Deletion
    # ---------------------------------------------------------------- #

    async def delete_repo(self, repo_id: str) -> None:
        """Delete repo document, all its chunks, its FAISS index, and upload artefacts."""
        doc = await RepositoryDocument.get(repo_id)
        if doc is None:
            raise NotFoundError(f"Repository '{repo_id}' not found.")

        # Remove FAISS index directory
        if doc.faiss_index_path:
            index_dir = Path(doc.faiss_index_path)
            if index_dir.exists():
                shutil.rmtree(index_dir, ignore_errors=True)

        # Remove uploaded ZIP
        if doc.zip_filename:
            zip_path = Path(doc.zip_filename)
            if zip_path.exists():
                zip_path.unlink(missing_ok=True)

        # Delete MongoDB documents
        await ChunkDocument.find(ChunkDocument.repo_id == repo_id).delete()
        await doc.delete()

        logger.info("Deleted repository {id} and all associated data.", id=repo_id)

    # ---------------------------------------------------------------- #
    # Helpers
    # ---------------------------------------------------------------- #

    @staticmethod
    def _parse_github_url(url: str) -> tuple[str, str]:
        """Extract (owner, repo_name) from a GitHub URL."""
        import re

        match = re.match(r"https?://github\.com/([^/]+)/([^/]+?)(?:\.git)?/?$", url)
        if not match:
            raise ValueError(f"Invalid GitHub URL: {url}")
        return match.group(1), match.group(2)

    @staticmethod
    async def _set_status(
        doc: RepositoryDocument,
        status: RepoStatus,
        error: str | None = None,
        indexed_at: datetime | None = None,
    ) -> None:
        doc.status = status
        doc.updated_at = datetime.utcnow()
        if error:
            doc.error_message = error
        if indexed_at:
            doc.indexed_at = indexed_at
        await doc.save()
