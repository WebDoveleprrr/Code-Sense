# backend/app/ml/metadata_generator.py
from __future__ import annotations

from typing import Any, Dict, List, Optional

"""
ParsedFileMetadata structure:{ This schema represents one file
    "file_path": str,
    "language": str,
    "line_count": int,
    "function_count": int,
    "class_count": int,
    "import_count": int,
    "comment_count": int,
    "functions": [...],   # from language parser
    "classes": [...],
    "imports": [...],
    "comments": [...],
    "docstring": str | None,    # module/file-level docstring (Python)
    "interfaces": [...],        # TypeScript only
    "type_aliases": [...],      # TypeScript only
    "namespaces": [...],        # C++ only
}

RepositoryMetadata structure:{ Represents the whole repository
    "total_files": int,
    "total_lines": int,
    "total_functions": int,
    "total_classes": int,
    "total_imports": int,
    "language_breakdown": {lang: file_count},
    "files": [ParsedFileMetadata, ...],
}
"""

#Merge repo_parser Output(repo_parser.py) + AST Parser Output into one standard dictionary.
def build_file_metadata(
    file_dict: Dict[str, Any],
    parsed: Dict[str, Any],
) -> Dict[str, Any]:
    functions: List = parsed.get("functions") or []
    classes: List = parsed.get("classes") or []
    imports: List = parsed.get("imports") or []
    comments: List = parsed.get("comments") or []

    metadata: Dict[str, Any] = {
        "file_path": file_dict.get("file_path", ""),
        "language": file_dict.get("language", parsed.get("language", "unknown")),
        "line_count": file_dict.get("line_count", 0),
        # Aggregate counts
        "function_count": len(functions),
        "class_count": len(classes),
        "import_count": len(imports),
        "comment_count": len(comments),
        # Detailed lists
        "functions": functions,
        "classes": classes,
        "imports": imports,
        "comments": comments,
        # Optional top-level fields
        "docstring": parsed.get("module_docstring"),          # Python
        "interfaces": parsed.get("interfaces", []),           # TypeScript
        "type_aliases": parsed.get("type_aliases", []),       # TypeScript
        "namespaces": parsed.get("namespaces", []),           # C++
    }
    return metadata

#Convert many files into one repository summary
def build_repo_metadata(
    parsed_files_meta: List[Dict[str, Any]],
) -> Dict[str, Any]:
    language_breakdown: Dict[str, int] = {}
    total_lines = 0
    total_functions = 0
    total_classes = 0
    total_imports = 0

    for fm in parsed_files_meta:
        lang = fm.get("language") or "unknown"
        language_breakdown[lang] = language_breakdown.get(lang, 0) + 1
        total_lines += fm.get("line_count", 0)
        total_functions += fm.get("function_count", 0)
        total_classes += fm.get("class_count", 0)
        total_imports += fm.get("import_count", 0)

    return {
        "total_files": len(parsed_files_meta),
        "total_lines": total_lines,
        "total_functions": total_functions,
        "total_classes": total_classes,
        "total_imports": total_imports,
        "language_breakdown": language_breakdown,
        # Embed per-file summaries (without heavy content fields)
        "files": [_file_summary(fm) for fm in parsed_files_meta],
    }

#Instead of embedding everything inside RepositoryMetadata only store summary.
def _file_summary(fm: Dict[str, Any]) -> Dict[str, Any]:
    return {
        "file_path": fm["file_path"],
        "language": fm["language"],
        "line_count": fm["line_count"],
        "function_count": fm["function_count"],
        "class_count": fm["class_count"],
        "import_count": fm["import_count"],
        "comment_count": fm["comment_count"],
        "imports": fm.get("imports", []),
    }

#Convert structured metadata back into plain text
def extract_symbol_text(file_meta: Dict[str, Any]) -> str:
    parts: List[str] = []

    funcs = [f.get("name", "") for f in file_meta.get("functions", [])]
    if funcs:
        parts.append("Functions: " + ", ".join(funcs))

    classes = file_meta.get("classes", [])
    if classes:
        class_strs = []
        for cls in classes:
            name = cls.get("name", "")
            bases = cls.get("bases") or cls.get("extends")
            if bases:
                bases_str = ", ".join(bases) if isinstance(bases, list) else bases
                class_strs.append(f"{name} (bases: {bases_str})")
            else:
                class_strs.append(name)
        parts.append("Classes: " + ", ".join(class_strs))

    imports = file_meta.get("imports", [])
    if imports:
        modules = list({imp.get("module", "") for imp in imports if imp.get("module")}) #set removes duplicates
        parts.append("Imports: " + ", ".join(modules[:20]))  # cap at 20 for imports

    interfaces = file_meta.get("interfaces", [])
    if interfaces:
        parts.append("Interfaces: " + ", ".join(i.get("name", "") for i in interfaces))

    docstring = file_meta.get("docstring")
    if docstring:
        parts.append("Docstring: " + docstring[:300]) #only first 300 char

    return "\n".join(parts)
