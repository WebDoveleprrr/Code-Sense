# backend/app/ml/chunker.py
"""
CodeSense — Code Chunker (v2)
Splits parsed file content into overlapping chunks with two strategies:

  1. SEMANTIC chunking  — respects function/class boundaries extracted
     by the language parsers (preferred for Python, JS/TS, C++).
  2. LINE-WINDOW chunking — sliding window fallback for files where
     no structural boundaries were detected (config files, SQL, etc.).

Chunk dict schema
-----------------
{
    "file_path":    str,
    "language":     str | None,
    "content":      str,
    "start_line":   int,          # 1-based
    "end_line":     int,
    "chunk_index":  int,          # 0-based within file
    "token_count":  int,
    "chunk_type":   "function" | "class" | "window" | "symbol_header",
    "symbol_name":  str | None,   # populated for function/class chunks
    "metadata":     dict,         # extra structured fields from parser
}
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional, Tuple


# ------------------------------------------------------------------ #
# Public API
# ------------------------------------------------------------------ #

def chunk_files(
    parsed_files: List[Dict[str, Any]],
    chunk_size: int = 512,
    overlap: int = 64,
    parsed_meta: Optional[List[Dict[str, Any]]] = None,
) -> List[Dict[str, Any]]:
    """
    Parameters
    ----------
    parsed_files : list[dict]
        Output from repo_parser.parse_repository.
        Each dict: {file_path, language, content, line_count}
    chunk_size : int
        Maximum lines per chunk (window fallback).
    overlap : int
        Overlap lines between consecutive window chunks.
    parsed_meta : list[dict] | None
        Optional list of ParsedFileMetadata dicts (from metadata_generator).
        When provided, semantic chunking is used for structured languages.

    Returns
    -------
    list[dict]
        Flat list of chunk dicts (schema above).
    """
    # Build a file_path -> metadata lookup if available
    meta_lookup: Dict[str, Dict] = {}
    if parsed_meta:
        for fm in parsed_meta:
            meta_lookup[fm["file_path"]] = fm

    all_chunks: List[Dict[str, Any]] = []

    for file in parsed_files:
        fp = file["file_path"]
        fm = meta_lookup.get(fp)

        if fm and _has_structural_symbols(fm):
            chunks = _semantic_chunks(file, fm)
        else:
            chunks = _window_chunks(file, chunk_size, overlap)

        all_chunks.extend(chunks)

    return all_chunks


# ------------------------------------------------------------------ #
# Semantic chunking
# ------------------------------------------------------------------ #

def _has_structural_symbols(fm: Dict[str, Any]) -> bool:
    return bool(fm.get("functions") or fm.get("classes") or fm.get("interfaces") or fm.get("structs"))


def _semantic_chunks(
    file: Dict[str, Any],
    fm: Dict[str, Any],
) -> List[Dict[str, Any]]:
    """
    Emit one chunk per top-level function/class/interface/struct boundary found in
    ParsedFileMetadata, then a final "remainder" window chunk for any
    lines not covered by a symbol boundary.
    """
    lines = file["content"].splitlines()
    language = file["language"]
    file_path = file["file_path"]
    chunks: List[Dict[str, Any]] = []
    chunk_index = 0

    # Collect (start_line, end_line, name, kind, metadata) boundaries
    boundaries: List[Tuple[int, int, str, str, Dict]] = []

    for func in fm.get("functions", []):
        start = func.get("lineno", 1)
        end = func.get("end_lineno") or _estimate_end(lines, start - 1, "function")
        boundaries.append((start, end, func.get("name", ""), "function", func))

    for cls in fm.get("classes", []):
        start = cls.get("lineno", 1)
        end = cls.get("end_lineno") or _estimate_end(lines, start - 1, "class")
        boundaries.append((start, end, cls.get("name", ""), "class", cls))

    for interface in fm.get("interfaces", []):
        start = interface.get("lineno", 1)
        end = interface.get("end_lineno") or _estimate_end(lines, start - 1, "interface")
        boundaries.append((start, end, interface.get("name", ""), "interface", interface))

    for struct in fm.get("structs", []):
        start = struct.get("lineno", 1)
        end = struct.get("end_lineno") or _estimate_end(lines, start - 1, "struct")
        boundaries.append((start, end, struct.get("name", ""), "struct", struct))

    # Sort by start line, deduplicate overlapping
    boundaries.sort(key=lambda b: b[0])

    covered_lines: set = set()

    for start, end, name, kind, meta in boundaries:
        # Clamp to file length
        start = max(1, start)
        end = min(len(lines), end or len(lines))

        chunk_lines = lines[start - 1 : end]
        content = "\n".join(chunk_lines)

        if not content.strip():
            continue

        chunks.append(
            _make_chunk(
                file_path=file_path,
                language=language,
                content=content,
                start_line=start,
                end_line=end,
                chunk_index=chunk_index,
                chunk_type=kind,
                symbol_name=name,
                metadata={
                    "args": meta.get("args") or meta.get("params"),
                    "decorators": meta.get("decorators"),
                    "docstring": meta.get("docstring"),
                    "bases": meta.get("bases"),
                    "is_async": meta.get("is_async"),
                },
            )
        )
        covered_lines.update(range(start, end + 1))
        chunk_index += 1

    # Emit uncovered lines as window chunks
    uncovered = [i for i in range(1, len(lines) + 1) if i not in covered_lines]
    if uncovered:
        # Collapse consecutive runs
        runs = _consecutive_runs(uncovered)
        for run_start, run_end in runs:
            content = "\n".join(lines[run_start - 1 : run_end])
            if not content.strip():
                continue
            chunks.append(
                _make_chunk(
                    file_path=file_path,
                    language=language,
                    content=content,
                    start_line=run_start,
                    end_line=run_end,
                    chunk_index=chunk_index,
                    chunk_type="window",
                )
            )
            chunk_index += 1

    # If no semantic chunks were emitted at all, fall back to windows
    if not chunks:
        return _window_chunks(file, chunk_size=512, overlap=64)

    return chunks


# ------------------------------------------------------------------ #
# Line-window chunking (fallback)
# ------------------------------------------------------------------ #

def _window_chunks(
    file: Dict[str, Any],
    chunk_size: int,
    overlap: int,
) -> List[Dict[str, Any]]:
    lines = file["content"].splitlines()
    total = len(lines)
    file_path = file["file_path"]
    language = file["language"]
    chunks: List[Dict[str, Any]] = []

    step = max(1, chunk_size - overlap)
    idx = 0
    chunk_index = 0

    while idx < total:
        end = min(idx + chunk_size, total)
        content = "\n".join(lines[idx:end])

        chunks.append(
            _make_chunk(
                file_path=file_path,
                language=language,
                content=content,
                start_line=idx + 1,
                end_line=end,
                chunk_index=chunk_index,
                chunk_type="window",
            )
        )
        idx += step
        chunk_index += 1

    return chunks


# ------------------------------------------------------------------ #
# Helpers
# ------------------------------------------------------------------ #

def _make_chunk(
    file_path: str,
    language: Optional[str],
    content: str,
    start_line: int,
    end_line: int,
    chunk_index: int,
    chunk_type: str = "window",
    symbol_name: Optional[str] = None,
    metadata: Optional[Dict] = None,
) -> Dict[str, Any]:
    return {
        "file_path": file_path,
        "language": language,
        "content": content,
        "start_line": start_line,
        "end_line": end_line,
        "chunk_index": chunk_index,
        "token_count": len(content.split()),
        "chunk_type": chunk_type,
        "symbol_name": symbol_name,
        "metadata": metadata or {},
    }


def _estimate_end(lines: List[str], start_idx: int, kind: str) -> int:
    """
    Rough heuristic for languages/parsers that don't emit end_lineno.
    Walks forward until the indentation level returns to the baseline.
    """
    if start_idx >= len(lines):
        return start_idx + 1

    baseline_indent = len(lines[start_idx]) - len(lines[start_idx].lstrip())
    for i in range(start_idx + 1, len(lines)):
        line = lines[i]
        if not line.strip():
            continue
        indent = len(line) - len(line.lstrip())
        if indent <= baseline_indent and i > start_idx + 1:
            return i  # 1-based: the line BEFORE this one

    return len(lines)


def _consecutive_runs(line_numbers: List[int]) -> List[Tuple[int, int]]:
    """Collapse a sorted list of ints into (start, end) inclusive ranges."""
    if not line_numbers:
        return []
    runs: List[Tuple[int, int]] = []
    start = prev = line_numbers[0]
    for n in line_numbers[1:]:
        if n == prev + 1:
            prev = n
        else:
            runs.append((start, prev))
            start = prev = n
    runs.append((start, prev))
    return runs
