# backend/app/ml/parsers/tree_sitter_parser.py
"""
CodeSense — Tree-Sitter AST Parser
Parses repositories using Tree-Sitter to extract classes, functions, methods,
imports, exports, interfaces, and structs.
"""

from typing import Any, Dict, List, Optional
import os

from tree_sitter import Language, Parser
import tree_sitter_python
import tree_sitter_javascript
import tree_sitter_typescript
import tree_sitter_cpp

def load_language(lang_module, name: str) -> Language:
    """Version-agnostic loader for tree-sitter Language."""
    lang_func = getattr(lang_module, "language", None)
    if not lang_func:
        if name == "typescript":
            lang_func = getattr(lang_module, "language_typescript", None)
        elif name == "tsx":
            lang_func = getattr(lang_module, "language_tsx", None)
            
    if not lang_func:
        raise AttributeError(f"Module {lang_module} has no language function")
        
    capsule = lang_func()
    try:
        # Try new API (0.22.x+ / 0.25.x+): expects a single argument (capsule or raw pointer)
        return Language(capsule)
    except TypeError:
        # Fallback path if capsule is not accepted directly or name is required
        if isinstance(capsule, int):
            ptr = capsule
        else:
            import ctypes
            ctypes.pythonapi.PyCapsule_GetPointer.restype = ctypes.c_void_p
            ctypes.pythonapi.PyCapsule_GetPointer.argtypes = [ctypes.py_object, ctypes.c_char_p]
            ptr = ctypes.pythonapi.PyCapsule_GetPointer(capsule, b"tree_sitter.Language")
            
        try:
            # Try new API (0.22.x+ / 0.23.x) with resolved pointer
            return Language(ptr)
        except TypeError:
            # Fall back to old API (0.21.x): expects (pointer, name)
            return Language(ptr, name)

# Initialize Languages
PY_LANG = load_language(tree_sitter_python, "python")
JS_LANG = load_language(tree_sitter_javascript, "javascript")
TS_LANG = load_language(tree_sitter_typescript, "typescript")
CPP_LANG = load_language(tree_sitter_cpp, "cpp")

def get_parser_for_language(lang_name: str) -> Optional[Parser]:
    parser = Parser()
    lang_name = lang_name.lower()
    
    lang_obj = None
    if lang_name == "python":
        lang_obj = PY_LANG
    elif lang_name == "javascript":
        lang_obj = JS_LANG
    elif lang_name == "typescript":
        lang_obj = TS_LANG
    elif lang_name in ("cpp", "c++", "c"):
        lang_obj = CPP_LANG

    if lang_obj:
        if hasattr(parser, "set_language"):
            parser.set_language(lang_obj)
        else:
            parser.language = lang_obj
        return parser
    return None

