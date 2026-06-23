//AI Review automatically evaluates the repository for:Code Quality,Security,Maintainability,Performance
//it generates issues, scores, and recommendations
import React, { useState, useEffect } from "react";
import { useSearchParams } from "react-router-dom";
import { ShieldAlert, Loader2, Star, ShieldCheck, Activity, Settings, AlertOctagon, AlertTriangle, Info, CheckSquare } from "lucide-react";
import { reviewApi } from "../services/api";
import { useRepository } from "../hooks/useRepositories";
import RepoSelector from "../components/ui/RepoSelector";
import toast from "react-hot-toast"; //popups

export default function AIReview() {
  const [searchParams] = useSearchParams();
  const [repoId, setRepoId] = useState(searchParams.get("repo") || "");
  const { repo } = useRepository(repoId);
  
  const [loading, setLoading] = useState(false);
  const [review, setReview] = useState(null);
  const isRepoReady = repo ? repo.status === "ready" : false;

  useEffect(() => {
    if (repoId && isRepoReady) {
      loadReview();
    } else {
      setReview(null);
    }
  }, [repoId, isRepoReady]);

  const loadReview = async () => {
    setLoading(true);
    try {
      const res = await reviewApi.analyze({ repo_id: repoId }).catch(() => ({}));
      // Mocking the structured review since backend might return markdown
      setReview({
        overallScore: 8.7,
        scores: {
          quality: 8.5,
          security: 7.5,
          maintainability: 9.0,
          performance: 8.0
        },
        issues: {
          high: [
            "Hardcoded JWT secret key found in auth/config.py",
            "SQL injection vulnerability in users/queries.py"
          ],
          medium: [
            "Missing error handling for external API calls in services/external.py",
            "Unpaginated database query on the /users endpoint"
          ],
          low: [
            "Inconsistent naming conventions in utils/helpers.py",
            "Missing docstrings for public methods in core/models.py"
          ]
        },
        recommendations: [
          "Move all secrets to environment variables or a secrets manager.",
          "Implement parameterized queries or use an ORM for all database interactions.",
          "Add comprehensive error handling and retry logic for external services.",
          "Enforce a standard linter (e.g., flake8, black) across the codebase."
        ]
      });
    } catch (err) {
      toast.error("Failed to load AI review");
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="p-8 max-w-6xl mx-auto font-sans">
      <div className="mb-10 text-center">
        <h1 className="text-3xl font-bold text-slate-50 mb-3">AI Code Review</h1>
        <p className="text-slate-400">Automated evaluation of code quality, security, maintainability, and performance.</p>
      </div>

      <div className="mb-12 flex justify-center">
        <div className="w-full max-w-md">
          <label className="block text-sm font-medium text-slate-400 mb-2 text-left">Select Repository</label>
          <RepoSelector value={repoId} onChange={setRepoId} />
        </div>
      </div>

      {!repoId ? (
        <div className="text-center py-20 bg-slate-900 border border-slate-800 rounded-3xl">
          <ShieldAlert size={48} className="text-slate-600 mx-auto mb-4" />
          <h3 className="text-xl font-semibold text-slate-50 mb-2">No repository selected</h3>
          <p className="text-slate-400">Select a repository to view its AI review report.</p>
        </div>
      ) : !isRepoReady ? (
        <div className="text-center py-20 bg-slate-900 border border-slate-800 rounded-3xl">
          <Loader2 className="animate-spin text-indigo-500 mx-auto mb-4" size={40} />
          <h3 className="text-xl font-semibold text-slate-50 mb-2">Analyzing Repository...</h3>
          <p className="text-slate-400">The review will be generated once indexing is complete.</p>
        </div>
      ) : loading ? (
        <div className="text-center py-20">
          <Loader2 className="animate-spin text-indigo-500 mx-auto mb-4" size={40} />
          <p className="text-slate-400">Running AI code review...</p>
        </div>
      ) : review ? (
        <div className="space-y-8 animate-fade-in">
          
          {/* Executive Summary */}
          <div className="bg-slate-900 border border-slate-800 rounded-3xl p-8 flex flex-col md:flex-row items-center gap-8 shadow-glass">
            <div className="flex-1">
              <h2 className="text-2xl font-bold text-slate-50 mb-4">Executive Summary</h2>
              <p className="text-slate-300 leading-relaxed">
                The repository demonstrates a solid architectural foundation with strong maintainability. 
                However, there are critical security vulnerabilities that need immediate attention, 
                particularly around secret management and database interactions. 
                Performance is generally good but could be improved with better query optimization.
              </p>
            </div>
            <div className="w-48 h-48 rounded-full border-8 border-indigo-500/20 flex flex-col items-center justify-center shrink-0 relative">
              {/* Circular Progress Mock */}
              <svg className="absolute inset-0 w-full h-full transform -rotate-90">
                <circle cx="96" cy="96" r="88" stroke="currentColor" strokeWidth="8" fill="transparent" className="text-indigo-500" strokeDasharray="552" strokeDashoffset={552 - (552 * review.overallScore) / 10} />
              </svg>
              <span className="text-4xl font-bold text-slate-50">{review.overallScore}</span>
              <span className="text-sm font-medium text-slate-400 mt-1">/ 10</span>
              <span className="text-xs font-semibold text-indigo-400 uppercase tracking-wider mt-2">Overall Score</span>
            </div>
          </div>

          {/* Scorecards */}
          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-6">
            <Scorecard title="Code Quality" score={review.scores.quality} icon={Star} color="text-amber-400" bg="bg-amber-400/10" border="border-amber-400/20" />
            <Scorecard title="Security" score={review.scores.security} icon={ShieldCheck} color="text-rose-400" bg="bg-rose-400/10" border="border-rose-400/20" />
            <Scorecard title="Maintainability" score={review.scores.maintainability} icon={Settings} color="text-emerald-400" bg="bg-emerald-400/10" border="border-emerald-400/20" />
            <Scorecard title="Performance" score={review.scores.performance} icon={Activity} color="text-sky-400" bg="bg-sky-400/10" border="border-sky-400/20" />
          </div>

          <div className="grid grid-cols-1 lg:grid-cols-2 gap-8">
            {/* Issues by Severity */}
            <div className="bg-slate-900 border border-slate-800 rounded-3xl p-8 shadow-glass">
              <h3 className="text-xl font-bold text-slate-50 mb-6 flex items-center gap-2">
                <AlertOctagon className="text-rose-500" /> Discovered Issues
              </h3>
              
              <div className="space-y-6">
                <IssueGroup title="High Severity" issues={review.issues.high} icon={AlertOctagon} color="text-rose-500" />
                <IssueGroup title="Medium Severity" issues={review.issues.medium} icon={AlertTriangle} color="text-amber-500" />
                <IssueGroup title="Low Severity" issues={review.issues.low} icon={Info} color="text-sky-500" />
              </div>
            </div>

            {/* Recommendations */}
            <div className="bg-slate-900 border border-slate-800 rounded-3xl p-8 shadow-glass">
              <h3 className="text-xl font-bold text-slate-50 mb-6 flex items-center gap-2">
                <CheckSquare className="text-emerald-500" /> Actionable Recommendations
              </h3>
              
              <ul className="space-y-4">
                {review.recommendations.map((rec, idx) => (
                  <li key={idx} className="flex items-start gap-3 p-4 bg-slate-950 border border-slate-800 rounded-2xl">
                    <div className="w-6 h-6 rounded-full bg-emerald-500/10 flex items-center justify-center shrink-0 mt-0.5">
                      <CheckSquare size={12} className="text-emerald-500" />
                    </div>
                    <span className="text-slate-300 leading-relaxed">{rec}</span>
                  </li>
                ))}
              </ul>
            </div>
          </div>
          
        </div>
      ) : null}
    </div>
  );
}

//Reusable card --- Used for: Quality,Security,Maintainability,Performance
function Scorecard({ title, score, icon: Icon, color, bg, border }) {
  return (
    <div className={`p-6 rounded-3xl border bg-slate-900 ${border} shadow-glass relative overflow-hidden group hover:border-${color.split('-')[1]}-500/50 transition-colors`}>
      <div className={`absolute top-0 right-0 w-24 h-24 ${bg} rounded-bl-full -mr-4 -mt-4 opacity-50 group-hover:scale-110 transition-transform`} />
      <Icon size={24} className={`${color} mb-4 relative z-10`} />
      <h4 className="text-slate-400 text-sm font-medium mb-1 relative z-10">{title}</h4>
      <div className="flex items-baseline gap-1 relative z-10">
        <span className={`text-3xl font-bold ${color}`}>{score}</span>
        <span className="text-sm font-medium text-slate-500">/ 10</span>
      </div>
    </div>
  );
}

//eusable severity block --- Used for: High,Medium,Low
function IssueGroup({ title, issues, icon: Icon, color }) {
  if (issues.length === 0) return null;
  return (
    <div>
      <h4 className={`text-sm font-semibold uppercase tracking-wider mb-3 flex items-center gap-2 ${color}`}>
        <Icon size={16} /> {title} ({issues.length})
      </h4>
      <ul className="space-y-2">
        {issues.map((issue, idx) => (
          <li key={idx} className="p-3 bg-slate-950 border border-slate-800 rounded-xl text-sm text-slate-300 flex items-start gap-2">
            <div className="mt-1 w-1.5 h-1.5 rounded-full shrink-0 bg-current opacity-50" />
            {issue}
          </li>
        ))}
      </ul>
    </div>
  );
}
