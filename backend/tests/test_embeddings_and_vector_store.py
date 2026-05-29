# tests/vector_store/test_embeddings_and_vector_store.py
"""
CodeSense — Tests: Embedding Pipeline + FAISS Vector Store + Retrieval

Covers:
  - Embedder singleton and output shapes
  - embedding_pipeline.generate_embeddings()
  - embedding_pipeline.embed_query()
  - FAISSStore build / save / load / search / batch_search
  - MetadataStore build / save / load / lookups / filters
  - RetrievalService._deduplicate()
  - embedding_utils (normalise, cosine, rank)

All tests are synchronous where possible; async tests use pytest-asyncio.
The real sentence-transformer model is NOT loaded — the Embedder is patched
with a tiny fixed-output stub to keep tests fast and dependency-free.
"""

from __future__ import annotations

import json
import tempfile
from pathlib import Path
from typing import List
from unittest.mock import MagicMock, patch

import numpy as np
import pytest


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

DIM = 16  # Tiny fixed dimension for tests


def _make_embedder_stub(dim: int = DIM) -> MagicMock:
    """Return a MagicMock that mimics the Embedder API."""
    stub = MagicMock()
    stub.dim = dim
    stub.model_name = "stub-model"
    stub.max_seq_length = 256

    def embed_text(text, normalize=True):
        vec = np.random.rand(dim).astype(np.float32)
        if normalize:
            vec /= np.linalg.norm(vec) + 1e-10
        return vec

    def embed_batch(texts, normalize=True, show_progress=False):
        vecs = np.random.rand(len(texts), dim).astype(np.float32)
        if normalize:
            norms = np.linalg.norm(vecs, axis=1, keepdims=True)
            vecs /= norms + 1e-10
        return vecs

    stub.embed_text.side_effect = embed_text
    stub.embed_batch.side_effect = embed_batch
    stub.model_info.return_value = {"model_name": "stub-model", "dim": dim}
    return stub


@pytest.fixture
def tmp_dir():
    with tempfile.TemporaryDirectory() as d:
        yield Path(d)


@pytest.fixture
def dummy_chunks() -> List[dict]:
    return [
        {
            "content": f"def func_{i}(): pass",
            "language": "python",
            "file_path": f"src/module_{i // 5}.py",
            "start_line": i * 10,
            "end_line": i * 10 + 9,
            "chunk_type": "function" if i % 3 == 0 else "window",
            "symbol_name": f"func_{i}" if i % 3 == 0 else None,
            "chunk_index": i,
            "token_count": 20,
        }
        for i in range(20)
    ]


@pytest.fixture
def vectors(dummy_chunks) -> np.ndarray:
    n = len(dummy_chunks)
    vecs = np.random.rand(n, DIM).astype(np.float32)
    norms = np.linalg.norm(vecs, axis=1, keepdims=True)
    return vecs / norms


# ---------------------------------------------------------------------------
# embedding_utils
# ---------------------------------------------------------------------------