def parse_with_tree_sitter(source: str, file_path: str, language: str) -> Dict[str, Any]:
    """
    Parse the source code string using tree-sitter and return parsed symbols.
    """
    parser = get_parser_for_language(language)
    result = {
        "language": language,
        "file_path": file_path,
        "classes": [],
        "functions": [],
        "imports": [],
        "exports": [],
        "interfaces": [],
        "structs": [],
        "comments": [],
    }

    if not parser:
        # Fallback empty structures
        return result

    tree = parser.parse(bytes(source, "utf8"))
    root_node = tree.root_node

    symbols: List[Dict[str, Any]] = []

    def get_node_text(node) -> str:
        return source[node.start_byte:node.end_byte]

    def walk(node, parent_symbol: Optional[str] = None, in_class: bool = False):
        node_type = node.type
        current_parent = parent_symbol

        # Extract comments and docstrings
        if node_type in ("comment", "line_comment", "block_comment"):
            start = node.start_point[0] + 1
            end = node.end_point[0] + 1
            result["comments"].append({
                "text": get_node_text(node).strip(),
                "lineno": start,
                "end_lineno": end,
            })

        # Python parsing logic
        if language == "python":
            if node_type == "expression_statement" and node.children and node.children[0].type == "string":
                start = node.start_point[0] + 1
                end = node.end_point[0] + 1
                result["comments"].append({
                    "text": get_node_text(node.children[0]).strip(),
                    "lineno": start,
                    "end_lineno": end,
                    "type": "docstring"
                })
            elif node_type == "class_definition":
                name_node = node.child_by_field_name("name")
                if name_node:
                    name = get_node_text(name_node)
                    start = node.start_point[0] + 1
                    end = node.end_point[0] + 1
                    symbol = {
                        "name": name,
                        "type": "class",
                        "file": file_path,
                        "start_line": start,
                        "end_line": end,
                        "parent_symbol": parent_symbol,
                    }
                    result["classes"].append({
                        "name": name,
                        "lineno": start,
                        "end_lineno": end,
                        "methods": []
                    })
                    symbols.append(symbol)
                    current_parent = name
                    in_class = True

            elif node_type == "function_definition":
                name_node = node.child_by_field_name("name")
                if name_node:
                    name = get_node_text(name_node)
                    start = node.start_point[0] + 1
                    end = node.end_point[0] + 1
                    sym_type = "method" if in_class else "function"
                    symbol = {
                        "name": name,
                        "type": sym_type,
                        "file": file_path,
                        "start_line": start,
                        "end_line": end,
                        "parent_symbol": parent_symbol,
                    }
                    result["functions"].append({
                        "name": name,
                        "lineno": start,
                        "end_lineno": end,
                        "is_async": False,
                    })
                    symbols.append(symbol)

            elif node_type in ("import_statement", "import_from_statement"):
                start = node.start_point[0] + 1
                end = node.end_point[0] + 1
                symbol = {
                    "name": get_node_text(node).strip(),
                    "type": "import",
                    "file": file_path,
                    "start_line": start,
                    "end_line": end,
                    "parent_symbol": parent_symbol,
                }
                result["imports"].append({
                    "type": "import",
                    "module": get_node_text(node),
                    "lineno": start,
                })
                symbols.append(symbol)

        # JS/TS parsing logic
        elif language in ("javascript", "typescript"):
            if node_type in ("class_declaration", "class"):
                name_node = node.child_by_field_name("name")
                if name_node:
                    name = get_node_text(name_node)
                    start = node.start_point[0] + 1
                    end = node.end_point[0] + 1
                    symbol = {
                        "name": name,
                        "type": "class",
                        "file": file_path,
                        "start_line": start,
                        "end_line": end,
                        "parent_symbol": parent_symbol,
                    }
                    result["classes"].append({
                        "name": name,
                        "lineno": start,
                        "end_lineno": end,
                    })
                    symbols.append(symbol)
                    current_parent = name
                    in_class = True

            elif node_type in ("function_declaration", "function", "arrow_function", "method_definition"):
                name_node = node.child_by_field_name("name")
                name = get_node_text(name_node) if name_node else "anonymous"
                if node_type == "arrow_function":
                    # Try to get the variable name it is assigned to
                    parent = node.parent
                    if parent and parent.type == "variable_declarator":
                        id_node = parent.child_by_field_name("name")
                        if id_node:
                            name = get_node_text(id_node)
                start = node.start_point[0] + 1
                end = node.end_point[0] + 1
                sym_type = "method" if (in_class or node_type == "method_definition") else "function"
                symbol = {
                    "name": name,
                    "type": sym_type,
                    "file": file_path,
                    "start_line": start,
                    "end_line": end,
                    "parent_symbol": parent_symbol,
                }
                result["functions"].append({
                    "name": name,
                    "lineno": start,
                    "end_lineno": end,
                    "is_async": False,
                })
                symbols.append(symbol)

            elif node_type == "import_statement":
                start = node.start_point[0] + 1
                end = node.end_point[0] + 1
                symbol = {
                    "name": get_node_text(node).strip(),
                    "type": "import",
                    "file": file_path,
                    "start_line": start,
                    "end_line": end,
                    "parent_symbol": parent_symbol,
                }
                result["imports"].append({
                    "type": "import",
                    "module": get_node_text(node),
                    "lineno": start,
                })
                symbols.append(symbol)

            elif node_type == "export_statement" or node_type.startswith("export_"):
                start = node.start_point[0] + 1
                end = node.end_point[0] + 1
                symbol = {
                    "name": get_node_text(node).strip(),
                    "type": "export",
                    "file": file_path,
                    "start_line": start,
                    "end_line": end,
                    "parent_symbol": parent_symbol,
                }
                result["exports"].append({
                    "type": "export",
                    "name": get_node_text(node),
                    "lineno": start,
                })
                symbols.append(symbol)

            elif node_type == "interface_declaration":
                name_node = node.child_by_field_name("name")
                if name_node:
                    name = get_node_text(name_node)
                    start = node.start_point[0] + 1
                    end = node.end_point[0] + 1
                    symbol = {
                        "name": name,
                        "type": "interface",
                        "file": file_path,
                        "start_line": start,
                        "end_line": end,
                        "parent_symbol": parent_symbol,
                    }
                    result["interfaces"].append({
                        "name": name,
                        "lineno": start,
                        "end_lineno": end,
                    })
                    symbols.append(symbol)

        # C/C++ parsing logic
        elif language in ("cpp", "c"):
            if node_type in ("class_specifier", "struct_specifier"):
                name_node = node.child_by_field_name("name")
                if name_node:
                    name = get_node_text(name_node)
                    start = node.start_point[0] + 1
                    end = node.end_point[0] + 1
                    sym_type = "class" if node_type == "class_specifier" else "struct"
                    symbol = {
                        "name": name,
                        "type": sym_type,
                        "file": file_path,
                        "start_line": start,
                        "end_line": end,
                        "parent_symbol": parent_symbol,
                    }
                    if sym_type == "class":
                        result["classes"].append({
                            "name": name,
                            "lineno": start,
                            "end_lineno": end,
                        })
                    else:
                        result["structs"].append({
                            "name": name,
                            "lineno": start,
                            "end_lineno": end,
                        })
                    symbols.append(symbol)
                    current_parent = name
                    in_class = True

            elif node_type == "function_definition":
                # Find declarator name
                declarator = node.child_by_field_name("declarator")
                name = "unknown"
                if declarator:
                    # Traversal for nested declarators (e.g. pointer/reference return types)
                    curr = declarator
                    while curr.child_by_field_name("declarator"):
                        curr = curr.child_by_field_name("declarator")
                    name_node = curr.child_by_field_name("declarator") or curr
                    name = get_node_text(name_node)
                start = node.start_point[0] + 1
                end = node.end_point[0] + 1
                sym_type = "method" if in_class else "function"
                symbol = {
                    "name": name,
                    "type": sym_type,
                    "file": file_path,
                    "start_line": start,
                    "end_line": end,
                    "parent_symbol": parent_symbol,
                }
                result["functions"].append({
                    "name": name,
                    "lineno": start,
                    "end_lineno": end,
                })
                symbols.append(symbol)

            elif node_type == "preproc_include":
                start = node.start_point[0] + 1
                end = node.end_point[0] + 1
                symbol = {
                    "name": get_node_text(node).strip(),
                    "type": "import",
                    "file": file_path,
                    "start_line": start,
                    "end_line": end,
                    "parent_symbol": parent_symbol,
                }
                result["imports"].append({
                    "type": "import",
                    "module": get_node_text(node),
                    "lineno": start,
                })
                symbols.append(symbol)

        # Walk children recursively
        for child in node.children:
            walk(child, parent_symbol=current_parent, in_class=in_class)

    walk(root_node)
    result["symbols"] = symbols
    return result
