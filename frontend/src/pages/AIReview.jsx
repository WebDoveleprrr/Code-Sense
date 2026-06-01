// src/pages/AIReview.jsx
import React, { useState, useEffect } from "react";
import { repositoriesApi, reviewApi } from "../services/api";
import toast from "react-hot-toast";
import { Shield, Sparkles, Filter, ChevronDown, CheckCircle, AlertTriangle } from "lucide-react";

export default function AIReview() {
  const [repos, setRepos] = useState([]);
  const [selectedRepo, setSelectedRepo] = useState("");
  const [loading, setLoading] = useState(false);
  const [issues, setIssues] = useState([]);
  const [filterSeverity, setFilterSeverity] = useState("all");
  const [filterCategory, setFilterCategory] = useState("all");

  useEffect(() => {
    repositoriesApi.list()
      .then((data) => {
        setRepos(data);
        if (data.length > 0) setSelectedRepo(data[0].id);
      })
      .catch((err) => toast.error("Failed to load repositories: " + err.message));
  }, []);

  const handleRunReview = async () => {
    if (!selectedRepo) {
      toast.error("Please select a repository.");
      return;
    }
    setLoading(true);
    setIssues([]);
    try {
      const res = await reviewApi.analyze({ repo_id: selectedRepo });
      setIssues(res.issues || []);
      toast.success("AI review completed!");
    } catch (err) {
      toast.error(err.message || "Failed to run AI review");
    } finally {
      setLoading(false);
    }
  };

  const getSeverityBadge = (severity) => {
    switch (severity.toLowerCase()) {
      case "high":
        return "bg-rose-500/10 text-rose-400 border-rose-500/20";
      case "medium":
        return "bg-amber-500/10 text-amber-400 border-amber-500/20";
      default:
        return "bg-sky-500/10 text-sky-400 border-sky-500/20";
    }
  };

  const filteredIssues = issues.filter((issue) => {
    const sevMatch = filterSeverity === "all" || issue.severity.toLowerCase() === filterSeverity.toLowerCase();
    const catMatch = filterCategory === "all" || issue.category.toLowerCase() === filterCategory.toLowerCase();
    return sevMatch && catMatch;
  });

  return (
    <div className="p-8 max-w-7xl mx-auto space-y-8 font-sans text-slate-200">
      {/* Header */}
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4">
        <div>
          <h1 className="text-3xl font-extrabold bg-gradient-to-r from-purple-400 via-indigo-300 to-emerald-400 bg-clip-text text-transparent flex items-center gap-2">
            <Shield className="text-purple-400" />
            AI Code Review
          </h1>
          <p className="text-slate-400 mt-2 text-sm">
            Evidence-based architectural, performance, and security checks verified by AST analysis.
          </p>
        </div>

        <div className="flex items-center gap-3">
          <select
            value={selectedRepo}
            onChange={(e) => setSelectedRepo(e.target.value)}
            className="px-4 py-2.5 bg-slate-900 border border-slate-800 rounded-xl text-slate-200 focus:outline-none focus:ring-2 focus:ring-purple-500/40 text-sm"
          >
            {repos.map((r) => (
              <option key={r.id} value={r.id}>
                {r.name}
              </option>
            ))}
          </select>

          <button
            onClick={handleRunReview}
            disabled={loading}
            className="px-5 py-2.5 bg-gradient-to-r from-purple-600 to-indigo-600 hover:from-purple-500 hover:to-indigo-500 text-white rounded-xl font-medium shadow-lg hover:scale-[1.01] active:scale-[0.99] transition-all flex items-center gap-2 text-sm disabled:opacity-50"
          >
            {loading ? (
              <div className="w-5 h-5 border-2 border-white/30 border-t-white rounded-full animate-spin"></div>
            ) : (
              <>
                <Sparkles size={16} />
                Run Review
              </>
            )}
          </button>
        </div>
      </div>

      {/* Filters Bar */}
      {issues.length > 0 && (
        <div className="flex flex-wrap items-center gap-4 p-4 bg-slate-900/40 border border-slate-800 rounded-2xl">
          <div className="flex items-center gap-2 text-xs font-semibold text-slate-400 uppercase tracking-wider">
            <Filter size={14} />
            Filters:
          </div>

          <select
            value={filterSeverity}
            onChange={(e) => setFilterSeverity(e.target.value)}
            className="px-3 py-1.5 bg-slate-950/80 border border-slate-800 rounded-lg text-slate-300 text-xs focus:outline-none focus:ring-1 focus:ring-purple-500"
          >
            <option value="all">All Severities</option>
            <option value="high">High</option>
            <option value="medium">Medium</option>
            <option value="low">Low</option>
          </select>

          <select
            value={filterCategory}
            onChange={(e) => setFilterCategory(e.target.value)}
            className="px-3 py-1.5 bg-slate-950/80 border border-slate-800 rounded-lg text-slate-300 text-xs focus:outline-none focus:ring-1 focus:ring-purple-500"
          >
            <option value="all">All Categories</option>
            <option value="architecture">Architecture</option>
            <option value="security">Security</option>
            <option value="performance">Performance</option>
            <option value="maintainability">Maintainability</option>
            <option value="bug">Bug</option>
          </select>

          <div className="ml-auto text-xs text-slate-400 font-mono">
            Showing {filteredIssues.length} of {issues.length} issues
          </div>
        </div>
      )}

      {/* Issues List */}
      {issues.length > 0 ? (
        <div className="space-y-6">
          {filteredIssues.map((issue, idx) => (
            <div
              key={idx}
              className="p-6 bg-slate-900/30 backdrop-blur-sm border border-slate-800 hover:border-slate-700/80 rounded-2xl shadow-xl transition-all space-y-4"
            >
              {/* Severity, Category & File info */}
              <div className="flex flex-wrap items-center gap-3">
                <span className={`px-2.5 py-1 text-xs font-bold rounded-lg border uppercase tracking-wider ${getSeverityBadge(issue.severity)}`}>
                  {issue.severity}
                </span>

                <span className="text-xs font-semibold px-2 py-1 rounded bg-slate-800 border border-slate-700 text-slate-300 uppercase tracking-widest font-mono">
                  {issue.category}
                </span>

                <div className="text-xs text-slate-400 font-mono ml-auto">
                  File: <span className="text-purple-300">{issue.file}</span> {issue.line ? `(Line ${issue.line})` : ""}
                </div>
              </div>

              {/* Issue Description */}
              <div className="text-lg font-bold text-slate-200">
                {issue.issue}
              </div>

              {/* Evidence Snippet */}
              {issue.evidence && (
                <div className="p-3.5 bg-slate-950/95 border border-slate-800 rounded-xl">
                  <div className="text-[10px] text-slate-500 font-mono uppercase tracking-widest mb-1.5">Evidence Detected</div>
                  <pre className="text-xs font-mono text-emerald-400 overflow-x-auto whitespace-pre-wrap">
                    {issue.evidence}
                  </pre>
                </div>
              )}

              {/* Recommendations */}
              <div className="space-y-1.5">
                <div className="text-xs font-bold text-purple-400 tracking-wide uppercase">Actionable Recommendation:</div>
                <div className="text-sm text-slate-300 leading-relaxed font-sans">
                  {issue.recommendation}
                </div>
              </div>
            </div>
          ))}

          {filteredIssues.length === 0 && (
            <div className="text-center py-12 text-slate-500 font-mono text-sm">
              No issues match selected filters.
            </div>
          )}
        </div>
      ) : (
        !loading && (
          <div className="flex flex-col items-center justify-center text-center p-16 bg-slate-900/20 border border-dashed border-slate-800 rounded-3xl">
            <CheckCircle className="w-12 h-12 text-emerald-500/80 mb-3" />
            <div className="text-base font-bold text-slate-300">Clean Bill of Health</div>
            <p className="text-slate-500 text-xs mt-1.5 max-w-sm leading-relaxed">
              No code reviews run yet or repository is clean. Run a review scan using the top-right button.
            </p>
          </div>
        )
      )}
    </div>
  );
}
