# backend/tests/test_tree_sitter_parser.py
import pytest
from app.ml.parsers.tree_sitter_parser import parse_with_tree_sitter

def test_parse_python():
    source = """
import os
import sys

class DatabaseManager:
    def __init__(self, url):
        self.url = url
    
    def connect(self):
        pass

def global_helper():
    return 42
"""
    result = parse_with_tree_sitter(source, "test.py", "python")
    
    # Assertions
    assert result["language"] == "python"
    assert len(result["classes"]) == 1
    assert result["classes"][0]["name"] == "DatabaseManager"
    assert len(result["functions"]) == 3  # __init__, connect, global_helper (methods are included in functions list in result for pipeline compatibility)
    assert len(result["imports"]) == 2

def test_parse_javascript_typescript():
    source = """
import { useState } from 'react';
export class UserController {
    constructor() {}
    getUser() {}
}
export interface User {
    id: string;
}
"""
    result = parse_with_tree_sitter(source, "test.ts", "typescript")
    
    assert result["language"] == "typescript"
    assert len(result["classes"]) == 1
    assert result["classes"][0]["name"] == "UserController"
    assert len(result["interfaces"]) == 1
    assert result["interfaces"][0]["name"] == "User"

def test_parse_cpp():
    source = """
#include <iostream>

struct Config {
    int id;
};

class Logger {
public:
    void log(std::string msg) {}
};
"""
    result = parse_with_tree_sitter(source, "test.cpp", "cpp")
    
    assert result["language"] == "cpp"
    assert len(result["classes"]) == 1
    assert result["classes"][0]["name"] == "Logger"
    assert len(result["structs"]) == 1
    assert result["structs"][0]["name"] == "Config"
