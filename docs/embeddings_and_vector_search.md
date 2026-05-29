# CodeSense — Embeddings & Vector Search System

## Overview

This document describes the complete embedding and vector search stack
added in v3 of the CodeSense backend.

---

## Architecture

```
User query
    │
    ▼
embedding_pipeline.embed_query()
    │  sentence-transformers (all-MiniLM-L6-v2 or CodeBERT)
    ▼
query_vec  shape (dim,)
    │
    ▼
FAISSStore.search()                 ← loads per-repo FAISS index from disk
    │  IndexFlatIP  (<10 k vectors)
    │  IndexIVFFlat (≥10 k vectors)
    ▼
(faiss_ids, scores)
    │
    ▼
MetadataStore.get_many()            ← disk-local JSON sidecar (fast path)
    │  or ChunkDocument.find()      ← MongoDB fallback
    ▼
post-filters  (language, chunk_type, min_score, dedup)
    │
    ▼
ranked results  →  SearchResponse / RAG context
```

---

## Module Reference

| Module | Path | Purpose |
|--------|------|---------|
| `Embedder` | `backend/app/ml/embedder.py` | SentenceTransformer wrapper, singleton |
| `embedding_pipeline` | `backend/app/ml/embedding_pipeline.py` | Batch embed chunks; embed queries |
| `embedding_utils` | `backend/app/ml/embedding_utils.py` | Numpy helpers (normalise, cosine, rank) |
| `FAISSStore` | `backend/app/vector_store/faiss_store.py` | Per-repo FAISS index lifecycle |
| `MetadataStore` | `backend/app/vector_store/metadata_store.py` | JSON sidecar for chunk metadata |
| `RetrievalService` | `backend/app/services/retrieval_service.py` | End-to-end semantic retrieval |
| `SearchService` | `backend/app/services/search_service.py` | Search + audit logging |
| `search` API | `backend/app/api/v1/search.py` | POST /search, /search/batch, /search/info |
| `vector_store` API | `backend/app/api/v1/vector_store.py` | Health, rebuild, delete, metadata list |

---

## Supported Embedding Models

| Model | Dim | Speed | Best for |
|-------|-----|-------|----------|
| `all-MiniLM-L6-v2` | 384 | ⚡ Fast | General search, default |
| `microsoft/codebert-base` | 768 | 🐢 Slower | Code-heavy repos |
| `all-mpnet-base-v2` | 768 | Medium | Balanced quality |

Switch by setting `EMBEDDING_MODEL` in `.env`.  
> **Important:** changing the model requires re-ingesting all repositories
> (the FAISS index dimension must match the model dim).

---

## FAISS Index Strategy

| Corpus size | Index type | Notes |
|-------------|------------|-------|
| < 10 000 vectors | `IndexFlatIP` | Exact search, cosine via inner product |
| ≥ 10 000 vectors | `IndexIVFFlat` | Approximate, faster at scale |

Vectors are **L2-normalised** before indexing so inner-product == cosine similarity.

### Disk layout

```
vector_store/indices/{repo_id}/
  index.faiss        ← FAISS binary index
  index_meta.json    ← dim, ntotal, model, index_type, created_at
  chunk_meta.json    ← per-vector chunk metadata (file_path, lines, type…)
```

---

## API Endpoints

### `POST /api/v1/search`

```json
{
  "repo_id": "664f...",
  "query": "how are embeddings generated",
  "top_k": 5,
  "language_filter": "python",
  "chunk_type_filter": "function",
  "min_score": 0.3
}
```

### `POST /api/v1/search/batch`

```json
{
  "repo_id": "664f...",
  "queries": ["query one", "query two"],
  "top_k": 5
}
```

### `GET /api/v1/search/info`

Returns current embedding model metadata.

### `GET /api/v1/vector-store/{repo_id}/health`

Returns FAISS index stats (total vectors, dim, index type, model).

### `POST /api/v1/vector-store/{repo_id}/rebuild`

Triggers background re-embedding and FAISS index rebuild without
re-parsing the repository. Useful after changing the embedding model.

### `DELETE /api/v1/vector-store/{repo_id}`

Deletes the FAISS index files from disk (repo record stays in MongoDB).

### `GET /api/v1/vector-store/{repo_id}/metadata`

Lists chunk metadata entries from the JSON sidecar (paginated).

---

## Ingestion Pipeline Integration (v3 changes)

`pipeline.py` now:

1. Calls `generate_embeddings(chunks)` from `embedding_pipeline` instead
   of calling the `Embedder` directly — this adds text preparation and stats.
2. Passes `model_name` into `FAISSStore.build()` for index metadata.
3. Builds and saves a `MetadataStore` JSON sidecar alongside the FAISS index.
4. Back-patches `chunk_ids` into the sidecar after MongoDB insert.

---

## Running Tests

```bash
cd backend
pytest tests/vector_store/test_embeddings_and_vector_store.py -v
```

The test suite mocks the SentenceTransformer model — no GPU or internet
connection required. All FAISS and metadata operations use real `tempfile`
directories.
