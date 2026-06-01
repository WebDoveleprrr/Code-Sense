# backend/app/models/dependency_graph.py
from __future__ import annotations

from datetime import datetime
from typing import Any, Dict, List

from beanie import Document
from pydantic import Field

class DependencyGraphDocument(Document):
    """
    Stores the full dependency/reference graph for a given repository.
    Nodes and edges are stored in a single document for fast read/write.
    """
    repo_id: str
    
    # List of node dicts: [{"id": "normalized_path", "type": "file", "language": "python"}, ...]
    nodes: List[Dict[str, Any]] = Field(default_factory=list)
    
    # List of edge dicts: [{"source": "fileA.py", "target": "fileB.py", "type": "import"}, ...]
    edges: List[Dict[str, Any]] = Field(default_factory=list)
    
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)

    class Settings:
        name = "dependency_graphs"
        indexes = [
            [("repo_id", 1)]
        ]
