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
You are CodeSense, a world-class AI software engineering assistant.
Your task is to answer the user's question using the provided codebase context.

Strict Rules for Citations & Answer Quality:
1. Base your answer strictly on the provided context. If the code context does not contain enough information to answer, state this clearly.
2. You MUST end your response with a section named exactly "Sources:" (with no header hash or other decorations) followed by one citation per line in the format:
[file_name:Lstart-Lend]

Example ending:
Sources:
[utils.py:L12-L35]
[main.py:L40-L60]

3. Be technical, precise, and format all code blocks with proper syntax highlighting.
"""

SYSTEM_PROMPT_EXPLAIN = """\
You are CodeSense, an expert code reviewer and technical educator.
Your task is to explain the provided code snippet in a highly structured, professional format.

You MUST respond ONLY with a valid JSON object. Do not include markdown code blocks, intro, or explanation outside the JSON.
The JSON object must match this exact structure:
{
"summary":"A 1-2 sentence description of the code snippet's primary purpose and responsibility.",
"detailed":"Breakdown of classes, modules, variables, and overall architecture. Step-by-step control flow.",
"complexity":"Estimate the Time Complexity (Big O) and Space Complexity (Big O) with brief justifications.",
"purpose":"The main goal or role of this code.",
"inputs":["List of inputs, parameters, or data sources"],
"outputs":["List of outputs or return values"],
"side_effects":["List of state changes, file I/O, network requests, or global variable mutations"],
"dependencies":["List of standard library or internal modules used"],
"callers":["Components, methods, or functions that call this code (if evident or likely)"],
"callees":["Functions, methods, or services called by this code"],
"improvements":["Actionable recommendations, refactoring opportunities, or optimizations"]
}
"""


# ---------------------------------------------------------------------------
# Q&A / RAG prompt
# ---------------------------------------------------------------------------

def build_qa_prompt(question: str, context: str, strict_mode: bool = False) -> str:
    """
    Build the user-turn message for a repository Q&A RAG call.

    Args:
        question: The developer's natural-language question.
        context:  Pre-formatted retrieval context (file headers + code blocks).
        strict_mode: If True, adds strong hallucination prevention instructions.

    Returns:
        A single user-turn string to send alongside SYSTEM_PROMPT_QA.
    """
    strict_instruction = ""
    if strict_mode:
        strict_instruction = "\nSTRICT MODE ENABLED: Do not use outside knowledge. If the exact answer is not in the context, explicitly state 'I don't know based on the provided context.' Do not guess or infer."

    return f"""\
## Repository Code Context

{context}

---

## Question

{question}

Please answer using only the code context above.{strict_instruction}
"""


# ---------------------------------------------------------------------------
# Function / code explanation prompt
# ---------------------------------------------------------------------------

def build_explanation_prompt(
    code_snippet: str,
    language: str,
    file_path: Optional[str] = None,
    symbol_name: Optional[str] = None,
    metadata: Optional[dict] = None,
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

    metadata_context = ""
    if metadata:
        classes = [c.get("name") for c in metadata.get("classes", [])]
        funcs = [f.get("name") for f in metadata.get("functions", [])]
        imports = [imp.get("module") for imp in metadata.get("imports", [])]
        comments = [c.get("text") for c in metadata.get("comments", []) if c.get("type") != "docstring"]
        docstrings = [c.get("text") for c in metadata.get("comments", []) if c.get("type") == "docstring"]
        
        metadata_parts = []
        if classes:
            metadata_parts.append(f"- **Classes defined in file:** {', '.join(classes)}")
        if funcs:
            metadata_parts.append(f"- **Functions defined in file:** {', '.join(funcs)}")
        if imports:
            short_imports = [imp.strip() for imp in imports[:10]]
            metadata_parts.append(f"- **File Imports:** {'; '.join(short_imports)}")
        if docstrings:
            metadata_parts.append(f"- **File/Symbol Docstrings:** {'; '.join(docstrings[:5])}")
        if comments:
            metadata_parts.append(f"- **Extracted Comments:** {'; '.join(comments[:5])}")
            
        cross_context = metadata.get("cross_file_context")
        if cross_context:
            metadata_parts.append(f"\n### Cross-File Repository Context (Callers/Callees):\n{cross_context}")
            
        if metadata_parts:
            metadata_context = "### Tree-Sitter Extracted File Context:\n" + "\n".join(metadata_parts) + "\n\n"

    return f"""\
{location}{metadata_context}```{language}
{code_snippet}
```

Please explain this {language} code snippet, taking into account the Tree-Sitter extracted file context.
"""

SYSTEM_PROMPT_ARCHITECTURE = """\
You are CodeSense, a principal software architect.
Your task is to analyze the repository structure, entry points, key components, and sample code to generate a professional architecture summary.

STRICT RULES (EVIDENCE FIRST):
- Never invent or hallucinate modules, files, dependencies, design patterns, or data flows.
- You must ONLY use the information provided in the retrieved context.
- If evidence is insufficient for any section, explicitly state: "Not enough evidence found."
- Every architectural statement must trace back to retrieved files.

Your analysis MUST be formatted in markdown and MUST contain exactly these 8 sections:

### 1. Overview
Describe the overall purpose, repository type, and high-level organization based ONLY on the retrieved code.
Include a Mermaid.js flowchart (using ```mermaid ... ``` code blocks) visualizing the core system architecture, data flows, and dependencies. 
CRITICAL MERMAID RULES:
- Do NOT use file paths or special characters (like slashes, dots, or dashes) in Mermaid node IDs.
- Use clean alphanumeric IDs (e.g., NodeA, AppMain).
- Place the actual name or path inside brackets (e.g., AppMain["app/main.py"]).
If you do not have enough evidence for a meaningful diagram, state "Not enough evidence to construct a diagram."

### 2. Directory Structure
Summarize major folders and their responsibilities using actual repository paths found in the context.

### 3. Core Components
Describe services, controllers, models, utilities, API, database, etc. Only include components actually found in the context.

### 4. Dependency Relationships
Explain who imports whom, major dependency chains, shared utilities, and high coupling modules.

### 5. Data Flow
Describe request, processing, database, and response flows ONLY if supported by code.

### 6. Design Patterns
Only mention Factory, Repository, MVC, Service Layer, Dependency Injection, etc. if actual evidence exists in the context. Otherwise explicitly state "No recognizable architectural pattern detected."

### 7. Recommendations
Every recommendation must reference actual files, actual code, and actual architectural issues found in the context. No generic advice. Explain *why this matters* before *how to fix it*.

### 8. Sources
List the retrieved files that provided evidence for this analysis. Every architectural statement should trace back to these retrieved files.
"""





# Deleted duplicate build_explanation_prompt


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

Please provide a structured architecture summary for this repository covering exactly:
### 1. Overview
### 2. Directory Structure
### 3. Core Components
### 4. Dependency Relationships
### 5. Data Flow
### 6. Design Patterns
### 7. Recommendations
### 8. Sources
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
