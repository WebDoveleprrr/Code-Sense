# backend/app/ml/repo_parser.py
"""
CodeSense — Repository File Parser (v2)
Walks a directory, filters source files, decodes content, and
returns structured file dicts ready for the chunking pipeline.

Improvements over v1
--------------------
* Binary-file detection (skip non-text files even if extension matches)
* .gitignore-aware skip patterns (best-effort)
* File size cap to avoid embedding megabyte-scale generated files
* Returns richer dict including sha256 content hash for dedup
"""

from __future__ import annotations

import asyncio
import hashlib
from pathlib import Path
from typing import Dict, List, Optional

import chardet
from app_logger import logger


# ------------------------------------------------------------------ #
# Language extension map
# ------------------------------------------------------------------ #

SUPPORTED_EXTENSIONS: Dict[str, str] = {
    # Python
    ".py": "python",
    # JavaScript
    ".js": "javascript",
    ".jsx": "javascript",
    ".mjs": "javascript",
    ".cjs": "javascript",
    # TypeScript
    ".ts": "typescript",
    ".tsx": "typescript",
    # C / C++
    ".c": "c",
    ".h": "c",
    ".cpp": "cpp",
    ".cc": "cpp",
    ".cxx": "cpp",
    ".hpp": "cpp",
    ".hxx": "cpp",
    # Other languages (parsed as plain text / fallback chunker)
    ".java": "java",
    ".go": "go",
    ".rs": "rust",
    ".cs": "csharp",
    ".rb": "ruby",
    ".php": "php",
    ".swift": "swift",
    ".kt": "kotlin",
    ".scala": "scala",
    ".sh": "bash",
    ".bash": "bash",
    # Config / data (line-window chunking only)
    ".yaml": "yaml",
    ".yml": "yaml",
    ".json": "json",
    ".toml": "toml",
    ".tf": "terraform",
    ".sql": "sql",
    ".md": "markdown",
    ".rst": "rst",
    ".env": "env",
}

# Directories always skipped during traversal
SKIP_DIRS: set = {
    ".git",
    ".github",
    "__pycache__",
    ".cache",
    "node_modules",
    ".venv",
    "venv",
    "env",
    "dist",
    "build",
    ".next",
    ".nuxt",
    "target",
    "out",
    "vendor",
    "third_party",
    ".idea",
    ".vscode",
    "coverage",
    ".pytest_cache",
    ".mypy_cache",
    "*.egg-info",
    "htmlcov",
}

# Individual file name patterns to skip
SKIP_FILES: set = {
    "package-lock.json",
    "yarn.lock",
    "pnpm-lock.yaml",
    "Pipfile.lock",
    "poetry.lock",
    "Cargo.lock",
    ".DS_Store",
    "Thumbs.db",
}

# Substring matches for file skipping
SKIP_EXTENSIONS = {
    ".min.js", ".min.css", ".map",
    ".png", ".jpg", ".jpeg", ".gif", ".svg", ".ico",
    ".pdf", ".zip", ".tar", ".gz", ".exe", ".dll"
}

# Maximum single-file size (bytes)
MAX_FILE_SIZE_BYTES: int = 1024 * 1024  # 1 MB


# ------------------------------------------------------------------ #
# Public API
# ------------------------------------------------------------------ #

async def parse_repository(repo_dir: Path) -> List[Dict]:
    """
    Async entry point: walk *repo_dir* and return a list of file dicts:
    {
        "file_path":  str,   # relative to repo_dir
        "language":   str,
        "size_bytes": int,
    }
    Runs the blocking filesystem walk in a thread executor.
    Does NOT load file contents.
    """
    loop = asyncio.get_event_loop()
    results = await loop.run_in_executor(None, _walk_sync, repo_dir)
    logger.info(
        "parse_repository: {n} files collected from {dir}",
        n=len(results),
        dir=str(repo_dir),
    )
    return results

def read_and_decode_file(path: Path) -> Optional[str]:
    """
    Lazily reads file content, detects binary files, skips invalid files,
    and returns decoded text. Returns None if the file is binary or unreadable.
    """
    try:
        size_bytes = path.stat().st_size
        if size_bytes > MAX_FILE_SIZE_BYTES or size_bytes == 0:
            return None
        
        raw = path.read_bytes()
    except OSError:
        return None

    # Binary sniff (null bytes in first 8KB → skip)
    if b"\x00" in raw[:8192]:
        return None

    enc_result = chardet.detect(raw[:4096])
    encoding = enc_result.get("encoding") or "utf-8"
    try:
        content = raw.decode(encoding, errors="replace")
    except (LookupError, ValueError):
        content = raw.decode("utf-8", errors="replace")

    return content


# ------------------------------------------------------------------ #
# Synchronous walk (runs in thread executor)
# ------------------------------------------------------------------ #

def _walk_sync(repo_dir: Path) -> List[Dict]:
    gitignore_patterns = _load_gitignore(repo_dir)
    results: List[Dict] = []

    for path in sorted(repo_dir.rglob("*")):
        # --- Directory checks ---
        if not path.is_file():
            continue
        if _should_skip_path(path, repo_dir, gitignore_patterns):
            continue

        # --- Extension check ---
        ext = path.suffix.lower()
        language = SUPPORTED_EXTENSIONS.get(ext)
        if language is None:
            continue

        # --- File name check ---
        if path.name in SKIP_FILES:
            continue
            
        if any(path.name.lower().endswith(ext) for ext in SKIP_EXTENSIONS):
            continue

        # --- Size check ---
        try:
            size_bytes = path.stat().st_size
        except OSError:
            continue
        if size_bytes > MAX_FILE_SIZE_BYTES:
            logger.debug("Skipping large file ({size}B): {p}", size=size_bytes, p=str(path))
            continue
        if size_bytes == 0:
            continue

        results.append(
            {
                "file_path": str(path.relative_to(repo_dir)),
                "language": language,
                "size_bytes": size_bytes,
            }
        )

    return results


# ------------------------------------------------------------------ #
# Path filtering helpers
# ------------------------------------------------------------------ #

def _should_skip_path(path: Path, repo_dir: Path, gitignore_patterns: List[str]) -> bool:
    """Return True if the path should be excluded from parsing."""
    try:
        parts = path.relative_to(repo_dir).parts
    except ValueError:
        return True

    for part in parts:
        if part.startswith(".") and part not in {".env"}:
            return True
        if part in SKIP_DIRS:
            return True

    rel_str = str(path.relative_to(repo_dir))
    for pattern in gitignore_patterns:
        if _gitignore_match(pattern, rel_str, parts):
            return True

    return False


def _gitignore_match(pattern: str, rel_str: str, parts: tuple) -> bool:
    """Very lightweight .gitignore pattern matcher (no globbing library dep)."""
    import fnmatch

    pattern = pattern.lstrip("/")
    if "/" not in pattern:
        # Match against any path component
        return any(fnmatch.fnmatch(p, pattern) for p in parts)
    # Directory prefix match
    return fnmatch.fnmatch(rel_str, pattern) or fnmatch.fnmatch(rel_str, pattern + "/*")


def _load_gitignore(repo_dir: Path) -> List[str]:
    """Parse a top-level .gitignore and return non-comment, non-empty patterns."""
    gitignore = repo_dir / ".gitignore"
    if not gitignore.is_file():
        return []
    try:
        text = gitignore.read_text(encoding="utf-8", errors="replace")
        patterns = [
            line.strip()
            for line in text.splitlines()
            if line.strip() and not line.startswith("#")
        ]
        return patterns
    except OSError:
        return []
