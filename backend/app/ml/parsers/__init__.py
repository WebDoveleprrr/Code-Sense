# backend/app/ml/parsers/__init__.py
"""
CodeSense — Parser Orchestrator
"""
import os
from typing import Any, Dict

from app.ml.parsers.python_parser import parse_python
from app.ml.parsers.js_ts_parser import parse_js_ts
from app.ml.parsers.cpp_parser import parse_cpp
from app.ml.parsers.tree_sitter_parser import parse_with_tree_sitter
from app_logger import logger

def parse_source(file_dict: Dict[str, Any]) -> Dict[str, Any]:
    """
    Dispatch parsing to the appropriate language parser based on the file extension or language field.
    Uses tree-sitter as primary, falls back to legacy AST/regex parsers if needed.
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

    # Try tree-sitter first
    try:
        ts_result = parse_with_tree_sitter(content, path, lang)
        # Verify if it extracted any symbols/structure
        if ts_result.get("classes") or ts_result.get("functions") or ts_result.get("imports") or ts_result.get("structs"):
            ts_result["line_count"] = len(content.splitlines())
            ts_result["function_count"] = len(ts_result.get("functions", []))
            ts_result["class_count"] = len(ts_result.get("classes", []))
            ts_result["import_count"] = len(ts_result.get("imports", []))
            ts_result["comment_count"] = len(ts_result.get("comments", []))
            return ts_result
    except Exception as e:
        logger.warning(f"Tree-sitter parse failed for {path}, falling back: {e}")

    # Fallback to legacy parsers
    try:
        if lang == "python" or ext in [".py"]:
            return parse_python(content, path)
        
        elif lang in ["javascript", "typescript"] or ext in [".js", ".jsx", ".ts", ".tsx"]:
            ts_lang = "typescript" if lang == "typescript" or ext in [".ts", ".tsx"] else "javascript"
            return parse_js_ts(content, path, ts_lang)
            
        elif lang in ["cpp", "c", "c++"] or ext in [".cpp", ".cc", ".cxx", ".h", ".hpp", ".c"]:
            cpp_lang = "c" if ext == ".c" else "cpp"
            return parse_cpp(content, path, cpp_lang)
            
        else:
            # Fallback or unsupported
            return {
                "file_path": path,
                "language": lang or ext.lstrip("."),
                "line_count": len(content.splitlines()),
                "function_count": 0,
                "class_count": 0,
                "import_count": 0,
                "comment_count": 0,
                "functions": [],
                "classes": [],
                "imports": []
            }
    except Exception as e:
        logger.error(f"Error parsing {path}: {e}")
        return {
            "file_path": path,
            "language": lang or ext.lstrip("."),
            "line_count": len(content.splitlines()),
            "function_count": 0,
            "class_count": 0,
            "import_count": 0,
            "comment_count": 0,
            "functions": [],
            "classes": [],
            "imports": []
        }

