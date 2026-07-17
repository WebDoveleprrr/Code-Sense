# backend/app/services/review_service.py
from __future__ import annotations

import re
from typing import Any, Dict, List, Optional
from pathlib import Path

from app_logger import logger
from app.models.repository import RepositoryDocument
from app.models.review_report import ReviewReportDocument
from app.db.ml.llm_client import complete
from app.core.config import get_settings

class ReviewService:
    """
    Automated code review service running static rule scans and LLM analysis.
    """

    async def run_review(self, repo_id: str) -> Dict[str, Any]:
        """
        Run static rule checks across the repository.
        """
        import time
        t0 = time.perf_counter()
        
        repo = await RepositoryDocument.get(repo_id)
        if not repo:
            raise ValueError(f"Repository {repo_id} not found.")

        settings = get_settings()
        repo_dir = settings.UPLOAD_DIR / repo_id

        issues = []
        if repo_dir.exists():
            issues = self._run_static_rules(repo_dir)
            
        # Add LLM Analysis to guarantee repository-specific findings
        try:
            meta = repo.repo_metadata or {}
            files = meta.get("files", [])
            file_names = [f.get("file_path", "") for f in files[:20]]
            
            system_prompt = "You are a senior software architect performing a code review."
            user_prompt = f"""
            Analyze the following repository structure and generate 2 to 3 insightful code quality or architecture issues.
            Language breakdown: {repo.language_breakdown}
            Total files: {repo.total_files}
            Sample files: {file_names}
            
            Format your response STRICTLY as a JSON array with NO markdown blocks and NO surrounding text:
            [
              {{
                 "severity": "Medium",
                 "category": "Maintainability",
                 "issue": "Brief issue title",
                 "file": "path/to/file",
                 "line": 1,
                 "confidence": 0.85,
                 "why_it_matters": "Why this matters architecturally",
                 "evidence": "Supporting evidence based on the context",
                 "recommendation": "How to fix it"
              }}
            ]
            """
            
            llm_res = await complete(system_prompt, user_prompt)
            import json
            
            clean_res = llm_res.strip()
            if clean_res.startswith("```json"):
                clean_res = clean_res[7:]
            elif clean_res.startswith("```"):
                clean_res = clean_res[3:]
            if clean_res.endswith("```"):
                clean_res = clean_res[:-3]
            
            llm_issues = json.loads(clean_res.strip())
            if isinstance(llm_issues, list):
                for issue in llm_issues:
                    # ensure correct keys
                    if "severity" in issue and "issue" in issue:
                        issues.append(issue)
        except Exception as e:
            logger.warning(f"LLM review analysis failed or skipped: {e}")

        # Apply confidence score to fit the response model if missing
        seen_recs = set()
        recommendations = []
        for issue in issues:
            if "confidence" not in issue:
                issue["confidence"] = 0.95
            if "why_it_matters" not in issue:
                issue["why_it_matters"] = "Could impact maintainability or security."
            if "recommendation" in issue:
                rec = issue["recommendation"].strip()
                if rec and rec not in seen_recs:
                    seen_recs.add(rec)
                    recommendations.append(rec)

        # Dynamic Scoring Calculation
        security_score = 10.0
        quality_score = 10.0
        maintain_score = 10.0
        perf_score = 10.0

        high_issues = 0
        medium_issues = 0
        low_issues = 0

        for issue in issues:
            sev = issue.get("severity", "Low").lower()
            cat = issue.get("category", "Code Quality")
            
            penalty = 2.0 if sev == "high" else 1.0 if sev == "medium" else 0.2
            
            if sev == "high": high_issues += 1
            elif sev == "medium": medium_issues += 1
            else: low_issues += 1

            if cat == "Security": security_score = max(0.0, security_score - penalty)
            elif cat == "Code Quality": quality_score = max(0.0, quality_score - penalty)
            elif cat == "Maintainability": maintain_score = max(0.0, maintain_score - penalty)
            elif cat == "Performance": perf_score = max(0.0, perf_score - penalty)
            else: quality_score = max(0.0, quality_score - penalty)

        overall_score = (security_score + quality_score + maintain_score + perf_score) / 4.0

        if high_issues > 0:
            summary = f"Critical security vulnerabilities or major maintainability issues detected ({high_issues} high severity). Immediate attention required."
        elif medium_issues > 0:
            summary = f"The repository demonstrates a solid foundation, but there are several medium-severity issues ({medium_issues}) that should be addressed."
        elif low_issues > 0:
            summary = f"The repository is generally healthy. A few minor low-severity issues were found."
        else:
            summary = "Repository appears healthy. No significant issues were detected."
            if not recommendations:
                recommendations.append("No significant issues detected. Keep up the good work!")

        # Save to DB
        report_doc = ReviewReportDocument(
            repo_id=repo_id,
            issues=issues
        )
        await ReviewReportDocument.find(ReviewReportDocument.repo_id == repo_id).delete()
        await report_doc.insert()

        import time
        from datetime import datetime
        t1 = time.perf_counter()
        
        provider = get_settings().LLM_PROVIDER
        model_name = get_settings().OLLAMA_MODEL if provider == "ollama" else get_settings().OPENAI_MODEL if provider == "openai" else get_settings().GEMINI_MODEL

        return {
            "success": True,
            "repo_id": repo_id,
            "issues": issues,
            "scores": {
                "overall": round(overall_score, 1),
                "quality": round(quality_score, 1),
                "security": round(security_score, 1),
                "maintainability": round(maintain_score, 1),
                "performance": round(perf_score, 1)
            },
            "summary": summary,
            "recommendations": recommendations,
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "duration_ms": int((t1 - t0) * 1000),
            "model": model_name
        }

    def _run_static_rules(self, repo_dir: Path) -> List[Dict[str, Any]]:
        issues = []
        secrets_pattern = re.compile(r'(?i)(api_key|secret|password|token|credentials|private_key)\s*[:=]\s*["\'][a-zA-Z0-9_\-\+\/]{16,}["\']')
        eval_pattern = re.compile(r'\beval\s*\(')
        exec_pattern = re.compile(r'\bexec\s*\(')
        subprocess_shell_pattern = re.compile(r'subprocess\.[a-z_]+\([^)]*shell\s*=\s*True')
        crypto_pattern = re.compile(r'\b(hashlib\.(md5|sha1)|crypto\.(md5|sha1))\b', re.IGNORECASE)
        todo_pattern = re.compile(r'(?i)#\s*(TODO|FIXME|HACK|DEPRECATED)')
        bare_except_pattern = re.compile(r'^\s*except\s*:\s*$|^\s*except\s+Exception\s*:\s*$')
        import_pattern = re.compile(r'^\s*(import\s+[\w\.]+|^from\s+[\w\.]+\s+import\s+[\w\., ]+)', re.MULTILINE)

        for file_path in repo_dir.rglob("*"):
            if file_path.is_file() and file_path.suffix in (".py", ".js", ".ts", ".cpp", ".c", ".h", ".go", ".rs", ".java"):
                is_test_file = "test_" in file_path.name or "_test" in file_path.name
                
                try:
                    content = file_path.read_text(encoding="utf-8", errors="ignore")
                    relative_path = str(file_path.relative_to(repo_dir)).replace('\\', '/')
                    lines = content.splitlines()
                    
                    if len(lines) > 300:
                        issues.append({
                            "severity": "Low",
                            "category": "Maintainability",
                            "issue": "Extremely long file",
                            "file": relative_path,
                            "line": 1,
                            "confidence": 1.0,
                            "why_it_matters": "Files over 300 lines become hard to navigate and often violate the Single Responsibility Principle.",
                            "evidence": f"File has {len(lines)} lines",
                            "recommendation": "Consider splitting this file into smaller, cohesive modules."
                        })
                    
                    imports = import_pattern.findall(content)
                    if len(imports) > 15:
                        issues.append({
                            "severity": "Medium",
                            "category": "Code Quality",
                            "issue": "High number of imports",
                            "file": relative_path,
                            "line": 1,
                            "confidence": 1.0,
                            "why_it_matters": "A high number of imports indicates tight coupling and potential architectural bottlenecks.",
                            "evidence": f"{len(imports)} imports detected",
                            "recommendation": "High coupling detected. Consider refactoring to reduce dependencies."
                        })

                    func_start = -1
                    func_name = ""
                    
                    for idx, line in enumerate(lines, 1):
                        stripped = line.strip()
                        if not stripped: continue
                        
                        # High Severity: Secrets
                        if secrets_pattern.search(line):
                            issues.append({
                                "severity": "High", "category": "Security", "issue": "Hardcoded secret or API key",
                                "file": relative_path, "line": idx, "confidence": 1.0, 
                                "why_it_matters": "Hardcoded secrets can be exposed in version control, leading to unauthorized access.",
                                "evidence": line.strip()[:100],
                                "recommendation": "Use environment variables or a secure vault for secrets."
                            })
                            
                        if not is_test_file:
                            # High: Security
                            if eval_pattern.search(line) or exec_pattern.search(line):
                                issues.append({
                                    "severity": "High", "category": "Security", "issue": "Unsafe eval/exec usage",
                                    "file": relative_path, "line": idx, "confidence": 1.0,
                                    "why_it_matters": "Using eval or exec on untrusted input can lead to arbitrary code execution.",
                                    "evidence": line.strip(),
                                    "recommendation": "Avoid eval() or exec() to prevent arbitrary code execution."
                                })
                            if subprocess_shell_pattern.search(line):
                                issues.append({
                                    "severity": "High", "category": "Security", "issue": "subprocess with shell=True",
                                    "file": relative_path, "line": idx, "confidence": 1.0,
                                    "why_it_matters": "shell=True allows attackers to execute arbitrary shell commands if inputs are untrusted.",
                                    "evidence": line.strip(),
                                    "recommendation": "Avoid shell=True as it can lead to shell injection vulnerabilities."
                                })
                            if crypto_pattern.search(line):
                                issues.append({
                                    "severity": "Medium", "category": "Security", "issue": "Weak cryptography (md5/sha1)",
                                    "file": relative_path, "line": idx, "confidence": 1.0,
                                    "why_it_matters": "MD5 and SHA-1 are cryptographically broken and vulnerable to collision attacks.",
                                    "evidence": line.strip(),
                                    "recommendation": "Use stronger algorithms like SHA-256 or bcrypt/argon2."
                                })
                            
                            # Medium: Maintainability / Quality
                            if bare_except_pattern.search(line):
                                issues.append({
                                    "severity": "Medium", "category": "Code Quality", "issue": "Broad exception handling",
                                    "file": relative_path, "line": idx, "confidence": 1.0,
                                    "why_it_matters": "Catching generic Exceptions masks unexpected bugs and makes debugging difficult.",
                                    "evidence": line.strip(),
                                    "recommendation": "Catch specific exceptions instead of using a bare except."
                                })
                                
                            if todo_pattern.search(line):
                                issues.append({
                                    "severity": "Low", "category": "Maintainability", "issue": "Unresolved TODO/FIXME comment",
                                    "file": relative_path, "line": idx, "confidence": 1.0,
                                    "why_it_matters": "Unresolved comments indicate incomplete work or technical debt.",
                                    "evidence": line.strip()[:100],
                                    "recommendation": "Resolve the pending work or track it in an issue tracker."
                                })
                                
                        # Function length check
                        if file_path.suffix in (".py", ".js", ".ts"):
                            if line.startswith("def ") or line.startswith("function ") or "=>" in line:
                                if func_start != -1 and (idx - func_start) > 50:
                                    issues.append({
                                        "severity": "Medium", "category": "Code Quality", "issue": "Long function detected",
                                        "file": relative_path, "line": func_start, "confidence": 1.0,
                                        "why_it_matters": "Long functions are harder to read, test, and maintain.",
                                        "evidence": f"Function {func_name} is {idx - func_start} lines long.",
                                        "recommendation": "Refactor this function to be shorter and focused on a single responsibility."
                                    })
                                func_start = idx
                                func_name = line.split("(")[0].replace("def ", "").replace("function ", "").strip()
                            elif not line.startswith(" ") and not line.startswith("\t") and stripped and not line.startswith("@") and not line.startswith("export") and not line.startswith("const"):
                                if func_start != -1 and (idx - func_start) > 50:
                                    issues.append({
                                        "severity": "Medium", "category": "Code Quality", "issue": "Long function detected",
                                        "file": relative_path, "line": func_start, "confidence": 1.0,
                                        "why_it_matters": "Long functions are harder to read, test, and maintain.",
                                        "evidence": f"Function {func_name} is {idx - func_start} lines long.",
                                        "recommendation": "Refactor this function to be shorter and focused on a single responsibility."
                                    })
                                func_start = -1
                except Exception as e:
                    logger.warning(f"Static analysis failed for {file_path}: {e}")
                    
        return issues
