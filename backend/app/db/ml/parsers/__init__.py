# backend/app/ml/parsers/__init__.py
"""
CodeSense — Parser Orchestrator
"""
import os
from typing import Any, Dict

from app.db.ml.parsers.python_parser import parse_python
from app.db.ml.parsers.tree_sitter_parser import parse_with_tree_sitter
from app_logger import logger

def parse_source(file_dict: Dict[str, Any]) -> Dict[str, Any]:
    """
    Dispatch parsing to the appropriate language parser based on the file extension or language field.
    Uses tree-sitter for C++/JS/TS, and built-in AST parser for Python.
    """
    path = file_dict.get("file_path", file_dict.get("path", ""))
    content = file_dict.get("content", "")
    language = file_dict.get("language", "").lower()

    ext = os.path.splitext(path)[1].lower()
    lang = language
    if not lang:
        if ext in [".py"]:
            lang = "python"
        elif ext in [".js", ".jsx", ".ts", ".tsx"]:
            lang = "typescript" if ext in [".ts", ".tsx"] else "javascript"
        elif ext in [".cpp", ".cc", ".cxx", ".h", ".hpp", ".c"]:
            lang = "cpp"
        else:
            lang = ext.lstrip(".")

    empty_fallback = {
        "file_path": path,
        "language": lang or ext.lstrip("."),
        "line_count": len(content.splitlines()),
        "function_count": 0,
        "class_count": 0,
        "import_count": 0,
        "comment_count": 0,
        "functions": [],
        "classes": [],
        "imports": [],
        "comments": [],
    }

    try:
        if lang == "python" or ext in [".py"]:
            return parse_python(content, path)
        
        elif lang in ["javascript", "typescript", "cpp", "c", "c++"] or ext in [".js", ".jsx", ".ts", ".tsx", ".cpp", ".cc", ".cxx", ".h", ".hpp", ".c"]:
            logger.info(f"Parsing {path} with Tree-sitter...")
            ts_result = parse_with_tree_sitter(content, path, lang)
            ts_result["line_count"] = len(content.splitlines())
            ts_result["function_count"] = len(ts_result.get("functions", []))
            ts_result["class_count"] = len(ts_result.get("classes", []))
            ts_result["import_count"] = len(ts_result.get("imports", []))
            ts_result["comment_count"] = len(ts_result.get("comments", []))
            logger.info(f"Tree-sitter parsing completed for {path}.")
            return ts_result
        
        else:
            # Unsupported language
            return empty_fallback
    except Exception as e:
        logger.error(f"Tree-sitter parsing failed for {path}: {e}")
        return empty_fallback