class TestEmbeddingUtils:
    def test_l2_normalize_1d(self):
        from app.ml.embedding_utils import l2_normalize
        v = np.array([3.0, 4.0], dtype=np.float32)
        n = l2_normalize(v)
        assert abs(np.linalg.norm(n) - 1.0) < 1e-5

    def test_l2_normalize_2d(self):
        from app.ml.embedding_utils import l2_normalize
        m = np.random.rand(5, DIM).astype(np.float32)
        n = l2_normalize(m)
        norms = np.linalg.norm(n, axis=1)
        assert np.allclose(norms, 1.0, atol=1e-5)

    def test_cosine_similarity_identical(self):
        from app.ml.embedding_utils import cosine_similarity
        v = np.random.rand(DIM).astype(np.float32)
        assert abs(cosine_similarity(v, v) - 1.0) < 1e-4

    def test_cosine_similarity_orthogonal(self):
        from app.ml.embedding_utils import cosine_similarity
        a = np.zeros(DIM, dtype=np.float32)
        b = np.zeros(DIM, dtype=np.float32)
        a[0] = 1.0
        b[1] = 1.0
        assert abs(cosine_similarity(a, b)) < 1e-5

    def test_rank_by_similarity_length(self, vectors):
        from app.ml.embedding_utils import rank_by_similarity
        query = vectors[0]
        results = rank_by_similarity(query, vectors, k=5)
        assert len(results) == 5

    def test_rank_by_similarity_top_is_self(self, vectors):
        from app.ml.embedding_utils import rank_by_similarity
        query = vectors[3]
        results = rank_by_similarity(query, vectors, k=1)
        assert results[0][0] == 3

    def test_vec_to_list_round_trip(self):
        from app.ml.embedding_utils import vec_to_list, list_to_vec
        v = np.random.rand(DIM).astype(np.float32)
        assert np.allclose(list_to_vec(vec_to_list(v)), v, atol=1e-6)

    def test_pad_or_truncate(self):
        from app.ml.embedding_utils import pad_or_truncate
        v = np.ones(10, dtype=np.float32)
        assert pad_or_truncate(v, 10).shape == (10,)
        assert pad_or_truncate(v, 5).shape == (5,)
        assert pad_or_truncate(v, 15).shape == (15,)


# ---------------------------------------------------------------------------
# embedding_pipeline
# ---------------------------------------------------------------------------

class TestEmbeddingPipeline:

    @patch("app.ml.embedding_pipeline.get_embedder")
    def test_generate_embeddings_shape(self, mock_get_embedder, dummy_chunks):
        from app.ml.embedding_pipeline import generate_embeddings
        mock_get_embedder.return_value = _make_embedder_stub(DIM)
        vectors, stats = generate_embeddings(dummy_chunks)
        assert vectors.shape == (len(dummy_chunks), DIM)
        assert vectors.dtype == np.float32

    @patch("app.ml.embedding_pipeline.get_embedder")
    def test_generate_embeddings_empty(self, mock_get_embedder):
        from app.ml.embedding_pipeline import generate_embeddings
        mock_get_embedder.return_value = _make_embedder_stub(DIM)
        vectors, stats = generate_embeddings([])
        assert vectors.shape[0] == 0
        assert stats["count"] == 0

    @patch("app.ml.embedding_pipeline.get_embedder")
    def test_stats_keys(self, mock_get_embedder, dummy_chunks):
        from app.ml.embedding_pipeline import generate_embeddings
        mock_get_embedder.return_value = _make_embedder_stub(DIM)
        _, stats = generate_embeddings(dummy_chunks)
        for key in ("count", "dim", "model", "elapsed_s", "throughput_per_s", "shape"):
            assert key in stats

    @patch("app.ml.embedding_pipeline.get_embedder")
    def test_embed_query_shape(self, mock_get_embedder):
        from app.ml.embedding_pipeline import embed_query
        mock_get_embedder.return_value = _make_embedder_stub(DIM)
        vec = embed_query("find authentication functions")
        assert vec.shape == (DIM,)
        assert vec.dtype == np.float32

    @patch("app.ml.embedding_pipeline.get_embedder")
    def test_embed_query_empty(self, mock_get_embedder):
        from app.ml.embedding_pipeline import embed_query
        stub = _make_embedder_stub(DIM)
        mock_get_embedder.return_value = stub
        vec = embed_query("   ")
        assert vec.shape == (DIM,)

    def test_prepare_texts_function_chunk(self):
        from app.ml.embedding_pipeline import _prepare_text
        chunk = {
            "content": "def parse(): ...",
            "chunk_type": "function",
            "symbol_name": "parse",
            "language": "python",
        }
        text = _prepare_text(chunk)
        assert "function: parse" in text
        assert "[python]" in text

    def test_prepare_texts_truncation(self):
        from app.ml.embedding_pipeline import _prepare_text, MAX_CHARS_PER_CHUNK
        chunk = {"content": "x" * (MAX_CHARS_PER_CHUNK + 500), "chunk_type": "window"}
        text = _prepare_text(chunk)
        assert len(text) <= MAX_CHARS_PER_CHUNK


# ---------------------------------------------------------------------------
# FAISSStore
# ---------------------------------------------------------------------------

