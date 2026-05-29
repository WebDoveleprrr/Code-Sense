# backend/app/ml/zip_loader.py
"""
CodeSense — ZIP Repository Extractor
"""

from __future__ import annotations

import asyncio
import zipfile
from pathlib import Path

from app_logger import logger


async def extract_zip(zip_path: str, dest: Path) -> Path:
    """Extract a ZIP archive to `dest` in a thread executor."""

    def _extract():
        dest.mkdir(parents=True, exist_ok=True)
        with zipfile.ZipFile(zip_path, "r") as zf:
            zf.extractall(dest)

    await asyncio.get_event_loop().run_in_executor(None, _extract)
    logger.info("Extracted {zip} → {dest}", zip=zip_path, dest=str(dest))

    # If ZIP contains a single top-level folder, descend into it
    entries = list(dest.iterdir())
    if len(entries) == 1 and entries[0].is_dir():
        return entries[0]
    return dest
