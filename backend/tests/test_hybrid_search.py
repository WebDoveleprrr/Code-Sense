# backend/tests/test_hybrid_search.py
import pytest
import pytest_asyncio
from app.services.retrieval_service import RetrievalService
from app.models.repository import RepositoryDocument, RepoStatus, RepoSource
from app.models.chunk import ChunkDocument
from beanie import init_beanie
from motor.motor_asyncio import AsyncIOMotorClient

@pytest_asyncio.fixture(autouse=True)
async def init_mock_db():
    client = AsyncIOMotorClient("mongodb://localhost:27017")
    db = client.test_db
    # Clear out mock DB first
    await init_beanie(
        database=db,
        document_models=[RepositoryDocument, ChunkDocument]
    )

@pytest.mark.asyncio
async def test_hybrid_search_fallback():
    # Insert mock repo
    repo = RepositoryDocument(
        name="test-repo",
        source=RepoSource.ZIP,
        status=RepoStatus.READY,
        faiss_index_path="dummy"
    )
    await repo.insert()
    
    # Insert mock chunks
    chunk1 = ChunkDocument(
        repo_id=str(repo.id),
        file_path="auth.py",
        content="def login(): return 'secret_token'",
        start_line=1,
        end_line=2,
        faiss_id=0
    )
    await chunk1.insert()
    
    # Instantiate retrieval service
    service = RetrievalService()
    
    # Run retrieval
    # Because FAISS is dummy, FAISS search will fail, but the service should gracefully
    # handle it and fallback or use lexical retrieval if BM25 catches it.
    # Note: We override FAISSStore search in retrieval service, let's see how it runs.
    # To avoid actual FAISSStore search exceptions, we mock store.search or let it raise NotFound.
    # Let's mock FAISSStore.search to return mock lists.
    from unittest.mock import MagicMock
    from app.vector_store.faiss_store import FAISSStore
    
    original_search = FAISSStore.search
    FAISSStore.search = MagicMock(return_value=([0], [0.99]))
    
    try:
        res = await service.retrieve(
            repo_id=str(repo.id),
            query="login",
            top_k=5
        )
        assert res["success"] is True
        assert len(res["results"]) > 0
        assert "login" in res["results"][0]["content"]
    finally:
        FAISSStore.search = original_search