class TestFAISSStore:

    def _make_store(self, tmp_dir: Path) -> "FAISSStore":
        from app.vector_store.faiss_store import FAISSStore
        return FAISSStore(repo_id="test-repo", index_path=str(tmp_dir))

    def test_build_and_search(self, tmp_dir, vectors):
        store = self._make_store(tmp_dir)
        store.build(vectors)
        ids, scores = store.search(vectors[0], top_k=3)
        assert len(ids) == 3
        assert ids[0] == 0  # exact match

    def test_build_saves_meta(self, tmp_dir, vectors):
        store = self._make_store(tmp_dir)
        store.build(vectors, model_name="all-MiniLM-L6-v2")
        store.save()
        meta_path = tmp_dir / "index_meta.json"
        assert meta_path.exists()
        meta = json.loads(meta_path.read_text())
        assert meta["model_name"] == "all-MiniLM-L6-v2"
        assert meta["ntotal"] == len(vectors)

    def test_save_and_load(self, tmp_dir, vectors):
        from app.vector_store.faiss_store import FAISSStore
        store = self._make_store(tmp_dir)
        store.build(vectors)
        store.save()

        store2 = FAISSStore(repo_id="test-repo", index_path=str(tmp_dir))
        store2.load()
        assert store2.total == len(vectors)

    def test_search_after_load(self, tmp_dir, vectors):
        from app.vector_store.faiss_store import FAISSStore
        store = self._make_store(tmp_dir)
        store.build(vectors)
        store.save()

        store2 = FAISSStore(repo_id="test-repo", index_path=str(tmp_dir))
        ids, scores = store2.search(vectors[5], top_k=5)
        assert 5 in ids

    def test_batch_search(self, tmp_dir, vectors):
        store = self._make_store(tmp_dir)
        store.build(vectors)
        query_batch = vectors[:3]
        all_ids, all_scores = store.batch_search(query_batch, top_k=3)
        assert len(all_ids) == 3
        assert len(all_ids[0]) == 3

    def test_exists_false_before_save(self, tmp_dir, vectors):
        store = self._make_store(tmp_dir)
        store.build(vectors)
        assert not store.exists()  # not saved yet

    def test_exists_true_after_save(self, tmp_dir, vectors):
        store = self._make_store(tmp_dir)
        store.build(vectors)
        store.save()
        assert store.exists()

    def test_health_dict_keys(self, tmp_dir, vectors):
        store = self._make_store(tmp_dir)
        store.build(vectors)
        health = store.health()
        for key in ("repo_id", "loaded", "on_disk", "total", "dim", "index_type"):
            assert key in health

    def test_delete(self, tmp_dir, vectors):
        store = self._make_store(tmp_dir)
        store.build(vectors)
        store.save()
        assert store.exists()
        store.delete()
        assert not store.exists()

    def test_float64_vectors_converted(self, tmp_dir):
        from app.vector_store.faiss_store import FAISSStore
        vecs = np.random.rand(10, DIM)  # float64
        store = FAISSStore(repo_id="test-repo", index_path=str(tmp_dir))
        store.build(vecs)  # should not raise


# ---------------------------------------------------------------------------
# MetadataStore
# ---------------------------------------------------------------------------

