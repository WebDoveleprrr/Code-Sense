//AI Review automatically evaluates the repository for:Code Quality,Security,Maintainability,Performance
//it generates issues, scores, and recommendations
import React, { useState, useEffect } from "react";
import { useSearchParams, useNavigate } from "react-router-dom";
import { ShieldAlert, Loader2, Star, ShieldCheck, Activity, Settings, AlertOctagon, AlertTriangle, Info, CheckSquare, Clock, Cpu, Calendar } from "lucide-react";
import { reviewApi } from "../services/api";
import { useRepository } from "../hooks/useRepositories";
import RepoSelector from "../components/ui/RepoSelector";
import toast from "react-hot-toast"; //popups

export default function AIReview() {
  const [searchParams] = useSearchParams();
  const navigate = useNavigate();
  const [repoId, setRepoId] = useState(searchParams.get("repo") || "");
  const { repo } = useRepository(repoId);
  
  const [loading, setLoading] = useState(false);
  const [review, setReview] = useState(null);
  const isRepoReady = repo ? repo.status === "ready" : false;
  const abortControllerRef = React.useRef(null);

  useEffect(() => {
    if (repoId && isRepoReady) {
      loadReview();
    } else {
      setReview(null);
    }
  }, [repoId, isRepoReady]);

  const loadReview = async () => {
    if (abortControllerRef.current) {
      abortControllerRef.current.abort();
    }
    const controller = new AbortController();
    abortControllerRef.current = controller;

    setLoading(true);
    try {
      const res = await reviewApi.analyze({ repo_id: repoId }, { signal: controller.signal });
      const high = [];
      const medium = [];
      const low = [];

      if (res && res.issues) {
        res.issues.forEach(issue => {
           if (issue.severity.toLowerCase() === 'high') high.push(issue);
           else if (issue.severity.toLowerCase() === 'medium') medium.push(issue);
           else low.push(issue);
        });
      }

      setReview({
        summary: res.summary || "No summary available.",
        overallScore: res.scores?.overall?.toFixed(1) || "10.0",
        scores: res.scores || { quality: 10, security: 10, maintainability: 10, performance: 10 },
        issues: { high, medium, low },
        recommendations: res.recommendations || [],
        timestamp: res.timestamp,
        duration_ms: res.duration_ms,
        model: res.model
      });
    } catch (err) {
      if (err.name === 'CanceledError' || err.message === 'canceled' || err.code === 'ERR_CANCELED') {
        return;
      }
      toast.error("Failed to load AI review");
    } finally {
      if (abortControllerRef.current === controller) {
        setLoading(false);
      }
    }
  };

  useEffect(() => {
    return () => {
      if (abortControllerRef.current) {
        abortControllerRef.current.abort();
      }
    };
  }, []);

  return (
    <div className="p-8 max-w-6xl mx-auto font-sans">
      <div className="mb-10 text-center relative">
        <h1 className="text-3xl font-bold text-slate-50 mb-3">AI Code Review</h1>
        <p className="text-slate-400">Automated evaluation of code quality, security, maintainability, and performance.</p>
        
        {review && (
          <button 
            onClick={() => {
              const dataStr = "data:text/json;charset=utf-8," + encodeURIComponent(JSON.stringify(review, null, 2));
              const downloadAnchorNode = document.createElement('a');
              downloadAnchorNode.setAttribute("href", dataStr);
              downloadAnchorNode.setAttribute("download", `review_${repoId}.json`);
              document.body.appendChild(downloadAnchorNode);
              downloadAnchorNode.click();
              downloadAnchorNode.remove();
            }}
            className="absolute top-0 right-0 px-4 py-2 bg-slate-800 hover:bg-slate-700 text-slate-200 text-sm font-medium rounded-lg transition-colors border border-slate-700 shadow-sm"
          >
            Export JSON
          </button>
        )}
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
          <div className="bg-slate-900 border border-slate-800 rounded-3xl p-8 flex flex-col md:flex-row items-center gap-8 shadow-glass relative overflow-hidden">
            <div className="flex-1">
              <h2 className="text-2xl font-bold text-slate-50 mb-4">Executive Summary</h2>
              <p className="text-slate-300 leading-relaxed mb-6">
                {review.summary}
              </p>
              
              <div className="flex flex-wrap gap-4 text-xs font-medium text-slate-400">
                {review.timestamp && (
                  <div className="flex items-center gap-1.5 px-3 py-1.5 bg-slate-950 rounded-lg border border-slate-800">
                    <Calendar size={14} className="text-indigo-400" />
                    {new Date(review.timestamp).toLocaleString()}
                  </div>
                )}
                {review.duration_ms && (
                  <div className="flex items-center gap-1.5 px-3 py-1.5 bg-slate-950 rounded-lg border border-slate-800">
                    <Clock size={14} className="text-sky-400" />
                    {(review.duration_ms / 1000).toFixed(1)}s Generation
                  </div>
                )}
                {review.model && (
                  <div className="flex items-center gap-1.5 px-3 py-1.5 bg-slate-950 rounded-lg border border-slate-800">
                    <Cpu size={14} className="text-emerald-400" />
                    Model: {review.model}
                  </div>
                )}
              </div>
            </div>
            <div className="w-48 h-48 rounded-full border-8 border-indigo-500/20 flex flex-col items-center justify-center shrink-0 relative">
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
              
              <div className="space-y-6 pr-2">
                <IssueGroup title="High Severity" issues={review.issues.high} icon={AlertOctagon} color="text-rose-500" bg="bg-rose-500/10" repoId={repoId} navigate={navigate} />
                <IssueGroup title="Medium Severity" issues={review.issues.medium} icon={AlertTriangle} color="text-amber-500" bg="bg-amber-500/10" repoId={repoId} navigate={navigate} />
                <IssueGroup title="Low Severity" issues={review.issues.low} icon={Info} color="text-sky-500" bg="bg-sky-500/10" repoId={repoId} navigate={navigate} />
              </div>
            </div>

            {/* Recommendations */}
            <div className="bg-slate-900 border border-slate-800 rounded-3xl p-8 shadow-glass h-fit sticky top-6">
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

//Reusable severity block --- Used for: High,Medium,Low
function IssueGroup({ title, issues, icon: Icon, color, bg, repoId, navigate }) {
  if (issues.length === 0) return null;
  return (
    <div className="mb-8 last:mb-0">
      <h4 className={`text-sm font-semibold uppercase tracking-wider mb-4 flex items-center gap-2 ${color}`}>
        <Icon size={16} /> {title} ({issues.length})
      </h4>
      <div className="space-y-4">
        {issues.map((issue, idx) => (
          <div key={idx} className="p-4 bg-slate-950 border border-slate-800 rounded-xl overflow-hidden relative">
            <div className={`absolute top-0 left-0 w-1 h-full ${bg.replace('/10', '')}`} />
            <div className="flex items-start justify-between mb-2 gap-4">
              <h5 className="font-semibold text-slate-200 text-sm">{issue.issue}</h5>
              <div className="flex items-center gap-2 shrink-0">
                <button 
                  onClick={() => {
                    const query = encodeURIComponent(`Explain this issue in ${issue.file}${issue.line ? ` around line ${issue.line}` : ''}: ${issue.issue}`);
                    navigate(`/qa?repo=${repoId}&q=${query}`);
                  }}
                  className="px-2 py-1 bg-indigo-500/10 hover:bg-indigo-500/20 text-indigo-400 border border-indigo-500/20 rounded text-xs transition-colors whitespace-nowrap"
                >
                  Explain Issue
                </button>
                <div className="text-xs font-mono bg-slate-800 px-2 py-1 rounded text-slate-400 max-w-[150px] sm:max-w-[200px] truncate" title={`${issue.file}${issue.line ? `:${issue.line}` : ''}`}>
                  {issue.file}{issue.line ? `:${issue.line}` : ''}
                </div>
              </div>
            </div>
            
            {issue.confidence && (
              <div className="flex items-center gap-2 mb-3">
                <div className="h-1.5 w-16 bg-slate-800 rounded-full overflow-hidden">
                  <div className={`h-full ${color}`} style={{ width: `${Math.round(issue.confidence * 100)}%` }} />
                </div>
                <span className="text-xs text-slate-500 font-medium">{Math.round(issue.confidence * 100)}% Confidence</span>
              </div>
            )}
            
            <div className="space-y-3">
              <div>
                <span className="text-xs font-semibold text-slate-500 uppercase tracking-wider block mb-1">Why it matters</span>
                <p className="text-sm text-slate-300 leading-relaxed">{issue.why_it_matters}</p>
              </div>
              
              {issue.evidence && (
                <div>
                  <span className="text-xs font-semibold text-slate-500 uppercase tracking-wider block mb-1">Evidence</span>
                  <code className="text-xs bg-slate-900 border border-slate-800 p-2 rounded block text-indigo-300 font-mono overflow-x-auto whitespace-pre">
                    {issue.evidence}
                  </code>
                </div>
              )}
              
              {issue.recommendation && (
                <div className="pt-2 border-t border-slate-800/50 mt-2">
                  <span className="text-xs font-semibold text-slate-500 uppercase tracking-wider block mb-1 flex items-center gap-1">
                    <CheckSquare size={12} className="text-emerald-500" /> Recommended Fix
                  </span>
                  <p className="text-sm text-emerald-400/90 leading-relaxed">{issue.recommendation}</p>
                </div>
              )}
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}
