# tests/test_parsing_pipeline.py
"""
CodeSense — Parsing Pipeline Tests
Tests for: Python parser, JS/TS parser, C++ parser, chunker,
           metadata generator, and repo_parser traversal helpers.
"""

from __future__ import annotations

import textwrap
from pathlib import Path
from typing import Any, Dict


# ------------------------------------------------------------------ #
# Python parser
# ------------------------------------------------------------------ #

def test_python_parser_functions():
    from app.ml.parsers.python_parser import parse_python

    source = textwrap.dedent(
        '''
        """Module docstring."""

        import os
        from pathlib import Path

        CONST = 42

        def greet(name: str, loud: bool = False) -> str:
            """Return a greeting."""
            return name.upper() if loud else name

        async def fetch(url: str) -> bytes:
            pass

        class Greeter:
            """A greeting class."""

            def __init__(self, prefix: str = "Hello") -> None:
                self.prefix = prefix

            def say(self, name: str) -> str:
                return f"{self.prefix}, {name}"
        '''
    )

    result = parse_python(source, "greet.py")

    assert result["language"] == "python"
    assert result["module_docstring"] == "Module docstring."

    func_names = {f["name"] for f in result["functions"]}
    assert "greet" in func_names
    assert "fetch" in func_names
    # Methods are NOT in top-level functions
    assert "say" not in func_names
    assert "__init__" not in func_names

    fetch_fn = next(f for f in result["functions"] if f["name"] == "fetch")
    assert fetch_fn["is_async"] is True

    greet_fn = next(f for f in result["functions"] if f["name"] == "greet")
    assert greet_fn["docstring"] == "Return a greeting."
    arg_names = [a["name"] for a in greet_fn["args"]]
    assert "name" in arg_names
    assert "loud" in arg_names

    cls = next(c for c in result["classes"] if c["name"] == "Greeter")
    assert cls["docstring"] == "A greeting class."
    method_names = {m["name"] for m in cls["methods"]}
    assert "__init__" in method_names
    assert "say" in method_names

    import_modules = {i["module"] for i in result["imports"]}
    assert "os" in import_modules
    assert "pathlib" in import_modules


def test_python_parser_syntax_error():
    from app.ml.parsers.python_parser import parse_python

    result = parse_python("def broken(", "bad.py")
    assert result["functions"] == []
    assert result["classes"] == []


# ------------------------------------------------------------------ #
# JS / TS parser
# ------------------------------------------------------------------ #

def test_js_parser_functions():
    from app.ml.parsers.js_ts_parser import parse_js_ts

    source = textwrap.dedent(
        """
        import React from 'react';
        import { useState, useEffect } from 'react';
        const fs = require('fs');

        /**
         * Formats a name.
         * @param {string} name
         */
        function formatName(name) {
            return name.trim();
        }

        const double = (x) => x * 2;

        async function fetchData(url) {
            const res = await fetch(url);
            return res.json();
        }

        class Animal {
            constructor(name) {
                this.name = name;
            }
        }
        """
    )

    result = parse_js_ts(source, "app.js", "javascript")

    func_names = {f["name"] for f in result["functions"]}
    assert "formatName" in func_names
    assert "double" in func_names
    assert "fetchData" in func_names

    fetch = next(f for f in result["functions"] if f["name"] == "fetchData")
    assert fetch["is_async"] is True

    assert any(c["name"] == "Animal" for c in result["classes"])

    modules = {i["module"] for i in result["imports"]}
    assert "react" in modules
    assert "fs" in modules


def test_ts_parser_interfaces():
    from app.ml.parsers.js_ts_parser import parse_js_ts

    source = textwrap.dedent(
        """
        export interface User {
            id: number;
            name: string;
        }

        export type UserId = number;

        export function getUser(id: UserId): User {
            return { id, name: 'Alice' };
        }
        """
    )

    result = parse_js_ts(source, "types.ts", "typescript")

    interface_names = {i["name"] for i in result.get("interfaces", [])}
    assert "User" in interface_names

    type_names = {t["name"] for t in result.get("type_aliases", [])}
    assert "UserId" in type_names

    func_names = {f["name"] for f in result["functions"]}
    assert "getUser" in func_names


# ------------------------------------------------------------------ #
# C++ parser
# ------------------------------------------------------------------ #

