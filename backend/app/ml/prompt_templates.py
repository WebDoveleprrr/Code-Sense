# backend/app/ml/prompt_templates.py
"""
CodeSense — Prompt Templates for RAG, Q&A, Explanation & Architecture
All templates return plain strings ready to be sent to any LLM.
"""

from __future__ import annotations

from typing import List, Optional


# ---------------------------------------------------------------------------
# System prompts
# ---------------------------------------------------------------------------

SYSTEM_PROMPT_QA = """\
You are CodeSense, an expert software engineering assistant.
You have been given excerpts from a real codebase to answer the user's question.

Rules:
- Base your answer ONLY on the provided code context.
- If the answer cannot be determined from the context, say so clearly.
- When referencing code, cite the file path and line numbers.
- Be concise but technically precise.
- Format code samples with the appropriate language fence (```python, etc.).
"""

SYSTEM_PROMPT_EXPLAIN = """\
You are CodeSense, an expert code reviewer and documentation writer.
Your job is to explain code clearly to developers of all experience levels.

Rules:
- Describe WHAT the code does, HOW it does it, and WHY (if inferrable).
- Mention parameters, return values, side effects, and notable patterns.
- Use plain language; avoid unnecessary jargon.
- Keep the explanation concise — one to three paragraphs unless the code is complex.
"""

SYSTEM_PROMPT_ARCHITECTURE = """\
You are CodeSense, a senior software architect.
You analyse repository metadata and code to describe the architecture of a codebase.

Rules:
- Summarise the high-level design, layers, and key components.
- Identify design patterns, frameworks, and notable architectural decisions.
- Keep the summary developer-friendly and structured.
- Base conclusions strictly on the provided repository metadata and code samples.
"""


# ---------------------------------------------------------------------------
# Q&A / RAG prompt
# ---------------------------------------------------------------------------

def build_qa_prompt(question: str, context: str) -> str:
    """
    Build the user-turn message for a repository Q&A RAG call.

    Args:
        question: The developer's natural-language question.
        context:  Pre-formatted retrieval context (file headers + code blocks).

    Returns:
        A single user-turn string to send alongside SYSTEM_PROMPT_QA.
    """
    return f"""\
## Repository Code Context

{context}

---

## Question

{question}

Please answer using only the code context above.
"""


# ---------------------------------------------------------------------------
# Function / code explanation prompt
# ---------------------------------------------------------------------------

def build_explanation_prompt(
    code_snippet: str,
    language: str,
    file_path: Optional[str] = None,
    symbol_name: Optional[str] = None,
) -> str:
    """
    Build the user-turn message for a code explanation call.
    """
    location = ""
    if file_path:
        location = f"**File:** `{file_path}`"
        if symbol_name:
            location += f"  |  **Symbol:** `{symbol_name}`"
        location += "\n\n"

    return f"""\
{location}```{language}
{code_snippet}
```

Please explain this {language} code snippet.
"""


# ---------------------------------------------------------------------------
# Architecture summariser prompt
# ---------------------------------------------------------------------------

def build_architecture_prompt(
    repo_name: str,
    language_breakdown: dict,
    total_files: int,
    total_functions: int,
    total_classes: int,
    entry_points: List[str],
    key_components: List[str],
    sample_files: List[str],
    code_samples: Optional[str] = None,
) -> str:
    """
    Build the user-turn message for an architecture analysis call.
    """
    lang_str = ", ".join(
        f"{lang} ({count} files)" for lang, count in language_breakdown.items()
    )

    entry_str = "\n".join(f"- `{ep}`" for ep in entry_points) or "- (none detected)"
    component_str = "\n".join(f"- `{c}`" for c in key_components) or "- (none detected)"
    sample_str = "\n".join(f"- `{f}`" for f in sample_files[:20])

    code_section = ""
    if code_samples:
        code_section = f"\n## Sample Code Chunks\n\n{code_samples}\n"

    return f"""\
## Repository: {repo_name}

**Languages:** {lang_str}
**Total Files:** {total_files}
**Functions:** {total_functions}
**Classes:** {total_classes}

### Entry Points
{entry_str}

### Key Config / Build Files
{component_str}

### Representative Files
{sample_str}
{code_section}
---

Please provide a structured architecture summary for this repository covering:
1. Overall architectural style (MVC, microservices, layered, etc.)
2. Key modules and their responsibilities
3. Technology stack and notable libraries
4. Data flow overview
5. Any notable design patterns or conventions
"""


# ---------------------------------------------------------------------------
# Context formatter used by retrieval → prompt pipeline
# ---------------------------------------------------------------------------

def format_retrieved_context(
    chunks: List[dict],
    max_chars: int = 6_000,
) -> str:
    """
    Convert a list of RetrievalResult dicts into a formatted context string.
    Respects a character budget to avoid oversized prompts.
    """
    parts: List[str] = []
    total = 0

    for i, chunk in enumerate(chunks, 1):
        file_path = chunk.get("file_path", "unknown")
        start = chunk.get("start_line", 0)
        end = chunk.get("end_line", 0)
        lang = chunk.get("language", "")
        content = chunk.get("content", "")
        symbol = chunk.get("symbol_name")
        score = chunk.get("score", 0.0)

        symbol_hint = f" [{chunk.get('chunk_type', 'window')}: {symbol}]" if symbol else ""
        header = (
            f"### [{i}] `{file_path}` (lines {start}–{end}){symbol_hint} "
            f"— score: {score:.3f}"
        )
        fence_lang = lang if lang else ""
        block = f"{header}\n```{fence_lang}\n{content}\n```"

        if total + len(block) > max_chars:
            # Try to fit a truncated version
            remaining = max_chars - total - len(header) - 20
            if remaining > 100:
                truncated = content[:remaining] + "\n... [truncated]"
                block = f"{header}\n```{fence_lang}\n{truncated}\n```"
                parts.append(block)
            break

        parts.append(block)
        total += len(block)

    return "\n\n".join(parts)
