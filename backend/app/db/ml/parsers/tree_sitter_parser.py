# backend/app/ml/parsers/tree_sitter_parser.py
"""
CodeSense — Tree-Sitter AST Parser
Parses repositories using Tree-Sitter to extract classes, functions, methods,
imports, exports, interfaces, and structs.
"""

from typing import Any, Dict, List, Optional
import os

from tree_sitter import Language, Parser #language --- Represents one programming language grammar
import tree_sitter_python #Provides Python grammar
import tree_sitter_javascript 
import tree_sitter_typescript
import tree_sitter_cpp

#Load Tree-sitter grammar
def load_language(lang_module, name: str) -> Language:
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

#Public API --- Parse the source code string using tree-sitter and return parsed symbols --- same schema as all parsers
#Parser maintains state --- Safer to create a fresh parser per file --- Grammar is reused
def parse_with_tree_sitter(source: str, file_path: str, language: str) -> Dict[str, Any]:
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
        "namespaces": [],
        "type_aliases": [],
    }

    if not parser:
        # Fallback empty structures
        return result

    tree = parser.parse(bytes(source, "utf8"))
    root_node = tree.root_node

    symbols: List[Dict[str, Any]] = []

    #access metadata
    def get_node_text(node) -> str:
        return source[node.start_byte:node.end_byte]

    def get_docstring(start_line: int) -> Optional[str]:
        for c in reversed(result["comments"]):
            if c["end_lineno"] == start_line - 1 or c["end_lineno"] == start_line - 2:
                if c["text"].startswith("/**") or c["text"].startswith("/*"):
                    return c["text"]
        return None

    #visit every node in AST tree
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
                
                module_name = get_node_text(node)
                src_node = node.child_by_field_name("source") or node.child_by_field_name("module")
                if src_node:
                    module_name = get_node_text(src_node).strip("'\"")
                    
                symbol = {
                    "name": module_name,
                    "type": "import",
                    "file": file_path,
                    "start_line": start,
                    "end_line": end,
                    "parent_symbol": parent_symbol,
                }
                result["imports"].append({
                    "type": "import",
                    "module": module_name,
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
                    
                    extends = None
                    implements = []
                    heritage = node.child_by_field_name("heritage") or next((c for c in node.children if c.type == "class_heritage"), None)
                    if heritage:
                        for clause in heritage.children:
                            if clause.type == "extends_clause":
                                ext_node = next((c for c in clause.children if c.type in ("identifier", "type_identifier")), None)
                                if ext_node:
                                    extends = get_node_text(ext_node)
                            elif clause.type == "implements_clause":
                                for c in clause.children:
                                    if c.type in ("type_identifier", "identifier"):
                                        implements.append(get_node_text(c))
                    
                    result["classes"].append({
                        "name": name,
                        "lineno": start,
                        "end_lineno": end,
                        "extends": extends,
                        "implements": implements,
                        "docstring": get_docstring(start)
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
                params = []
                formal_params = next((c for c in node.children if c.type == "formal_parameters"), None)
                if formal_params:
                    for c in formal_params.children:
                        if c.type in ("identifier", "required_parameter", "optional_parameter"):
                            params.append(get_node_text(c).split(":")[0].strip())
                
                is_async = "async" in get_node_text(node).split("{")[0]
                is_arrow = node_type == "arrow_function"

                result["functions"].append({
                    "name": name,
                    "lineno": start,
                    "end_lineno": end,
                    "is_async": is_async,
                    "is_arrow": is_arrow,
                    "params": params,
                    "docstring": get_docstring(start)
                })
                symbols.append(symbol)

            elif node_type == "import_statement":
                start = node.start_point[0] + 1
                end = node.end_point[0] + 1
                
                module_name = get_node_text(node)
                src_node = node.child_by_field_name("source")
                if src_node:
                    module_name = get_node_text(src_node).strip("'\"")
                    
                symbol = {
                    "name": module_name,
                    "type": "import",
                    "file": file_path,
                    "start_line": start,
                    "end_line": end,
                    "parent_symbol": parent_symbol,
                }
                result["imports"].append({
                    "type": "import",
                    "module": module_name,
                    "lineno": start,
                })
                symbols.append(symbol)

            elif node_type == "call_expression":
                func_node = node.child_by_field_name("function")
                if func_node and get_node_text(func_node) == "require":
                    args_node = node.child_by_field_name("arguments")
                    if args_node and len(args_node.children) > 1:
                        for arg in args_node.children:
                            if arg.type == "string":
                                module_name = get_node_text(arg).strip("'\"")
                                start = node.start_point[0] + 1
                                end = node.end_point[0] + 1
                                symbol = {
                                    "name": module_name,
                                    "type": "require",
                                    "file": file_path,
                                    "start_line": start,
                                    "end_line": end,
                                    "parent_symbol": parent_symbol,
                                }
                                result["imports"].append({
                                    "type": "require",
                                    "module": module_name,
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

            elif node_type == "type_alias_declaration":
                name_node = node.child_by_field_name("name")
                if name_node:
                    name = get_node_text(name_node)
                    start = node.start_point[0] + 1
                    end = node.end_point[0] + 1
                    symbol = {
                        "name": name,
                        "type": "type_alias",
                        "file": file_path,
                        "start_line": start,
                        "end_line": end,
                        "parent_symbol": parent_symbol,
                    }
                    result["type_aliases"].append({
                        "name": name,
                        "lineno": start,
                        "end_lineno": end,
                    })
                    symbols.append(symbol)

        # C/C++ parsing logic
        elif language in ("cpp", "c"):
            if node_type == "namespace_definition":
                name_node = node.child_by_field_name("name")
                if name_node:
                    name = get_node_text(name_node)
                    start = node.start_point[0] + 1
                    end = node.end_point[0] + 1
                    symbol = {
                        "name": name,
                        "type": "namespace",
                        "file": file_path,
                        "start_line": start,
                        "end_line": end,
                        "parent_symbol": parent_symbol,
                    }
                    result["namespaces"].append({
                        "name": name,
                        "lineno": start,
                        "end_lineno": end,
                    })
                    symbols.append(symbol)
                    current_parent = name

            elif node_type in ("class_specifier", "struct_specifier"):
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
                    
                    bases = []
                    base_clause = next((c for c in node.children if c.type == "base_class_clause"), None)
                    if base_clause:
                        for c in base_clause.children:
                            if c.type in ("type_identifier", "identifier"):
                                bases.append(get_node_text(c))
                                
                    if sym_type == "class":
                        result["classes"].append({
                            "name": name,
                            "lineno": start,
                            "end_lineno": end,
                            "bases": bases,
                            "docstring": get_docstring(start)
                        })
                    else:
                        result["structs"].append({
                            "name": name,
                            "lineno": start,
                            "end_lineno": end,
                            "bases": bases,
                            "docstring": get_docstring(start)
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
                params = []
                param_list = None
                if declarator:
                    curr = declarator
                    while curr.child_by_field_name("declarator"):
                        curr = curr.child_by_field_name("declarator")
                    param_list = next((c for c in curr.children if c.type == "parameter_list"), None)
                if param_list:
                    for c in param_list.children:
                        if c.type == "parameter_declaration":
                            params.append(get_node_text(c))
                            
                result["functions"].append({
                    "name": name,
                    "lineno": start,
                    "end_lineno": end,
                    "params": params,
                    "docstring": get_docstring(start)
                })
                symbols.append(symbol)

            elif node_type == "preproc_include":
                start = node.start_point[0] + 1
                end = node.end_point[0] + 1
                
                module_name = get_node_text(node)
                path_node = node.child_by_field_name("path")
                if path_node:
                    module_name = get_node_text(path_node)
                    
                symbol = {
                    "name": module_name,
                    "type": "import",
                    "file": file_path,
                    "start_line": start,
                    "end_line": end,
                    "parent_symbol": parent_symbol,
                }
                result["imports"].append({
                    "type": "import",
                    "module": module_name,
                    "lineno": start,
                })
                symbols.append(symbol)

        # Walk children recursively
        for child in node.children:
            walk(child, parent_symbol=current_parent, in_class=in_class)

    walk(root_node)
    result["symbols"] = symbols
    return result
