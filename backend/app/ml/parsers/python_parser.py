# backend/app/ml/parsers/python_parser.py
"""
CodeSense — Python Source Code Parser
Uses the built-in `ast` module to extract:
  - functions (with args, return type, decorators, docstrings)
  - classes (with bases, methods, class docstring)
  - imports (module-level import / from-import statements)
  - inline comments
  - module-level docstring
"""

from __future__ import annotations

import ast
import re
import tokenize
from io import StringIO
from typing import Any, Dict, List, Optional


# ------------------------------------------------------------------ #
# Public entry point
# ------------------------------------------------------------------ #

def parse_python(source: str, file_path: str = "") -> Dict[str, Any]:
    """
    Parse a Python source string and return a structured metadata dict:
    {
        "language": "python",
        "file_path": ...,
        "module_docstring": ...,
        "functions": [...],
        "classes": [...],
        "imports": [...],
        "comments": [...],
    }
    Returns an empty structure if the source cannot be parsed.
    """
    result: Dict[str, Any] = {
        "language": "python",
        "file_path": file_path,
        "module_docstring": None,
        "functions": [],
        "classes": [],
        "imports": [],
        "comments": [],
    }

    try:
        tree = ast.parse(source)
    except SyntaxError:
        return result

    result["module_docstring"] = ast.get_docstring(tree)
    result["functions"] = _extract_functions(tree)
    result["classes"] = _extract_classes(tree)
    result["imports"] = _extract_imports(tree)
    result["comments"] = _extract_comments(source)
    return result


# ------------------------------------------------------------------ #
# Functions
# ------------------------------------------------------------------ #

def _extract_functions(tree: ast.Module) -> List[Dict[str, Any]]:
    funcs = []
    for node in ast.walk(tree):
        if not isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            continue
        # Skip methods — captured inside _extract_classes
        if _is_method(node, tree):
            continue
        funcs.append(_function_info(node))
    return funcs


def _function_info(node: ast.FunctionDef | ast.AsyncFunctionDef) -> Dict[str, Any]:
    return {
        "name": node.name,
        "lineno": node.lineno,
        "end_lineno": getattr(node, "end_lineno", None),
        "is_async": isinstance(node, ast.AsyncFunctionDef),
        "args": _extract_args(node.args),
        "returns": _annotation_to_str(node.returns),
        "decorators": [_annotation_to_str(d) for d in node.decorator_list],
        "docstring": ast.get_docstring(node),
    }


def _extract_args(args: ast.arguments) -> List[Dict[str, Any]]:
    result = []
    all_args = args.posonlyargs + args.args + args.kwonlyargs
    if args.vararg:
        all_args.append(args.vararg)
    if args.kwarg:
        all_args.append(args.kwarg)

    defaults_map: Dict[str, Any] = {}
    # Positional defaults are right-aligned against args list
    offset = len(args.args) - len(args.defaults)
    for i, default in enumerate(args.defaults):
        arg_name = args.args[offset + i].arg
        defaults_map[arg_name] = ast.unparse(default)
    for arg, default in zip(args.kwonlyargs, args.kw_defaults):
        if default is not None:
            defaults_map[arg.arg] = ast.unparse(default)

    for arg in all_args:
        result.append(
            {
                "name": arg.arg,
                "annotation": _annotation_to_str(arg.annotation),
                "default": defaults_map.get(arg.arg),
            }
        )
    return result


# ------------------------------------------------------------------ #
# Classes
# ------------------------------------------------------------------ #

def _extract_classes(tree: ast.Module) -> List[Dict[str, Any]]:
    classes = []
    for node in ast.walk(tree):
        if not isinstance(node, ast.ClassDef):
            continue
        methods = []
        for item in node.body:
            if isinstance(item, (ast.FunctionDef, ast.AsyncFunctionDef)):
                methods.append(_function_info(item))

        classes.append(
            {
                "name": node.name,
                "lineno": node.lineno,
                "end_lineno": getattr(node, "end_lineno", None),
                "bases": [_annotation_to_str(b) for b in node.bases],
                "decorators": [_annotation_to_str(d) for d in node.decorator_list],
                "docstring": ast.get_docstring(node),
                "methods": methods,
            }
        )
    return classes


# ------------------------------------------------------------------ #
# Imports
# ------------------------------------------------------------------ #

def _extract_imports(tree: ast.Module) -> List[Dict[str, Any]]:
    imports = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                imports.append(
                    {
                        "type": "import",
                        "module": alias.name,
                        "alias": alias.asname,
                        "names": [],
                        "lineno": node.lineno,
                    }
                )
        elif isinstance(node, ast.ImportFrom):
            imports.append(
                {
                    "type": "from_import",
                    "module": node.module or "",
                    "alias": None,
                    "names": [a.name for a in node.names],
                    "lineno": node.lineno,
                }
            )
    return imports


# ------------------------------------------------------------------ #
# Comments (via tokenizer — ast strips them)
# ------------------------------------------------------------------ #

def _extract_comments(source: str) -> List[Dict[str, Any]]:
    comments = []
    try:
        tokens = tokenize.generate_tokens(StringIO(source).readline)
        for tok_type, tok_string, tok_start, _, _ in tokens:
            if tok_type == tokenize.COMMENT:
                comments.append(
                    {
                        "text": tok_string.lstrip("#").strip(),
                        "lineno": tok_start[0],
                    }
                )
    except tokenize.TokenError:
        pass
    return comments


# ------------------------------------------------------------------ #
# Helpers
# ------------------------------------------------------------------ #

def _annotation_to_str(node: Optional[ast.expr]) -> Optional[str]:
    if node is None:
        return None
    try:
        return ast.unparse(node)
    except Exception:
        return None


def _is_method(
    func: ast.FunctionDef | ast.AsyncFunctionDef,
    tree: ast.Module,
) -> bool:
    """Return True if *func* is a method of any class in *tree*."""
    for node in ast.walk(tree):
        if isinstance(node, ast.ClassDef):
            for item in node.body:
                if item is func:
                    return True
    return False
