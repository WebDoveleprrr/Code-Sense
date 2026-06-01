# backend/app/services/impact_service.py
from __future__ import annotations

import collections
from typing import Any, Dict, List, Set, Optional

from app_logger import logger
from app.models.repository import RepositoryDocument
from app.models.dependency_graph import DependencyGraphDocument

class ImpactService:
    """
    Builds, persists, and queries a repository's dependency and reference graph.
    Supports BFS/DFS traversals to perform impact analysis ("What breaks if I change X?").
    """

    async def get_or_build_graph(self, repo_id: str) -> DependencyGraphDocument:
        """Fetch the dependency graph from DB, or build and store it if missing."""
        graph_doc = await DependencyGraphDocument.find_one(DependencyGraphDocument.repo_id == repo_id)
        if graph_doc:
            return graph_doc
        
        logger.info(f"Dependency graph for repo {repo_id} not found in DB. Building now...")
        return await self.build_and_save_graph(repo_id)

    async def build_and_save_graph(self, repo_id: str) -> DependencyGraphDocument:
        """
        Scan repo metadata and chunks to construct nodes and edges,
        then save the resulting graph to MongoDB.
        """
        repo = await RepositoryDocument.get(repo_id)
        if not repo:
            raise ValueError(f"Repository {repo_id} not found.")

        nodes: List[Dict[str, Any]] = []
        edges: List[Dict[str, Any]] = []

        # 1. Create file and symbol nodes
        files = repo.repo_metadata.get("files", [])
        symbol_to_file: Dict[str, str] = {}
        all_symbol_names: Set[str] = set()
        seen_node_ids: Set[str] = set()

        for f in files:
            file_path = f["file_path"].replace('\\', '/')
            if file_path not in seen_node_ids:
                seen_node_ids.add(file_path)
                nodes.append({
                    "id": file_path,
                    "type": "file",
                    "label": file_path.split('/')[-1],
                    "language": f.get("language", "unknown")
                })

        # Fetch chunks to get detailed function and class symbols
        from app.models.chunk import ChunkDocument
        chunks = await ChunkDocument.find(ChunkDocument.repo_id == repo_id).to_list()
        
        for c in chunks:
            if c.symbol_name:
                file_path_clean = c.file_path.replace('\\', '/')
                symbol_id = f"{file_path_clean}::{c.symbol_name}"
                if symbol_id not in seen_node_ids:
                    seen_node_ids.add(symbol_id)
                    c_type = (c.chunk_type or "function").lower()
                    if c_type in ("struct", "interface"):
                        c_type = "class"
                    nodes.append({
                        "id": symbol_id,
                        "type": c_type,
                        "label": c.symbol_name,
                        "file_path": file_path_clean,
                        "start_line": c.start_line,
                        "end_line": c.end_line,
                        "symbol_name": c.symbol_name,
                        "metadata": c.symbol_metadata or {}
                    })
                symbol_to_file[c.symbol_name] = file_path_clean
                all_symbol_names.add(c.symbol_name)

        # 2. Extract edges: imports and symbol references
        for f in files:
            file_path = f["file_path"].replace('\\', '/')
            # If the parser extracted imports, add import edges
            imports = f.get("imports", [])
            for imp in imports:
                module_name = imp.get("module", "")
                # Find if any file matches or ends with this module name
                for target_node in nodes:
                    if target_node["type"] == "file":
                        target_path = target_node["id"]
                        if target_path != file_path and (module_name in target_path or target_path.endswith(module_name)):
                            edges.append({
                                "source": file_path,
                                "target": target_path,
                                "type": "import"
                            })

        # Reference analysis: Check which chunks contain references to symbols in other files
        for c in chunks:
            source_file = c.file_path.replace('\\', '/')
            content = c.content
            
            # Simple keyword matching: check for symbol references
            for sym in all_symbol_names:
                if sym != c.symbol_name and sym in content:
                    target_file = symbol_to_file[sym]
                    if target_file != source_file:
                        # Edge from referencing file/symbol to the target definition
                        edges.append({
                            "source": source_file,
                            "target": target_file,
                            "type": "references"
                        })
                        if c.symbol_name:
                            source_sym_id = f"{source_file}::{c.symbol_name}"
                            target_sym_id = f"{target_file}::{sym}"
                            edges.append({
                                "source": source_sym_id,
                                "target": target_sym_id,
                                "type": "calls"
                            })

        # Deduplicate edges
        unique_edges = []
        seen_edges = set()
        for e in edges:
            edge_key = (e["source"], e["target"], e["type"])
            if edge_key not in seen_edges:
                seen_edges.add(edge_key)
                unique_edges.append(e)

        # Save to DB
        graph_doc = DependencyGraphDocument(
            repo_id=repo_id,
            nodes=nodes,
            edges=unique_edges
        )
        # Delete old graph if exists, then insert new one
        await DependencyGraphDocument.find(DependencyGraphDocument.repo_id == repo_id).delete()
        await graph_doc.insert()
        return graph_doc

    def analyze_impact(
        self,
        graph: DependencyGraphDocument,
        file_path: str,
        symbol_name: Optional[str] = None,
        algorithm: str = "bfs"
    ) -> Dict[str, Any]:
        """
        Run BFS or DFS to locate affected nodes when a file/symbol is changed.
        """
        normalized_file = file_path.replace('\\', '/')
        start_node = normalized_file
        if symbol_name:
            start_node = f"{normalized_file}::{symbol_name}"

        # Build adjacency list: target -> list of sources (incoming edges / dependencies)
        # Because we want to find "who depends on me", we traverse edges in REVERSE
        adj: Dict[str, List[str]] = collections.defaultdict(list)
        for e in graph.edges:
            # e["source"] depends on e["target"]. So modifying target affects source.
            adj[e["target"]].append(e["source"])

        # Traversal
        visited: Set[str] = set()
        queue = collections.deque([start_node])
        visited.add(start_node)
        
        # Track dependency chains/paths
        parent_map: Dict[str, str] = {}

        if algorithm.lower() == "dfs":
            # DFS Traversal
            stack = [start_node]
            while stack:
                curr = stack.pop()
                for neighbor in adj[curr]:
                    if neighbor not in visited:
                        visited.add(neighbor)
                        parent_map[neighbor] = curr
                        stack.append(neighbor)
        else:
            # BFS Traversal (Default)
            while queue:
                curr = queue.popleft()
                for neighbor in adj[curr]:
                    if neighbor not in visited:
                        visited.add(neighbor)
                        parent_map[neighbor] = curr
                        queue.append(neighbor)

        # Separate affected files and functions
        affected_files = set()
        affected_functions = set()
        for node_id in visited:
            if node_id == start_node:
                continue
            if "::" in node_id:
                affected_functions.add(node_id.split("::")[-1])
                affected_files.add(node_id.split("::")[0])
            else:
                affected_files.add(node_id)

        # Build dependency chains
        dependency_chain = []
        for leaf in visited:
            if leaf == start_node:
                continue
            chain = []
            curr = leaf
            while curr in parent_map:
                chain.append(curr)
                curr = parent_map[curr]
            chain.append(start_node)
            chain.reverse()
            dependency_chain.append(chain)

        # Calculate risk score
        w1 = 2.0
        w2 = 1.0
        w3 = 3.0
        
        # Calculate depth (maximum length of any dependency chain minus 1)
        depth = max((len(chain) - 1) for chain in dependency_chain) if dependency_chain else 0
        
        raw_score = (len(affected_files) * w1) + (len(affected_functions) * w2) + (depth * w3)
        # Scaled to 0-100 range, clamped at 100
        risk_score = min(100.0, raw_score * 5.0)

        return {
            "affected_files": list(affected_files),
            "affected_functions": list(affected_functions),
            "dependency_chain": dependency_chain,
            "risk_score": round(risk_score, 2)
        }
