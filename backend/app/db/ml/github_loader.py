# backend/app/ml/github_loader.py
"""
CodeSense — GitHub Repository Cloner
Uses GitPython to clone a repository to a local temp directory.
"""

from __future__ import annotations

import asyncio
import shutil
from pathlib import Path

from app_logger import logger


async def clone_repo(github_url: str, dest: Path) -> Path:
    """
    Async wrapper: clones `github_url` into `dest` and returns the path.
    Runs git clone in a thread to avoid blocking the event loop.
    """
    from app.core.config import get_settings

    settings = get_settings()

    if dest.exists():
        shutil.rmtree(dest)
    dest.mkdir(parents=True, exist_ok=True)

    # Inject token into URL for private repos
    authed_url = github_url
    if settings.GITHUB_TOKEN:
        authed_url = github_url.replace(
            "https://github.com",
            f"https://{settings.GITHUB_TOKEN}@github.com",
        )

    def _clone():
        import git

        git.Repo.clone_from(authed_url, dest, depth=1)

    await asyncio.get_event_loop().run_in_executor(None, _clone)
    logger.info("Cloned {url} → {dest}", url=github_url, dest=str(dest))
    return dest
