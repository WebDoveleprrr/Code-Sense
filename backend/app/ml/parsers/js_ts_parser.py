# backend/app/ml/parsers/js_ts_parser.py
"""
CodeSense — JavaScript / TypeScript Source Code Parser
Uses regex-based extraction (no Node.js runtime required) to pull:
  - functions (declarations, arrow functions, async variants)
  - classes (with optional extends/implements)
  - imports (ES module import / require)
  - JSDoc / inline comments
  - TypeScript interface & type alias stubs
"""

from __future__ import annotations

import re
from typing import Any, Dict, List, Optional


# ------------------------------------------------------------------ #
# Regex patterns
# ------------------------------------------------------------------ #

# Functions
_FUNC_DECL = re.compile(
    r"(?P<export>export\s+)?(?P<async>async\s+)?function\s*\*?\s+"
    r"(?P<name>[A-Za-z_$][A-Za-z0-9_$]*)\s*"
    r"(?P<generics><[^>]*>)?\s*\((?P<params>[^)]*)\)"
    r"(?:\s*:\s*(?P<ret>[A-Za-z_$<>\[\]|&, ]+))?",
    re.MULTILINE,
)

# Arrow functions assigned to const/let/var
_ARROW_FUNC = re.compile(
    r"(?:export\s+)?(?:const|let|var)\s+(?P<name>[A-Za-z_$][A-Za-z0-9_$]*)\s*"
    r"(?::\s*[A-Za-z_$<>\[\]|& ]+)?\s*=\s*(?P<async>async\s*)?\((?P<params>[^)]*)\)"
    r"\s*(?::\s*(?P<ret>[A-Za-z_$<>\[\]|&, ]+))?\s*=>",
    re.MULTILINE,
)

# Classes
_CLASS_DECL = re.compile(
    r"(?:export\s+)?(?:abstract\s+)?class\s+(?P<name>[A-Za-z_$][A-Za-z0-9_$]*)"
    r"(?P<generics><[^>]*>)?"
    r"(?:\s+extends\s+(?P<extends>[A-Za-z_$][A-Za-z0-9_$<>, ]*))?"
    r"(?:\s+implements\s+(?P<implements>[A-Za-z_$][A-Za-z0-9_$<>, ]*))?",
    re.MULTILINE,
)

# ES module imports
_ES_IMPORT = re.compile(
    r"^import\s+(?:type\s+)?(?P<clause>[^\"']+?)\s+from\s+[\"'](?P<module>[^\"']+)[\"']",
    re.MULTILINE,
)
_REQUIRE = re.compile(
    r"(?:const|let|var)\s+(?P<clause>\{[^}]+\}|[A-Za-z_$][A-Za-z0-9_$]*)\s*="
    r"\s*require\([\"'](?P<module>[^\"']+)[\"']\)",
    re.MULTILINE,
)

# JSDoc blocks
_JSDOC = re.compile(r"/\*\*(?P<body>.*?)\*/", re.DOTALL)

# Inline comments
_INLINE_COMMENT = re.compile(r"//(?P<text>.+)$", re.MULTILINE)

# TypeScript interfaces
_INTERFACE = re.compile(
    r"(?:export\s+)?interface\s+(?P<name>[A-Za-z_$][A-Za-z0-9_$]*)"
    r"(?P<generics><[^>]*>)?(?:\s+extends\s+(?P<extends>[^{]+))?",
    re.MULTILINE,
)

# TypeScript type aliases
_TYPE_ALIAS = re.compile(
    r"(?:export\s+)?type\s+(?P<name>[A-Za-z_$][A-Za-z0-9_$]*)"
    r"(?P<generics><[^>]*>)?\s*=",
    re.MULTILINE,
)


# ------------------------------------------------------------------ #
# Public entry point
# ------------------------------------------------------------------ #

def parse_js_ts(source: str, file_path: str = "", language: str = "javascript") -> Dict[str, Any]:
    """
    Parse a JS/TS source string and return structured metadata:
    {
        "language": "javascript" | "typescript",
        "file_path": ...,
        "functions": [...],
        "classes": [...],
        "imports": [...],
        "comments": [...],
        "interfaces": [...],   # TS only
        "type_aliases": [...], # TS only
    }
    """
    lines = source.splitlines()

    result: Dict[str, Any] = {
        "language": language,
        "file_path": file_path,
        "functions": _extract_functions(source, lines),
        "classes": _extract_classes(source, lines),
        "imports": _extract_imports(source),
        "comments": _extract_comments(source, lines),
    }

    if language == "typescript":
        result["interfaces"] = _extract_interfaces(source, lines)
        result["type_aliases"] = _extract_type_aliases(source, lines)

    return result


# ------------------------------------------------------------------ #
# Functions
# ------------------------------------------------------------------ #

