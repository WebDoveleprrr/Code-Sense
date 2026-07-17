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
            if isinstance(f, dict):
                file_path = f.get("file_path", "").replace('\\', '/')
                imports = f.get("imports", [])
            else:
                file_path = str(f).replace('\\', '/')
                imports = []
                
            if not file_path:
                continue

            for imp in imports:
                module_name = imp.get("module", "")
                if not module_name:
                    continue
                # Normalize python-style dotted imports to slash paths
                module_path = module_name.replace('.', '/')
                
                # Find if any file matches or ends with this module name
                for target_node in nodes:
                    if target_node["type"] == "file":
                        target_path = target_node["id"]
                        # Strip extension for reliable matching (e.g., matching 'requests/api' against '.../requests/api.py')
                        target_path_no_ext = target_path.rsplit('.', 1)[0] if '.' in target_path else target_path
                        
                        if target_path != file_path and (target_path_no_ext == module_path or target_path_no_ext.endswith('/' + module_path)):
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
        Strictly follows OUTGOING dependencies for blast radius.
        """
        # Normalize user input path
        import re
        normalized_file = file_path.replace('\\', '/')
        # Strip leading dots or slashes
        normalized_file = re.sub(r'^(\./|/)+', '', normalized_file)
        
        start_node = None
        target_suffix = f"{normalized_file}::{symbol_name}" if symbol_name else normalized_file
        
        # Exact match first
        for node in graph.nodes:
            if node["id"] == target_suffix:
                start_node = node["id"]
                break
                
        # Suffix match (handles if graph has full absolute paths and frontend sends relative)
        if not start_node:
            for node in graph.nodes:
                if node["id"].endswith('/' + target_suffix) or node["id"].endswith('\\' + target_suffix):
                    start_node = node["id"]
                    break
        
        # Substring match as last resort
        if not start_node:
            for node in graph.nodes:
                if target_suffix in node["id"]:
                    start_node = node["id"]
                    break
                
        if not start_node:
            logger.warning(f"Impact Analysis: Node ending with '{target_suffix}' not found in graph.")
            return {
                "impact_score": 0.0,
                "risk_level": "Low",
                "score_reason": f"File not found in the dependency graph: {file_path}. Ensure it is indexed and has dependencies.",
                "affected_files": [],
                "affected_functions": [],
                "affected_classes": [],
                "incoming_dependencies": 0,
                "outgoing_dependencies": 0,
                "dependency_depth": 0,
                "fan_in": 0,
                "fan_out": 0,
                "traversal_order": [],
                "graph_nodes": [],
                "graph_edges": []
            }

        logger.info(f"[IMPACT ANALYSIS] Traversal start node: {start_node} via {algorithm}")

        node_dict = {n["id"]: n for n in graph.nodes}
        node_types = {n["id"]: n.get("type", "unknown") for n in graph.nodes}

        adj: Dict[str, List[str]] = collections.defaultdict(list)
        forward_adj: Dict[str, List[str]] = collections.defaultdict(list)
        for e in graph.edges:
            adj[e["target"]].append(e["source"])
            forward_adj[e["source"]].append(e["target"])

        fan_in = len(adj[start_node])
        fan_out = len(forward_adj[start_node])

        visited_set: Set[str] = set()
        visit_order: List[str] = []
        depth_map: Dict[str, int] = {start_node: 0}
        traversed_edges: Set[tuple] = set()
        
        # Traversal logic - strictly OUTGOING (forward_adj)
        if algorithm.lower() == "dfs":
            # True DFS using a stack of (current_node, parent_node, depth)
            stack = [(start_node, start_node, 0)]
            while stack:
                curr, parent, depth = stack.pop()
                if curr not in visited_set:
                    visited_set.add(curr)
                    visit_order.append(curr)
                    depth_map[curr] = depth
                    if parent != curr:
                        traversed_edges.add((parent, curr))
                    # Reverse so left-most children are visited first (optional but typical)
                    for neighbor in reversed(forward_adj[curr]):
                        if neighbor not in visited_set:
                            stack.append((neighbor, curr, depth + 1))
        else:
            # True BFS using a queue
            queue = collections.deque([(start_node, start_node, 0)])
            while queue:
                curr, parent, depth = queue.popleft()
                if curr not in visited_set:
                    visited_set.add(curr)
                    visit_order.append(curr)
                    depth_map[curr] = depth
                    if parent != curr:
                        traversed_edges.add((parent, curr))
                    for neighbor in forward_adj[curr]:
                        if neighbor not in visited_set:
                            queue.append((neighbor, curr, depth + 1))

        # Build subgraph of visited nodes
        subgraph_nodes = []
        for n_id in visit_order:
            if n_id in node_dict:
                subgraph_nodes.append(node_dict[n_id])

        subgraph_edges = []
        seen_edges = set()
        for e in graph.edges:
            # Include edge if it was actually traversed
            edge_key = (e["source"], e["target"])
            if edge_key in traversed_edges and edge_key not in seen_edges:
                subgraph_edges.append(e)
                seen_edges.add(edge_key)

        affected_files_list = []
        affected_functions_list = []
        affected_classes_list = []
        
        for n in subgraph_nodes:
            if n["type"] == "file":
                affected_files_list.append(n["id"])
            elif n["type"] == "function":
                affected_functions_list.append(n["id"])
            elif n["type"] == "class":
                affected_classes_list.append(n["id"])
                
        # Calculate impact score
        impact_score = min(100.0, (len(affected_files_list) * 5) + (len(affected_functions_list) * 2))
        risk_level = "Critical" if impact_score > 80 else "High" if impact_score > 50 else "Medium" if impact_score > 20 else "Low"

        # Logging as requested
        logger.info(
            f"Impact generation completed | Repo: {graph.repo_id} | Traversal: {algorithm.upper()} | "
            f"Start Node: {start_node} | Graph Nodes: {len(graph.nodes)} | Graph Edges: {len(graph.edges)} | "
            f"Visited Nodes: {len(subgraph_nodes)} | Impact Score: {impact_score}"
        )

        seen_files = set()
        seen_funcs = set()
        seen_classes = set()

        for node_id in visit_order:
            if node_id == start_node:
                continue
            ntype = node_types.get(node_id, "unknown")
            if "::" in node_id:
                base_name = node_id.split("::")[-1]
                if ntype in ("class", "struct", "interface"):
                    if base_name not in seen_classes:
                        affected_classes_list.append(base_name)
                        seen_classes.add(base_name)
                else:
                    if base_name not in seen_funcs:
                        affected_functions_list.append(base_name)
                        seen_funcs.add(base_name)
                
                file_name = node_id.split("::")[0]
                if file_name not in seen_files:
                    affected_files_list.append(file_name)
                    seen_files.add(file_name)
            else:
                if node_id not in seen_files:
                    affected_files_list.append(node_id)
                    seen_files.add(node_id)

        max_depth = max(depth_map.values()) if depth_map else 0
        total_repo_nodes = max(len(graph.nodes), 1)

        # Normalized Metrics for Weighted Scoring
        norm_files = min(len(affected_files_list) / 20.0, 1.0) * 100
        norm_depth = min(max_depth / 10.0, 1.0) * 100
        norm_fan_out = min(fan_out / 15.0, 1.0) * 100
        
        # Centrality approximation
        centrality = (fan_in + fan_out) / total_repo_nodes
        norm_centrality = min(centrality * 10.0, 1.0) * 100
        
        # Critical Bonus
        critical_bonus = 0
        if any(c in start_node for c in ['main', 'config', 'app', 'index', 'route']):
            critical_bonus = 100

        # Weighted Score Calculation
        score = (
            (norm_files * 0.35) +
            (norm_depth * 0.25) +
            (norm_fan_out * 0.20) +
            (norm_centrality * 0.15) +
            (critical_bonus * 0.05)
        )
        impact_score = min(100.0, score)

        # Risk Thresholds
        risk_level = "Low"
        if impact_score >= 75:
            risk_level = "Critical"
        elif impact_score >= 50:
            risk_level = "High"
        elif impact_score >= 25:
            risk_level = "Medium"

        reason = (
            f"Affects {len(affected_files_list)} files, dependency depth of {max_depth}, "
            f"fan-out of {fan_out}, and "
            f"{'high' if norm_centrality > 50 else 'low'} graph centrality."
        )

        return {
            "impact_score": round(impact_score, 2),
            "risk_level": risk_level,
            "score_reason": reason,
            "affected_files": affected_files_list,
            "affected_functions": affected_functions_list,
            "affected_classes": affected_classes_list,
            "incoming_dependencies": fan_in,
            "outgoing_dependencies": fan_out,
            "dependency_depth": max_depth,
            "fan_in": fan_in,
            "fan_out": fan_out,
            "traversal_order": visit_order,
            "graph_nodes": subgraph_nodes,
            "graph_edges": subgraph_edges
        }