class TestMetadataStore:

    def _make_store(self, tmp_dir: Path) -> "MetadataStore":
        from app.vector_store.metadata_store import MetadataStore
        return MetadataStore(repo_id="test-repo", index_path=str(tmp_dir))

    def test_build_from_chunks(self, tmp_dir, dummy_chunks):
        store = self._make_store(tmp_dir)
        store.build_from_chunks(dummy_chunks)
        assert store.count == len(dummy_chunks)

    def test_get_by_faiss_id(self, tmp_dir, dummy_chunks):
        store = self._make_store(tmp_dir)
        store.build_from_chunks(dummy_chunks)
        record = store.get_by_faiss_id(0)
        assert record is not None
        assert record["faiss_id"] == 0

    def test_get_by_faiss_id_out_of_range(self, tmp_dir, dummy_chunks):
        store = self._make_store(tmp_dir)
        store.build_from_chunks(dummy_chunks)
        assert store.get_by_faiss_id(999) is None

    def test_get_many(self, tmp_dir, dummy_chunks):
        store = self._make_store(tmp_dir)
        store.build_from_chunks(dummy_chunks)
        records = store.get_many([0, 1, 2])
        assert len(records) == 3
        assert all(r is not None for r in records)

    def test_filter_by_language(self, tmp_dir, dummy_chunks):
        store = self._make_store(tmp_dir)
        store.build_from_chunks(dummy_chunks)
        ids = list(range(len(dummy_chunks)))
        filtered = store.filter_by_language(ids, "python")
        # All dummy_chunks are python
        assert len(filtered) == len(dummy_chunks)

    def test_filter_by_chunk_type(self, tmp_dir, dummy_chunks):
        store = self._make_store(tmp_dir)
        store.build_from_chunks(dummy_chunks)
        ids = list(range(len(dummy_chunks)))
        fn_ids = store.filter_by_chunk_type(ids, "function")
        win_ids = store.filter_by_chunk_type(ids, "window")
        assert len(fn_ids) + len(win_ids) == len(dummy_chunks)

    def test_save_and_load(self, tmp_dir, dummy_chunks):
        from app.vector_store.metadata_store import MetadataStore
        store = self._make_store(tmp_dir)
        store.build_from_chunks(dummy_chunks, chunk_ids=[str(i) for i in range(len(dummy_chunks))])
        store.save()

        store2 = MetadataStore(repo_id="test-repo", index_path=str(tmp_dir))
        store2.load()
        assert store2.count == len(dummy_chunks)
        assert store2.get_by_faiss_id(5)["chunk_id"] == "5"

    def test_patch_chunk_ids(self, tmp_dir, dummy_chunks):
        store = self._make_store(tmp_dir)
        store.build_from_chunks(dummy_chunks)
        ids = [f"mongo-{i}" for i in range(len(dummy_chunks))]
        store.patch_chunk_ids(ids)
        assert store.get_by_faiss_id(7)["chunk_id"] == "mongo-7"

    def test_exists_false_before_save(self, tmp_dir, dummy_chunks):
        store = self._make_store(tmp_dir)
        store.build_from_chunks(dummy_chunks)
        assert not store.exists()

    def test_exists_true_after_save(self, tmp_dir, dummy_chunks):
        store = self._make_store(tmp_dir)
        store.build_from_chunks(dummy_chunks)
        store.save()
        assert store.exists()


# ---------------------------------------------------------------------------
# RetrievalService (unit-level)
# ---------------------------------------------------------------------------

class TestRetrievalServiceHelpers:

    def test_deduplicate_same_location(self):
        from app.services.retrieval_service import _deduplicate
        results = [
            {"file_path": "a.py", "start_line": 1, "score": 0.9, "content": ""},
            {"file_path": "a.py", "start_line": 1, "score": 0.7, "content": ""},  # duplicate
            {"file_path": "b.py", "start_line": 10, "score": 0.8, "content": ""},
        ]
        deduped = _deduplicate(results)
        assert len(deduped) == 2

    def test_deduplicate_keeps_higher_score(self):
        from app.services.retrieval_service import _deduplicate
        results = [
            {"file_path": "a.py", "start_line": 1, "score": 0.5, "content": ""},
            {"file_path": "a.py", "start_line": 1, "score": 0.95, "content": ""},
        ]
        deduped = _deduplicate(results)
        assert len(deduped) == 1
        assert deduped[0]["score"] == 0.95

    def test_deduplicate_preserves_order(self):
        from app.services.retrieval_service import _deduplicate
        results = [
            {"file_path": "a.py", "start_line": 1, "score": 0.9, "content": ""},
            {"file_path": "b.py", "start_line": 5, "score": 0.8, "content": ""},
            {"file_path": "c.py", "start_line": 2, "score": 0.7, "content": ""},
        ]
        deduped = _deduplicate(results)
        assert [r["file_path"] for r in deduped] == ["a.py", "b.py", "c.py"]