def _extract_functions(source: str, lines: List[str]) -> List[Dict[str, Any]]:
    funcs = []

    for m in _FUNC_DECL.finditer(source):
        lineno = _offset_to_line(source, m.start())
        funcs.append(
            {
                "name": m.group("name"),
                "lineno": lineno,
                "is_async": bool(m.group("async")),
                "is_arrow": False,
                "params": _clean_params(m.group("params")),
                "return_type": (m.group("ret") or "").strip() or None,
                "docstring": _preceding_jsdoc(source, m.start()),
            }
        )

    for m in _ARROW_FUNC.finditer(source):
        lineno = _offset_to_line(source, m.start())
        funcs.append(
            {
                "name": m.group("name"),
                "lineno": lineno,
                "is_async": bool(m.group("async")),
                "is_arrow": True,
                "params": _clean_params(m.group("params")),
                "return_type": (m.group("ret") or "").strip() or None,
                "docstring": _preceding_jsdoc(source, m.start()),
            }
        )

    # De-duplicate by (name, lineno)
    seen = set()
    unique = []
    for f in sorted(funcs, key=lambda x: x["lineno"]):
        key = (f["name"], f["lineno"])
        if key not in seen:
            seen.add(key)
            unique.append(f)
    return unique


# ------------------------------------------------------------------ #
# Classes
# ------------------------------------------------------------------ #

def _extract_classes(source: str, lines: List[str]) -> List[Dict[str, Any]]:
    classes = []
    for m in _CLASS_DECL.finditer(source):
        lineno = _offset_to_line(source, m.start())
        classes.append(
            {
                "name": m.group("name"),
                "lineno": lineno,
                "extends": (m.group("extends") or "").strip() or None,
                "implements": _split_csv(m.group("implements") or ""),
                "docstring": _preceding_jsdoc(source, m.start()),
            }
        )
    return classes


# ------------------------------------------------------------------ #
# Imports
# ------------------------------------------------------------------ #

def _extract_imports(source: str) -> List[Dict[str, Any]]:
    imports = []

    for m in _ES_IMPORT.finditer(source):
        clause = m.group("clause").strip()
        names = _parse_import_clause(clause)
        imports.append(
            {
                "type": "es_import",
                "module": m.group("module"),
                "names": names,
                "lineno": _offset_to_line(source, m.start()),
            }
        )

    for m in _REQUIRE.finditer(source):
        clause = m.group("clause").strip()
        names = _parse_import_clause(clause) if clause.startswith("{") else [clause]
        imports.append(
            {
                "type": "require",
                "module": m.group("module"),
                "names": names,
                "lineno": _offset_to_line(source, m.start()),
            }
        )

    return imports


# ------------------------------------------------------------------ #
# Comments
# ------------------------------------------------------------------ #

def _extract_comments(source: str, lines: List[str]) -> List[Dict[str, Any]]:
    comments = []

    # JSDoc blocks
    for m in _JSDOC.finditer(source):
        text = re.sub(r"\s*\*\s*", " ", m.group("body")).strip()
        comments.append(
            {
                "type": "jsdoc",
                "text": text,
                "lineno": _offset_to_line(source, m.start()),
            }
        )

    # Inline // comments
    for m in _INLINE_COMMENT.finditer(source):
        comments.append(
            {
                "type": "inline",
                "text": m.group("text").strip(),
                "lineno": _offset_to_line(source, m.start()),
            }
        )

    return sorted(comments, key=lambda c: c["lineno"])


# ------------------------------------------------------------------ #
# TypeScript-specific
# ------------------------------------------------------------------ #

def _extract_interfaces(source: str, lines: List[str]) -> List[Dict[str, Any]]:
    return [
        {
            "name": m.group("name"),
            "extends": _split_csv(m.group("extends") or ""),
            "lineno": _offset_to_line(source, m.start()),
        }
        for m in _INTERFACE.finditer(source)
    ]


def _extract_type_aliases(source: str, lines: List[str]) -> List[Dict[str, Any]]:
    return [
        {
            "name": m.group("name"),
            "lineno": _offset_to_line(source, m.start()),
        }
        for m in _TYPE_ALIAS.finditer(source)
    ]


# ------------------------------------------------------------------ #
# Helpers
# ------------------------------------------------------------------ #

def _offset_to_line(source: str, offset: int) -> int:
    """Convert a character offset to a 1-based line number."""
    return source[:offset].count("\n") + 1


def _preceding_jsdoc(source: str, offset: int) -> Optional[str]:
    """Return the JSDoc comment immediately preceding *offset*, if any."""
    snippet = source[:offset].rstrip()
    m = _JSDOC.search(snippet)
    if m and snippet.endswith("*/"):
        text = re.sub(r"\s*\*\s*", " ", m.group("body")).strip()
        return text
    return None


def _clean_params(params_str: str) -> List[str]:
    """Split and clean a raw parameter string."""
    if not params_str.strip():
        return []
    # Remove type annotations (everything after : up to the next , or end)
    return [p.strip().split(":")[0].split("=")[0].strip() for p in params_str.split(",") if p.strip()]


def _split_csv(text: str) -> List[str]:
    return [s.strip() for s in text.split(",") if s.strip()]


def _parse_import_clause(clause: str) -> List[str]:
    """Parse `{ foo, bar as baz }` or `* as ns` or bare default name."""
    clause = clause.strip()
    if clause.startswith("{") and clause.endswith("}"):
        inner = clause[1:-1]
        return [part.split("as")[0].strip() for part in inner.split(",") if part.strip()]
    if clause.startswith("*"):
        return [clause]
    # Could be `DefaultExport, { named }` combo
    parts = clause.split(",", 1)
    names = [parts[0].strip()]
    if len(parts) > 1:
        names += _parse_import_clause(parts[1].strip())
    return names
