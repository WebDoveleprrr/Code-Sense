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

    # Create nodes with normalized forward slashes
    for f in files:
        normalized_path = f["file_path"].replace('\\', '/')
        nodes.append({
            "id": normalized_path,
            "label": normalized_path.split('/')[-1],
            "language": f["language"],
            "file_path": normalized_path,
            "type": "file"
        })

    # Extract import edges if files exist on disk
    if repo_dir.exists():
        file_paths = {f["file_path"].replace('\\', '/') for f in files}
        
        for f in files:
            source_path = f["file_path"].replace('\\', '/')
            path = repo_dir / source_path
            if not path.exists():
                continue
                
            try:
                content = path.read_text(encoding="utf-8", errors="ignore")
                
                # Basic python import detection
                if f["language"].lower() == "python":
                    # matches: import foo.bar or from foo import bar
                    import_pattern = re.compile(r'^\s*(?:from\s+([a-zA-Z0-9_\.]+)\s+import|import\s+([a-zA-Z0-9_\., \t]+))', re.MULTILINE)
                    for match in import_pattern.finditer(content):
                        module_base = match.group(1) or match.group(2)
                        if module_base:
                            module_base = module_base.strip().split(',')[0].strip()
                            
                            # Handle relative vs absolute imports
                            if module_base.startswith('.'):
                                dots_count = len(module_base) - len(module_base.lstrip('.'))
                                module_name = module_base.lstrip('.')
                                
                                parts = source_path.split('/')[:-1]
                                if dots_count > 1 and len(parts) >= (dots_count - 1):
                                    parts = parts[:-(dots_count - 1)]
                                
                                target_dir = "/".join(parts)
                                if target_dir:
                                    target_base = f"{target_dir}/{module_name}" if module_name else target_dir
                                else:
                                    target_base = module_name
                            else:
                                target_base = module_base.replace('.', '/')
                                
                            possible_targets = [f"{target_base}.py", f"{target_base}/__init__.py"]
                            for pt in possible_targets:
                                matched = next((fp for fp in file_paths if fp.endswith(pt) or fp == pt), None)
                                if matched and matched != source_path:
                                    edges.append({
                                        "source": source_path,
                                        "target": matched,
                                        "type": "import"
                                    })
                                    break
                                    
                # Basic JS/TS import detection
                elif f["language"].lower() in ("javascript", "typescript"):
                    # matches: import ... from './path' or require('./path')
                    import_pattern = re.compile(r'(?:import.*from|require\()\s*[\'"]([^\'"]+)[\'"]', re.MULTILINE)
                    for match in import_pattern.finditer(content):
                        target = match.group(1)
                        if target.startswith('.'):
                            base_dir = "/".join(source_path.split('/')[:-1])
                            target_name = target.split('/')[-1]
                            matched = next((fp for fp in file_paths if target_name in fp and fp.startswith(base_dir)), None)
                            if matched and matched != source_path:
                                edges.append({
                                    "source": source_path,
                                    "target": matched,
                                    "type": "import"
                                })
                                break
            except Exception:
                pass

    return nodes, edges
