# backend/app/ml/chunker.py
"""
Chunk dict schema{
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

# USED BY: pipeline.py --- DEPENDS ON: Output from repo_parser.py and metadata_generator.py

def chunk_files( #public entry point
    parsed_files: List[Dict[str, Any]], #Actual File Contents
    chunk_size: int = 512,
    overlap: int = 64,
    parsed_meta: Optional[List[Dict[str, Any]]] = None, #AST Metadata,Functions,Classes,Interfaces,Structs
) -> List[Dict[str, Any]]:
    #Decides how each file should be split into chunks based on the information extracted during parsing.
    meta_lookup: Dict[str, Dict] = {}
    if parsed_meta:
        for fm in parsed_meta:
            meta_lookup[fm["file_path"]] = fm

    all_chunks: List[Dict[str, Any]] = []

    for file in parsed_files:
        fp = file["file_path"]
        fm = meta_lookup.get(fp)
        #Determine which chunking strategy to use
        if fm and _has_structural_symbols(fm):
            chunks = _semantic_chunks(file, fm)
        else:
            chunks = _window_chunks(file, chunk_size, overlap)

        all_chunks.extend(chunks)

    return all_chunks


#Determine whether AST parsing found meaningful code structures: functions,classes,interfaces,structs
#If any exist: Use Semantic Chunking --- Otherwise: Use Window Chunking
def _has_structural_symbols(fm: Dict[str, Any]) -> bool:
    return bool(fm.get("functions") or fm.get("classes") or fm.get("interfaces") or fm.get("structs"))

#semnatic chunking --- Create one chunk per: Function,Class,Interface,Struct
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

        MAX_LINES_PER_SYMBOL = 200
        MAX_CHARS_PER_CHUNK = 2000
        #If exceeded: Function -> Sub-Chunks --- Example: lines 1-100,Lines 81-180,Lines 161-260 --- with overlap
        if len(chunk_lines) > MAX_LINES_PER_SYMBOL or len(content) > MAX_CHARS_PER_CHUNK:
            sub_chunk_size = 100
            sub_overlap = 20
            sub_idx = 0
            while sub_idx < len(chunk_lines):
                sub_end = min(sub_idx + sub_chunk_size, len(chunk_lines))
                sub_content = "\n".join(chunk_lines[sub_idx:sub_end])
                if len(sub_content) > MAX_CHARS_PER_CHUNK:
                    sub_content = sub_content[:MAX_CHARS_PER_CHUNK]
                #Every chunk produced looks like:
                chunks.append(
                    _make_chunk(
                        file_path=file_path,
                        language=language,
                        content=sub_content,
                        start_line=start + sub_idx,
                        end_line=start + sub_end - 1,
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
                sub_idx += max(1, sub_chunk_size - sub_overlap)
                chunk_index += 1
        else:
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
            chunk_index += 1

        covered_lines.update(range(start, end + 1)) #Already Chunked Lines(similar to vis array)

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

#Chunk files when no semantic structure exists --- Examples: yaml,json,sql,txt,env,config
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


#Create standardized chunk dictionary
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

#Some parsers provide start line but not  end line --- estimates end of symbol using indentation
def _estimate_end(lines: List[str], start_idx: int, kind: str) -> int:
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

#Used when processing uncovered lines
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
