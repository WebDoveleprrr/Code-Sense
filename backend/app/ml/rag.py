# backend/app/ml/rag.py
"""
CodeSense — RAG Answer & Explanation Generator (v2)

REPLACES the stub rag.py with a full implementation that:
  - Routes to llm_client.complete() for generative answers
  - Uses structured prompt_templates for Q&A, explanation, and architecture
  - Applies context_ranker before answer generation
  - Returns richly formatted Markdown responses

Drop-in compatible with all existing callers:
  - qa_service.py      → generate_answer(question, context)
  - explain_service.py → generate_explanation(code_snippet, language)
  - architecture_service.py uses ArchitectureRAG directly
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional

from app_logger import logger

from app.ml.llm_client import complete
from app.ml.prompt_templates import (
    SYSTEM_PROMPT_ARCHITECTURE,
    SYSTEM_PROMPT_EXPLAIN,
    SYSTEM_PROMPT_QA,
    build_architecture_prompt,
    build_explanation_prompt,
    build_qa_prompt,
    format_retrieved_context,
)


# ─────────────────────────────────────────────
# LINES 39-77
# PURPOSE:
# The core generative function for answering user questions based on retrieved code.
#
# WHY IT EXISTS:
# Retrieving code is only half the battle. We must package that code into a
# structured prompt and ask an LLM to synthesize an answer. This function acts
# as the final layer of the Retrieval-Augmented Generation (RAG) pipeline.
#
# ARCHITECTURE NOTE:
# This file intentionally separates *Prompt Construction* (`prompt_templates.py`) 
# and *Network Execution* (`llm_client.py`) from the RAG orchestration logic.
#
# USED BY:
# `qa_service.py`
#
# INTERVIEW NOTE:
# "In my RAG implementation, I strictly decouple retrieval from generation. 
# `generate_answer` receives the context as a raw string; it doesn't care if that 
# string came from FAISS, MongoDB, or a mock test. This makes the LLM layer 100% 
# unit-testable without needing a live vector database."
# ─────────────────────────────────────────────

async def generate_answer(
    question: str,
    context: str,
    *,
    provider: Optional[str] = None,
) -> str:
    """
    Generate a grounded answer to `question` using `context`.

    Args:
        question:  The developer's natural-language question.
        context:   Pre-formatted retrieved code context string.
        provider:  Optional LLM provider override ("openai" | "anthropic" | "local").

    Returns:
        Markdown-formatted answer string.
    """
    # FLOW:
    # qa_service
    #   ↓ (searches FAISS)
    # context string
    #   ↓
    # generate_answer()
    #   ↓ (build_qa_prompt)
    # complete()
    #   ↓
    # Gemini / OpenAI API
    #   ↓
    # Markdown Answer

    if not context.strip():
        # Guard clause: Hallucination prevention.
        # If the vector search found nothing, do NOT let the LLM guess the answer.
        return (
            "No relevant code context was found for this question.\n\n"
            "_Try rephrasing your query or ensure the repository has been indexed._"
        )

    user_prompt = build_qa_prompt(question=question, context=context)

    logger.info(
        "RAG answer generation | question_len={q} context_len={c}",
        q=len(question),
        c=len(context),
    )

    answer = await complete(
        system_prompt=SYSTEM_PROMPT_QA,
        user_prompt=user_prompt,
        provider=provider,
    )

    return answer


# ─────────────────────────────────────────────
# LINES 83-130
# PURPOSE:
# Generates inline explanations for specific code snippets (e.g., when a user
# highlights code in the frontend).
#
# WHY IT EXISTS:
# Often users don't want to search the entire codebase; they just want to understand
# a specific function they are looking at. This skips the vector retrieval phase
# and performs a direct zero-shot explanation.
# ─────────────────────────────────────────────

async def generate_explanation(
    code_snippet: str,
    language: str,
    *,
    file_path: Optional[str] = None,
    symbol_name: Optional[str] = None,
    metadata: Optional[dict] = None,
    provider: Optional[str] = None,
) -> str:
    """
    Explain a code snippet.

    Args:
        code_snippet: The raw source code to explain.
        language:     Programming language identifier (python, js, etc.).
        file_path:    Source file path for context (optional).
        symbol_name:  Function/class name if known (optional).
        metadata:     Tree-sitter parsed metadata of the file (optional).
        provider:     Optional LLM provider override.

    Returns:
        Markdown explanation string.
    """
    if not code_snippet.strip():
        return "No code provided to explain."

    user_prompt = build_explanation_prompt(
        code_snippet=code_snippet,
        language=language,
        file_path=file_path,
        symbol_name=symbol_name,
        metadata=metadata,
    )

    logger.info(
        "Explanation generation | lang={l} snippet_len={n}",
        l=language,
        n=len(code_snippet),
    )

    explanation = await complete(
        system_prompt=SYSTEM_PROMPT_EXPLAIN,
        user_prompt=user_prompt,
        provider=provider,
    )

    return explanation


# ─────────────────────────────────────────────
# LINES 136-183
# PURPOSE:
# Generates a high-level architectural overview of a repository.
#
# WHY IT EXISTS:
# Gives users a "birds-eye view" of a codebase immediately after ingestion.
# Instead of searching vectors, this prompt relies heavily on the structural
# metadata (total files, language breakdown, entry points) extracted by
# the AST parser during ingestion.
# ─────────────────────────────────────────────

async def generate_architecture_summary(
    repo_name: str,
    language_breakdown: Dict[str, Any],
    total_files: int,
    total_functions: int,
    total_classes: int,
    entry_points: List[str],
    key_components: List[str],
    sample_files: List[str],
    code_samples: Optional[str] = None,
    *,
    provider: Optional[str] = None,
) -> str:
    """
    Generate a structured architecture summary for a repository.

    Called by ArchitectureService.summarise() with repo metadata + optional
    code samples retrieved via semantic search.

    Returns:
        Markdown-formatted architecture summary.
    """
    user_prompt = build_architecture_prompt(
        repo_name=repo_name,
        language_breakdown={k: v for k, v in language_breakdown.items()},
        total_files=total_files,
        total_functions=total_functions,
        total_classes=total_classes,
        entry_points=entry_points,
        key_components=key_components,
        sample_files=sample_files,
        code_samples=code_samples,
    )

    logger.info(
        "Architecture summary generation | repo={r} files={f}",
        r=repo_name,
        f=total_files,
    )

    summary = await complete(
        system_prompt=SYSTEM_PROMPT_ARCHITECTURE,
        user_prompt=user_prompt,
        provider=provider,
    )

    return summary


# ---------------------------------------------------------------------------
# RAG context builder (used by qa_service for multi-query RAG)
# ---------------------------------------------------------------------------

def build_rag_context(chunks: List[Dict[str, Any]], max_chars: int = 6_000) -> str:
    """
    Convert ranked retrieval results into a prompt-ready context string.
    Thin wrapper over prompt_templates.format_retrieved_context.
    """
    # SCALABILITY NOTE:
    # max_chars acts as a safety valve. If the retriever accidentally pulls
    # massive files, this truncation ensures we never exceed the LLM's context limit,
    # preventing HTTP 400 Payload Too Large errors from the provider.
    return format_retrieved_context(chunks, max_chars=max_chars)
