# CodeSense — Semantic Search & RAG Pipeline

## Overview

This document describes the semantic search and retrieval-augmented generation (RAG) pipeline introduced in **v3** of CodeSense. It covers the data flow, component responsibilities, configuration, and usage of every endpoint.

---

## Architecture Diagram

```
User Query
    │
    ▼
┌──────────────────────────────────────────────┐
│              API Layer (FastAPI)              │
│  POST /api/v1/search                         │
│  POST /api/v1/qa                             │
│  POST /api/v1/explain  (+ /symbol)           │
│  GET  /api/v1/architecture/{repo_id}         │
└───────────────────┬──────────────────────────┘
                    │
                    ▼
┌──────────────────────────────────────────────┐
│              Service Layer                   │
│  SearchService → RetrievalService            │
│  QAService     → RetrievalService +          │
│                  ContextRanker + RAG         │
│  ExplainService → CodeReader + RAG           │
│  ArchitectureService → RetrievalService +    │
│                        RAG                  │
└──────────────────┬───────────────────────────┘
                   │
        ┌──────────┴──────────┐
        ▼                     ▼
┌───────────────┐    ┌──────────────────────┐
│ RetrievalSvc  │    │    RAG Module         │
│ 1. embed_query│    │ prompt_templates.py   │
│ 2. FAISS ANN  │    │ llm_client.py         │
│ 3. Hydrate    │    │ context_ranker.py     │
│ 4. Filter     │    └──────────────────────┘
│ 5. Dedupe     │
└───────────────┘
```

---

## Components

### `app/ml/prompt_templates.py`
Centralised Jinja-free prompt library. All system prompts and user-turn builders live here. Swapping wording or adding few-shot examples requires no code changes elsewhere.

| Function | Purpose |
|---|---|
| `SYSTEM_PROMPT_QA` | System role for Q&A |
| `SYSTEM_PROMPT_EXPLAIN` | System role for code explanation |
| `SYSTEM_PROMPT_ARCHITECTURE` | System role for arch summariser |
| `build_qa_prompt(question, context)` | User-turn for RAG Q&A |
| `build_explanation_prompt(...)` | User-turn for code explanation |
| `build_architecture_prompt(...)` | User-turn for arch summary |
| `format_retrieved_context(chunks, max_chars)` | Serialise ranked chunks → prompt string |

### `app/ml/context_ranker.py`
Re-ranks FAISS ANN results before answer generation.

**Composite score formula:**
```
composite = 0.70 × faiss_score
           + 0.20 × cross_encoder_score   (optional)
           + 0.07 × symbol_token_overlap
           + 0.03 × position_score
```
Then multiplied by a chunk-type boost: `function × 1.05`, `class × 1.03`, `window × 1.00`.

The cross-encoder (`cross-encoder/ms-marco-MiniLM-L-6-v2`) loads lazily and degrades gracefully if unavailable.

### `app/ml/llm_client.py`
Provider-agnostic LLM dispatch. Reads `LLM_PROVIDER` from env.

| Provider | Env Var | Model Default |
|---|---|---|
| `openai` | `OPENAI_API_KEY` | `gpt-4o-mini` |
| `anthropic` | `ANTHROPIC_API_KEY` | `claude-3-haiku-20240307` |
| `local` | _(none)_ | Extractive fallback |

### `app/ml/rag.py`
Orchestrates answer + explanation + architecture generation. Calls `llm_client.complete()` with prompts from `prompt_templates.py`.

### `app/services/qa_service.py`
Full RAG pipeline:
1. `RetrievalService.retrieve()` → candidates
2. `context_ranker.apply_ranking()` → re-ranked context
3. `rag.build_rag_context()` → prompt context string
4. `rag.generate_answer()` → LLM answer
5. Audit log (fire-and-forget)

### `app/services/explain_service.py`
Reads raw code with `code_reader.read_lines()`, infers language from extension, looks up symbol name from `ChunkDocument`, then calls `rag.generate_explanation()`.

### `app/services/architecture_service.py`
Retrieves code samples via 5 semantic seed queries, combines with stored repo metadata, calls `rag.generate_architecture_summary()`.

---

## API Reference

### `POST /api/v1/search`
Semantic similarity search.

```json
{
  "repo_id": "...",
  "query": "how does authentication work",
  "top_k": 5,
  "language_filter": "python",
  "min_score": 0.2
}
```

### `POST /api/v1/qa`
Full RAG Q&A with re-ranking.

```json
{
  "repo_id": "...",
  "question": "How does the embedding pipeline generate vectors?",
  "top_k": 8,
  "use_cross_encoder": true,
  "provider": "openai"
}
```

### `POST /api/v1/qa/multi`
Parallel multi-question RAG (up to 5 questions).

### `GET /api/v1/qa/history?repo_id=...`
Paginated Q&A audit log.

### `POST /api/v1/explain`
Explain a line range in a file.

```json
{
  "repo_id": "...",
  "file_path": "backend/app/ml/embedder.py",
  "start_line": 80,
  "end_line": 110
}
```

### `POST /api/v1/explain/symbol`
Explain a named function or class.

```json
{ "repo_id": "...", "symbol_name": "generate_embeddings" }
```

### `GET /api/v1/architecture/{repo_id}`
Full AI-generated architecture summary.

### `GET /api/v1/architecture/{repo_id}/metrics`
Fast structural metrics — no LLM call.

---

## Configuration

Add to `.env`:

```dotenv
LLM_PROVIDER=openai          # openai | anthropic | local
OPENAI_API_KEY=sk-...
OPENAI_MODEL=gpt-4o-mini
LLM_MAX_TOKENS=1024
LLM_TEMPERATURE=0.2
```

---

## Testing

```bash
pytest tests/rag/ -v
```

Tests use `unittest.mock` to patch `llm_client.complete` and `RetrievalService.retrieve` — no API keys or running services needed.
