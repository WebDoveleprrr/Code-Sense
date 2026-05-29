# backend/app/ml/parsers/__init__.py
"""
CodeSense — Parser Orchestrator
"""
import os
from typing import Any, Dict

from app.ml.parsers.python_parser import parse_python
from app.ml.parsers.js_ts_parser import parse_js_ts
from app.ml.parsers.cpp_parser import parse_cpp
from app_logger import logger

def parse_source(file_dict: Dict[str, Any]) -> Dict[str, Any]:
    """
    Dispatch parsing to the appropriate language parser based on the file extension or language field.
    Returns the AST structure matching the ParsedFileSchema.
    """
    path = file_dict.get("file_path", file_dict.get("path", ""))
    content = file_dict.get("content", "")
    language = file_dict.get("language", "").lower()

    ext = os.path.splitext(path)[1].lower()

    try:
        if language == "python" or ext in [".py"]:
            return parse_python(content, path)
        
        elif language in ["javascript", "typescript"] or ext in [".js", ".jsx", ".ts", ".tsx"]:
            # Provide language explicitly as parse_js_ts uses it
            lang = "typescript" if language == "typescript" or ext in [".ts", ".tsx"] else "javascript"
            return parse_js_ts(content, path, lang)
            
        elif language in ["cpp", "c", "c++"] or ext in [".cpp", ".cc", ".cxx", ".h", ".hpp", ".c"]:
            lang = "c" if ext == ".c" else "cpp"
            return parse_cpp(content, path, lang)
            
        else:
            # Fallback or unsupported
            return {
                "file_path": path,
                "language": language or ext.lstrip("."),
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
            "language": language or ext.lstrip("."),
            "line_count": len(content.splitlines()),
            "function_count": 0,
            "class_count": 0,
            "import_count": 0,
            "comment_count": 0,
            "functions": [],
            "classes": [],
            "imports": []
        }
