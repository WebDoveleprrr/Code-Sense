# backend/tests/test_impact_and_review.py
import pytest
import pytest_asyncio
from app.services.impact_service import ImpactService
from app.services.review_service import ReviewService
from app.models.dependency_graph import DependencyGraphDocument
from app.models.repository import RepositoryDocument, RepoStatus, RepoSource
from beanie import init_beanie
from motor.motor_asyncio import AsyncIOMotorClient

@pytest_asyncio.fixture(autouse=True)
async def init_mock_db():
    client = AsyncIOMotorClient("mongodb://localhost:27017")
    db = client.test_db
    await init_beanie(
        database=db,
        document_models=[RepositoryDocument, DependencyGraphDocument]
    )

def test_impact_bfs_dfs():
    graph = DependencyGraphDocument(
        repo_id="test_repo",
        nodes=[
            {"id": "auth.py", "type": "file"},
            {"id": "db.py", "type": "file"},
            {"id": "main.py", "type": "file"}
        ],
        edges=[
            {"source": "main.py", "target": "auth.py", "type": "import"},
            {"source": "auth.py", "target": "db.py", "type": "import"}
        ]
    )
    
    service = ImpactService()
    
    # BFS: modifying db.py should affect auth.py and main.py
    res_bfs = service.analyze_impact(graph, "db.py", algorithm="bfs")
    assert "auth.py" in res_bfs["affected_files"]
    assert "main.py" in res_bfs["affected_files"]
    assert res_bfs["risk_score"] > 0
    
    # DFS
    res_dfs = service.analyze_impact(graph, "db.py", algorithm="dfs")
    assert "auth.py" in res_dfs["affected_files"]
    assert "main.py" in res_dfs["affected_files"]

def test_static_rule_engine(tmp_path):
    # Create temp directory with file containing a security smell
    file_path = tmp_path / "unsafe.py"
    file_path.write_text("token = 'abcdef1234567890abcdef1234567890'\neval('print(42)')")
    
    service = ReviewService()
    issues = service._run_static_rules(tmp_path)
    
    categories = [i["category"] for i in issues]
    assert "Security" in categories
    assert len(issues) >= 2