def test_cpp_parser_basic():
    from app.ml.parsers.cpp_parser import parse_cpp

    source = textwrap.dedent(
        """
        #include <iostream>
        #include "mylib.h"

        namespace utils {

        /**
         * Add two integers.
         */
        int add(int a, int b) {
            return a + b;
        }

        class Vector3 : public BaseVector {
        public:
            float x, y, z;
            Vector3(float x, float y, float z);
        };

        } // namespace utils
        """
    )

    result = parse_cpp(source, "math.cpp", "cpp")

    assert any(i["header"] == "iostream" and i["system"] for i in result["imports"])
    assert any(i["header"] == "mylib.h" and not i["system"] for i in result["imports"])

    assert any(n["name"] == "utils" for n in result["namespaces"])

    class_names = {c["name"] for c in result["classes"]}
    assert "Vector3" in class_names

    vec = next(c for c in result["classes"] if c["name"] == "Vector3")
    assert "BaseVector" in vec["bases"]


# ------------------------------------------------------------------ #
# Parser dispatcher
# ------------------------------------------------------------------ #

def test_parse_source_dispatch():
    from app.ml.parsers import parse_source

    py_file = {"file_path": "x.py", "language": "python", "content": "def foo(): pass\n"}
    result = parse_source(py_file)
    assert result["language"] == "python"
    assert any(f["name"] == "foo" for f in result["functions"])

    js_file = {"file_path": "x.js", "language": "javascript", "content": "function bar() {}\n"}
    result = parse_source(js_file)
    assert result["language"] == "javascript"

    yaml_file = {"file_path": "x.yaml", "language": "yaml", "content": "key: value\n"}
    result = parse_source(yaml_file)
    assert result["language"] == "yaml"
    assert result["functions"] == []


# ------------------------------------------------------------------ #
# Metadata generator
# ------------------------------------------------------------------ #

def test_build_file_metadata():
    from app.ml.metadata_generator import build_file_metadata

    file_dict = {"file_path": "foo.py", "language": "python", "content": "x=1\n", "line_count": 1}
    parsed = {
        "language": "python",
        "file_path": "foo.py",
        "functions": [{"name": "f", "lineno": 1}],
        "classes": [],
        "imports": [{"module": "os"}],
        "comments": [],
        "module_docstring": "A module.",
    }

    meta = build_file_metadata(file_dict, parsed)

    assert meta["function_count"] == 1
    assert meta["class_count"] == 0
    assert meta["import_count"] == 1
    assert meta["docstring"] == "A module."


def test_build_repo_metadata():
    from app.ml.metadata_generator import build_repo_metadata

    files = [
        {"file_path": "a.py", "language": "python", "line_count": 100,
         "function_count": 5, "class_count": 2, "import_count": 3, "comment_count": 10},
        {"file_path": "b.js", "language": "javascript", "line_count": 50,
         "function_count": 3, "class_count": 0, "import_count": 2, "comment_count": 5},
    ]

    meta = build_repo_metadata(files)

    assert meta["total_files"] == 2
    assert meta["total_lines"] == 150
    assert meta["total_functions"] == 8
    assert meta["language_breakdown"] == {"python": 1, "javascript": 1}


# ------------------------------------------------------------------ #
# Chunker
# ------------------------------------------------------------------ #

def test_window_chunker_basic():
    from app.ml.chunker import chunk_files

    content = "\n".join([f"line {i}" for i in range(1, 201)])
    files = [{"file_path": "big.py", "language": "python", "content": content, "line_count": 200}]
    chunks = chunk_files(files, chunk_size=50, overlap=10)

    assert len(chunks) > 1
    for c in chunks:
        assert c["file_path"] == "big.py"
        assert c["start_line"] >= 1
        assert c["end_line"] <= 200
        assert c["token_count"] >= 0


def test_semantic_chunker_respects_boundaries():
    from app.ml.chunker import chunk_files

    source = textwrap.dedent(
        """
        import os

        def alpha():
            x = 1
            y = 2
            return x + y

        def beta():
            return 42

        class Gamma:
            pass
        """
    )

    files = [{"file_path": "s.py", "language": "python", "content": source, "line_count": source.count("\n")}]
    meta = [
        {
            "file_path": "s.py",
            "language": "python",
            "functions": [
                {"name": "alpha", "lineno": 3, "end_lineno": 6},
                {"name": "beta", "lineno": 8, "end_lineno": 9},
            ],
            "classes": [{"name": "Gamma", "lineno": 11, "end_lineno": 12}],
        }
    ]

    chunks = chunk_files(files, parsed_meta=meta)

    types = {c["chunk_type"] for c in chunks}
    assert "function" in types
    assert "class" in types

    names = {c["symbol_name"] for c in chunks if c["symbol_name"]}
    assert "alpha" in names
    assert "beta" in names
    assert "Gamma" in names
