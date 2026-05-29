# backend/app/ml/code_reader.py
"""
CodeSense — Raw Code Reader
Reads specific lines from source files on disk or falls back to chunk contents.
"""

from typing import Optional
from pathlib import Path
from app.core.config import get_settings
from app.models.repository import RepositoryDocument
from app.core.exceptions import NotFoundError

async def read_lines(
    repo: RepositoryDocument,
    file_path: str,
    start_line: int,
    end_line: int
) -> str:
    """Reads specific lines from a file."""
    settings = get_settings()
    repo_dir = settings.UPLOAD_DIR / str(repo.id)
    full_path = repo_dir / file_path
    
    if not full_path.exists():
        # Fallback to DB: find all chunks for this file
        from app.models.chunk import ChunkDocument
        chunks = await ChunkDocument.find(
            ChunkDocument.repo_id == str(repo.id)
        ).to_list()
        
        # Filter manually since file_path might be a suffix (e.g. main.py vs src/main.py)
        # and we want any chunks that overlap the requested range
        matching_chunks = []
        for c in chunks:
            if file_path in c.file_path:
                # Check overlap
                if c.start_line <= end_line and c.end_line >= start_line:
                    matching_chunks.append(c)
                    
        if matching_chunks:
            matching_chunks.sort(key=lambda x: x.start_line)
            # Just return the combined text of the chunks that matched
            return "\n".join([c.content for c in matching_chunks])
            
        raise NotFoundError(f"File not found on disk or DB: {file_path}")

    try:
        lines = full_path.read_text(encoding="utf-8", errors="replace").splitlines()
        start_idx = max(0, start_line - 1)
        end_idx = min(len(lines), end_line)
        return "\n".join(lines[start_idx:end_idx])
    except Exception as e:
        raise NotFoundError(f"Could not read file {file_path}: {e}")
