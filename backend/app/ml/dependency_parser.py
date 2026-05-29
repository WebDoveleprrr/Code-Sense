# backend/app/ml/dependency_parser.py
"""
CodeSense — Dependency Graph Parser
"""

from typing import Tuple, List, Dict, Any
import re
from pathlib import Path
from app.models.repository import RepositoryDocument
from app.core.config import get_settings

async def parse_dependencies(repo: RepositoryDocument) -> Tuple[List[Dict[str, Any]], List[Dict[str, Any]]]:
    """
    Parse repository files to extract dependency nodes and edges.
    """
    settings = get_settings()
    repo_dir = settings.UPLOAD_DIR / str(repo.id)
    
    nodes = []
    edges = []
    
    files = repo.repo_metadata.get("files", [])
    if not files:
        return nodes, edges

    # Create nodes
    for f in files:
        nodes.append({
            "id": f["file_path"],
            "label": f["file_path"].split('/')[-1],
            "language": f["language"],
            "file_path": f["file_path"],
            "type": "file"
        })

    # Try to extract simple import edges if files exist on disk
    if repo_dir.exists():
        file_paths = {f["file_path"] for f in files}
        
        for f in files:
            path = repo_dir / f["file_path"]
            if not path.exists():
                continue
                
            try:
                content = path.read_text(encoding="utf-8", errors="ignore")
                # Basic python import detection
                if f["language"] == "python":
                    # matches: import foo.bar or from foo import bar
                    import_pattern = re.compile(r'^(?:from\s+([a-zA-Z0-9_\.]+)\s+import|import\s+([a-zA-Z0-9_\.,\s]+))', re.MULTILINE)
                    for match in import_pattern.finditer(content):
                        module_base = match.group(1) or match.group(2)
                        if module_base:
                            module_parts = module_base.strip().split(',')[0].strip().split('.')
                            # guess target file path
                            target_base = "/".join(module_parts)
                            possible_targets = [f"{target_base}.py", f"{target_base}/__init__.py"]
                            for pt in possible_targets:
                                # We do a simplistic check if it's in our file list
                                # In a real app we'd resolve properly
                                matched = next((fp for fp in file_paths if fp.endswith(pt)), None)
                                if matched:
                                    edges.append({
                                        "source": f["file_path"],
                                        "target": matched,
                                        "type": "import"
                                    })
                                    break
                # Basic JS/TS import detection
                elif f["language"] in ("javascript", "typescript"):
                    # matches: import ... from './path' or require('./path')
                    import_pattern = re.compile(r'(?:import.*from|require\()\s*[\'"]([^\'"]+)[\'"]', re.MULTILINE)
                    for match in import_pattern.finditer(content):
                        target = match.group(1)
                        if target.startswith('.'):
                            # simplistic resolution
                            base_dir = "/".join(f["file_path"].split('/')[:-1])
                            target_name = target.split('/')[-1]
                            matched = next((fp for fp in file_paths if target_name in fp and fp.startswith(base_dir)), None)
                            if matched:
                                edges.append({
                                    "source": f["file_path"],
                                    "target": matched,
                                    "type": "import"
                                })
                                break

            except Exception:
                pass

    return nodes, edges
