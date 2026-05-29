# backend/app/ml/parsers/cpp_parser.py
"""
CodeSense — C / C++ Source Code Parser
Regex-based extraction of:
  - functions (free and member declarations/definitions)
  - classes and structs (with optional inheritance)
  - #include directives
  - namespace declarations
  - block and inline comments
  - Doxygen-style docstrings
"""

from __future__ import annotations

import re
from typing import Any, Dict, List, Optional


# ------------------------------------------------------------------ #
# Regex patterns
# ------------------------------------------------------------------ #

# Function definitions — matches return-type name(params) with optional
# cv-qualifiers.  Deliberately broad to cover templates and nested types.
_FUNC_DEF = re.compile(
    r"^(?P<modifiers>(?:(?:inline|static|virtual|explicit|constexpr|"
    r"friend|template\s*<[^>]*>|[\w:*&<>\[\],\s]+?)\s+)+)"
    r"(?P<name>[A-Za-z_][A-Za-z0-9_:~]*)\s*"
    r"\((?P<params>[^)]*)\)\s*"
    r"(?:const|override|final|noexcept(?:\([^)]*\))?)?\s*"
    r"(?:->[\w:*&<>\[\], ]+)?\s*[{;]",
    re.MULTILINE,
)

# Classes / structs
_CLASS_DECL = re.compile(
    r"(?:template\s*<[^>]*>\s*)?"
    r"(?P<kind>class|struct)\s+(?P<name>[A-Za-z_][A-Za-z0-9_]*)"
    r"(?:\s*:\s*(?P<bases>[^{;]+))?\s*\{",
    re.MULTILINE,
)

# #include
_INCLUDE = re.compile(
    r"^\s*#\s*include\s+(?P<delim>[\"<])(?P<header>[^\">;]+)[>\"]",
    re.MULTILINE,
)

# namespace
_NAMESPACE = re.compile(
    r"namespace\s+(?P<name>[A-Za-z_][A-Za-z0-9_:]*)\s*\{",
    re.MULTILINE,
)

# Doxygen / block comments
_BLOCK_COMMENT = re.compile(r"/\*(?P<body>.*?)\*/", re.DOTALL)

# Inline // comments
_INLINE_COMMENT = re.compile(r"//(?P<text>.+)$", re.MULTILINE)


# ------------------------------------------------------------------ #
# Public entry point
# ------------------------------------------------------------------ #

def parse_cpp(source: str, file_path: str = "", language: str = "cpp") -> Dict[str, Any]:
    """
    Parse a C/C++ source string and return structured metadata:
    {
        "language": "cpp" | "c",
        "file_path": ...,
        "functions": [...],
        "classes": [...],
        "imports": [...],      # #include directives
        "namespaces": [...],
        "comments": [...],
    }
    """
    return {
        "language": language,
        "file_path": file_path,
        "functions": _extract_functions(source),
        "classes": _extract_classes(source),
        "imports": _extract_includes(source),
        "namespaces": _extract_namespaces(source),
        "comments": _extract_comments(source),
    }


# ------------------------------------------------------------------ #
# Functions
# ------------------------------------------------------------------ #

def _extract_functions(source: str) -> List[Dict[str, Any]]:
    funcs = []
    seen: set = set()

    for m in _FUNC_DEF.finditer(source):
        name = m.group("name").strip()
        # Skip common false positives
        if name in {"if", "while", "for", "switch", "catch", "return"}:
            continue
        lineno = _offset_to_line(source, m.start())
        key = (name, lineno)
        if key in seen:
            continue
        seen.add(key)

        params_raw = m.group("params") or ""
        funcs.append(
            {
                "name": name,
                "lineno": lineno,
                "params": _parse_cpp_params(params_raw),
                "modifiers": _clean_modifiers(m.group("modifiers") or ""),
                "docstring": _preceding_doxygen(source, m.start()),
            }
        )

    return funcs


def _parse_cpp_params(params_raw: str) -> List[str]:
    """Return a list of parameter names (stripped of type info)."""
    if not params_raw.strip() or params_raw.strip() in {"void", ""}:
        return []
    result = []
    for param in params_raw.split(","):
        param = param.strip()
        if not param:
            continue
        # Last token is typically the name (may be absent for unnamed params)
        tokens = re.split(r"[\s*&]+", param)
        name = tokens[-1].strip().lstrip("*&").strip()
        if name and re.match(r"[A-Za-z_][A-Za-z0-9_]*", name):
            result.append(name)
    return result


def _clean_modifiers(raw: str) -> List[str]:
    return [t.strip() for t in raw.split() if t.strip() and t.strip() not in {"", "::"}]


# ------------------------------------------------------------------ #
# Classes / Structs
# ------------------------------------------------------------------ #

def _extract_classes(source: str) -> List[Dict[str, Any]]:
    classes = []
    for m in _CLASS_DECL.finditer(source):
        bases_raw = m.group("bases") or ""
        bases = [b.strip().lstrip("public ").lstrip("private ").lstrip("protected ").strip()
                 for b in bases_raw.split(",") if b.strip()]
        classes.append(
            {
                "kind": m.group("kind"),
                "name": m.group("name"),
                "lineno": _offset_to_line(source, m.start()),
                "bases": bases,
                "docstring": _preceding_doxygen(source, m.start()),
            }
        )
    return classes


# ------------------------------------------------------------------ #
# Includes
# ------------------------------------------------------------------ #

def _extract_includes(source: str) -> List[Dict[str, Any]]:
    return [
        {
            "type": "include",
            "header": m.group("header"),
            "system": m.group("delim") == "<",
            "lineno": _offset_to_line(source, m.start()),
        }
        for m in _INCLUDE.finditer(source)
    ]


# ------------------------------------------------------------------ #
# Namespaces
# ------------------------------------------------------------------ #

def _extract_namespaces(source: str) -> List[Dict[str, Any]]:
    return [
        {
            "name": m.group("name"),
            "lineno": _offset_to_line(source, m.start()),
        }
        for m in _NAMESPACE.finditer(source)
    ]


# ------------------------------------------------------------------ #
# Comments
# ------------------------------------------------------------------ #

def _extract_comments(source: str) -> List[Dict[str, Any]]:
    comments = []

    for m in _BLOCK_COMMENT.finditer(source):
        body = m.group("body")
        # Strip leading " * " from each line (Doxygen / JavaDoc style)
        text = re.sub(r"^\s*\*\s?", "", body, flags=re.MULTILINE).strip()
        comments.append(
            {
                "type": "block",
                "text": text,
                "lineno": _offset_to_line(source, m.start()),
            }
        )

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
# Helpers
# ------------------------------------------------------------------ #

def _offset_to_line(source: str, offset: int) -> int:
    return source[:offset].count("\n") + 1


def _preceding_doxygen(source: str, offset: int) -> Optional[str]:
    """Return the Doxygen/block comment immediately preceding *offset*."""
    snippet = source[:offset].rstrip()
    m = _BLOCK_COMMENT.search(snippet)
    if m and snippet.endswith("*/"):
        body = re.sub(r"^\s*\*\s?", "", m.group("body"), flags=re.MULTILINE).strip()
        return body
    return None
