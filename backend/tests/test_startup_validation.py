# backend/tests/test_startup_validation.py
import pytest
from app.ml.llm_client import normalize_model_name

def test_normalize_model_name():
    # Verify target tag matching, default latest stripping, registry path cleaning
    assert normalize_model_name("library/llama3.2:latest") == "llama3.2"
    assert normalize_model_name("llama3.2:latest") == "llama3.2"
    assert normalize_model_name("llama3.2:3b") == "llama3.2:3b"
    assert normalize_model_name("llama3.2") == "llama3.2"
    assert normalize_model_name("registry.hub.docker.com/library/llama3.2:3b") == "llama3.2:3b"
