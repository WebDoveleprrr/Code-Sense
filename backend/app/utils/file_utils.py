# backend/app/utils/file_utils.py
"""
CodeSense — File Utility Functions
Shared helpers used across the ingestion and parsing pipeline.
"""

from __future__ import annotations

import hashlib
import mimetypes
import re
from pathlib import Path
from typing import Optional


# ------------------------------------------------------------------ #
# Language detection
# ------------------------------------------------------------------ #

_EXT_TO_LANGUAGE = {
    ".py": "python",
    ".js": "javascript",
    ".mjs": "javascript",
    ".cjs": "javascript",
    ".jsx": "javascript",
    ".ts": "typescript",
    ".tsx": "typescript",
    ".c": "c",
    ".h": "c",
    ".cpp": "cpp",
    ".cc": "cpp",
    ".cxx": "cpp",
    ".hpp": "cpp",
    ".hxx": "cpp",
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
    ".yaml": "yaml",
    ".yml": "yaml",
    ".json": "json",
    ".toml": "toml",
    ".tf": "terraform",
    ".sql": "sql",
    ".md": "markdown",
    ".rst": "rst",
}


def detect_language(file_path: str | Path) -> Optional[str]:
    """Return the CodeSense language name for a file path, or None."""
    return _EXT_TO_LANGUAGE.get(Path(file_path).suffix.lower())


# ------------------------------------------------------------------ #
# Binary detection
# ------------------------------------------------------------------ #

def is_binary(raw_bytes: bytes, sample_size: int = 8192) -> bool:
    """
    Heuristic binary check: return True if the byte sample contains
    null bytes (common in compiled / binary files).
    """
    return b"\x00" in raw_bytes[:sample_size]


# ------------------------------------------------------------------ #
# Path normalisation
# ------------------------------------------------------------------ #

def normalise_path(path: str | Path) -> str:
    """Return a forward-slash, stripped relative path string."""
    return str(path).replace("\\", "/").strip("/")


# ------------------------------------------------------------------ #
# Content hashing
# ------------------------------------------------------------------ #

def sha256_hash(data: bytes) -> str:
    """Return the hex SHA-256 digest of *data*."""
    return hashlib.sha256(data).hexdigest()


# ------------------------------------------------------------------ #
# Token counting
# ------------------------------------------------------------------ #

def count_tokens(text: str) -> int:
    """
    Approximate token count using whitespace splitting.
    Fast enough for batch processing; not BPE-accurate.
    """
    return len(text.split())


def count_tokens_precise(text: str) -> int:
    """
    Slightly more accurate estimate: split on whitespace AND punctuation.
    Still faster than a full tiktoken pass.
    """
    tokens = re.findall(r"\w+|[^\w\s]", text)
    return len(tokens)


# ------------------------------------------------------------------ #
# Chunk preview
# ------------------------------------------------------------------ #

def truncate_content(content: str, max_chars: int = 500) -> str:
    """Return a truncated preview of content with ellipsis."""
    if len(content) <= max_chars:
        return content
    return content[:max_chars].rstrip() + " …"


# ------------------------------------------------------------------ #
# GitHub URL utilities
# ------------------------------------------------------------------ #

_GITHUB_URL_RE = re.compile(
    r"https?://github\.com/(?P<owner>[^/]+)/(?P<repo>[^/]+?)(?:\.git)?/?$"
)


def parse_github_url(url: str) -> tuple[str, str]:
    """
    Extract (owner, repo_name) from a GitHub HTTPS URL.
    Raises ValueError on mismatch.
    """
    m = _GITHUB_URL_RE.match(url.strip())
    if not m:
        raise ValueError(f"Cannot parse GitHub URL: {url!r}")
    return m.group("owner"), m.group("repo")


def build_github_raw_url(owner: str, repo: str, branch: str, file_path: str) -> str:
    """Build a raw.githubusercontent.com URL for a specific file."""
    return f"https://raw.githubusercontent.com/{owner}/{repo}/{branch}/{file_path}"
