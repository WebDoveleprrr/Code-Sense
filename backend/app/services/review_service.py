# backend/app/services/review_service.py
from __future__ import annotations

import re
from typing import Any, Dict, List, Optional
from pathlib import Path

from app_logger import logger
from app.models.repository import RepositoryDocument
from app.models.review_report import ReviewReportDocument
from app.ml.llm_client import complete
from app.core.config import get_settings

class ReviewService:
    """
    Automated code review service running static rule scans and LLM analysis.
    """

    async def run_review(self, repo_id: str) -> Dict[str, Any]:
        """
        Run static rule checks, then run LLM verification in parallel, and store results.
        """
        repo = await RepositoryDocument.get(repo_id)
        if not repo:
            raise ValueError(f"Repository {repo_id} not found.")

        settings = get_settings()
        repo_dir = settings.UPLOAD_DIR / repo_id

        # 1. Static Rule Engine Scan
        static_issues = []
        if repo_dir.exists():
            static_issues = self._run_static_rules(repo_dir)

        # 2. Parallel LLM Verification and Semantic Review
        files = repo.repo_metadata.get("files", [])
        llm_issues = []
        
        # We review the top 5 largest or most complex files
        files_to_review = sorted(files, key=lambda x: x.get("line_count", 0), reverse=True)[:5]
        
        import asyncio
        tasks = []
        for f in files_to_review:
            file_path = f["file_path"]
            abs_path = repo_dir / file_path
            if abs_path.exists():
                tasks.append(self._run_file_review(file_path, abs_path))
                
        results = await asyncio.gather(*tasks, return_exceptions=True)
        for r in results:
            if isinstance(r, list):
                llm_issues.extend(r)

        # Combine issues and assign confidence scores
        combined_issues = []
        for issue in static_issues:
            issue["confidence"] = 0.95
            combined_issues.append(issue)

        for issue in llm_issues:
            if "confidence" not in issue:
                issue["confidence"] = 0.80
            combined_issues.append(issue)

        # Save to DB
        report_doc = ReviewReportDocument(
            repo_id=repo_id,
            issues=combined_issues
        )
        await ReviewReportDocument.find(ReviewReportDocument.repo_id == repo_id).delete()
        await report_doc.insert()

        return {
            "success": True,
            "repo_id": repo_id,
            "issues": combined_issues
        }

    async def _run_file_review(self, file_path: str, abs_path: Path) -> List[Dict[str, Any]]:
        # Avoid verifying test files for security/performance issues unless actual secrets are present
        is_test_file = "test_" in file_path or "_test" in file_path
        
        try:
            content = abs_path.read_text(encoding="utf-8", errors="ignore")
            if not content.strip():
                return []
                
            evidence_list = []
            lines = content.splitlines()
            
            # Static scan 1: Long methods / cognitive complexity
            if len(lines) > 150:
                evidence_list.append(f"File has {len(lines)} lines of code (potential maintainability smell).")
                
            # Static scan 2: Secrets check
            secrets_pattern = re.compile(r'(?i)(api_key|secret|password|token|credentials|private_key)\s*[:=]\s*["\'][a-zA-Z0-9_\-\+\/]{16,}["\']')
            for idx, line in enumerate(lines, 1):
                if secrets_pattern.search(line):
                    evidence_list.append(f"L{idx}: Potential hardcoded secret or API key matching pattern: '{line.strip()[:40]}...'")

            # Static scan 3: Nested loops
            nested_loop_pattern = re.compile(r'for\s*\(.*\)\s*\{[^{}]*for\s*\(.*\)\s*\{|for\s+[a-zA-Z0-9_]+\s+in\s+.*:\s*\n\s+for\s+[a-zA-Z0-9_]+\s+in\s+.*:')
            for idx, line in enumerate(lines, 1):
                if nested_loop_pattern.search(line) or (idx < len(lines) and "for " in line and "for " in lines[idx]):
                    evidence_list.append(f"L{idx}: Deeply nested loop structure detected (potential performance issue).")
                    
            # Static scan 4: Circular or excessive imports check
            imports_count = sum(1 for line in lines if line.strip().startswith(("import ", "from ")) )
            if imports_count > 15:
                evidence_list.append(f"Excessive imports ({imports_count}) in file (potential high coupling architecture smell).")

            # If it's a test file and no actual hardcoded secret was found, filter out performance and security alerts
            if is_test_file:
                evidence_list = [e for e in evidence_list if "secret" in e.lower()]

            # Feed to LLM with gathered static evidence
            evidence_str = "\n".join(evidence_list) if evidence_list else "None detected statically."
            return await self._run_llm_analysis(file_path, content, evidence_str)
        except Exception as e:
            logger.warning(f"Static file review failed for {file_path}: {e}")
            return []

    def _run_static_rules(self, repo_dir: Path) -> List[Dict[str, Any]]:
        issues = []
        secrets_pattern = re.compile(r'(?i)(api_key|secret|password|token|credentials|private_key)\s*[:=]\s*["\'][a-zA-Z0-9_\-\+\/]{16,}["\']')
        eval_pattern = re.compile(r'\beval\s*\(')
        pickle_pattern = re.compile(r'\bpickle\.loads\b')

        for file_path in repo_dir.rglob("*"):
            # Skip test files for static alerts unless they contain clear secrets/eval issues
            is_test_file = "test_" in file_path.name or "_test" in file_path.name
            
            if file_path.is_file() and file_path.suffix in (".py", ".js", ".ts", ".cpp", ".c", ".h"):
                try:
                    content = file_path.read_text(encoding="utf-8", errors="ignore")
                    relative_path = str(file_path.relative_to(repo_dir)).replace('\\', '/')
                    lines = content.splitlines()
                    
                    # Search Secrets
                    for idx, line in enumerate(lines, 1):
                        if secrets_pattern.search(line):
                            issues.append({
                                "severity": "High",
                                "category": "Security",
                                "issue": "Potential hardcoded secret or API key",
                                "file": relative_path,
                                "line": idx,
                                "evidence": line.strip(),
                                "recommendation": "Move secrets to environment variables or config files."
                            })

                    # Search Eval usage (exclude test files to avoid false positives)
                    if not is_test_file:
                        for idx, line in enumerate(lines, 1):
                            if eval_pattern.search(line):
                                issues.append({
                                    "severity": "High",
                                    "category": "Security",
                                    "issue": "Unsafe eval usage detected",
                                    "file": relative_path,
                                    "line": idx,
                                    "evidence": line.strip(),
                                    "recommendation": "Avoid using eval() as it can lead to arbitrary code execution."
                                })

                        for idx, line in enumerate(lines, 1):
                            if pickle_pattern.search(line):
                                issues.append({
                                    "severity": "Medium",
                                    "category": "Security",
                                    "issue": "Insecure deserialization using pickle",
                                    "file": relative_path,
                                    "line": idx,
                                    "evidence": line.strip(),
                                    "recommendation": "Use safer serialization alternatives like json or safetensors."
                                })
                except Exception as e:
                    logger.warning(f"Static analysis failed for {file_path}: {e}")
                    
        return issues

    async def _run_llm_analysis(self, file_path: str, content: str, static_evidence: str) -> List[Dict[str, Any]]:
        system_prompt = (
            "You are an expert static analyzer, principal architect, and security auditor.\n\n"
            "Analyze the given source code file and identify actual issues matching the static evidence provided.\n"
            "Strict Rules:\n"
            "1. Base findings strictly on the code content. If no issue exists, return an empty list [].\n"
            "2. If it is a test file, DO NOT report security warnings (unless it contains hardcoded production passwords/secrets) or performance smells.\n"
            "3. Every reported issue MUST have an exact 'line' number and a concrete snippet in the 'evidence' key. If there is no specific code evidence, DO NOT report it.\n\n"
            "Respond ONLY with a valid JSON list of issues matching this format:\n"
            "[\n"
            "  {\n"
            "    \"severity\": \"High\" | \"Medium\" | \"Low\",\n"
            "    \"category\": \"Architecture\" | \"Security\" | \"Performance\" | \"Maintainability\" | \"Bug\",\n"
            "    \"issue\": \"Short issue description\",\n"
            "    \"file\": \"path/to/file\",\n"
            "    \"line\": 10,\n"
            "    \"evidence\": \"exact line of code causing this issue\",\n"
            "    \"recommendation\": \"Detailed, actionable recommendation on how to fix this issue with code examples if helpful.\",\n"
            "    \"confidence\": 0.8\n"
            "  }\n"
            "]\n"
            "Do not include markdown code blocks, intro, or explanation outside the JSON."
        )

        user_prompt = (
            f"File: {file_path}\n"
            f"Static Evidence Gathered:\n{static_evidence}\n\n"
            f"Content:\n{content[:4000]}"
        )
        
        try:
            raw_response = await complete(system_prompt, user_prompt)
            import json
            clean_response = re.sub(r"^```json\s*", "", raw_response, flags=re.IGNORECASE)
            clean_response = re.sub(r"\s*```$", "", clean_response, flags=re.IGNORECASE).strip()
            
            issues = json.loads(clean_response)
            if isinstance(issues, list):
                valid_issues = []
                for issue in issues:
                    # Double check evidence and fields
                    if issue.get("evidence") and issue.get("line"):
                        issue["file"] = file_path.replace('\\', '/')
                        valid_issues.append(issue)
                return valid_issues
        except Exception as e:
            logger.warning(f"Failed to parse LLM code review response: {e}")
            
        return []
