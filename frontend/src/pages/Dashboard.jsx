import React, { useEffect, useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import { Upload, Database, Search, Activity, Zap, Play, CheckCircle2, Clock } from "lucide-react";
import { useRepositories } from "../hooks/useRepositories";
import { repositoriesApi, healthApi } from "../services/api";
import { timeAgo } from "../utils/helpers";
import toast from "react-hot-toast";

export default function Dashboard() {
  const { repos, loading, mutate } = useRepositories();
  const [health, setHealth] = useState(null);
  const navigate = useNavigate();

  useEffect(() => {
    healthApi.ping().then(setHealth).catch(() => {});
  }, []);

  const handleExploreDemo = async () => {
    const demoRepo = repos.find(r => r.name.toLowerCase().includes('fastapi') || r.name.toLowerCase().includes('demo'));
    if (demoRepo) {
      navigate(`/search?repo=${demoRepo.id}`);
    } else {
      try {
        toast.loading("Provisioning Demo Repository (FastAPI)...", { id: "demo-toast" });
        await repositoriesApi.ingestGitHub("https://github.com/tiangolo/fastapi", "master");
        toast.success("Demo repository ingestion started!", { id: "demo-toast" });
        mutate();
      } catch (err) {
        toast.error("Failed to provision demo repository.", { id: "demo-toast" });
      }
    }
  };

  const readyRepos = repos.filter((r) => r.status === "ready");

  return (
    <div className="p-8 max-w-7xl mx-auto font-sans">
      {/* Hero Section */}
      <section className="mb-16 mt-8">
        <h1 className="text-4xl md:text-5xl font-bold text-slate-50 mb-4 tracking-tight">
          Welcome back
        </h1>
        <p className="text-lg text-slate-400 mb-8 max-w-2xl">
          Understand repositories instantly. Analyze architecture, search semantically, and review code quality with AI.
        </p>
        <div className="flex flex-col sm:flex-row items-center gap-4">
          <Link
            to="/upload"
            className="w-full sm:w-auto px-6 py-3 bg-indigo-600 hover:bg-indigo-700 text-white rounded-lg font-medium transition-all shadow-glow flex items-center justify-center gap-2"
          >
            <Upload size={18} /> Upload Repository
          </Link>
          <button
            onClick={handleExploreDemo}
            className="w-full sm:w-auto px-6 py-3 bg-slate-800 hover:bg-slate-700 text-slate-200 rounded-lg font-medium transition-all flex items-center justify-center gap-2 border border-slate-700"
          >
            <Play size={18} className="text-indigo-400" /> Explore Demo Repository
          </button>
        </div>
      </section>

      {/* Repository Overview */}
      <section>
        <div className="flex items-center justify-between mb-6">
          <h2 className="text-xl font-semibold text-slate-50">Repository Overview</h2>
          <div className="flex items-center gap-2 text-sm text-slate-400">
            <div className={`w-2 h-2 rounded-full ${health ? "bg-emerald-500 shadow-[0_0_8px_rgba(16,185,129,0.5)]" : "bg-slate-600"}`} />
            {health ? "System Online" : "Connecting..."}
          </div>
        </div>

        {loading ? (
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
            {[1, 2, 3].map(i => (
              <div key={i} className="h-48 bg-slate-900 border border-slate-800 rounded-2xl animate-pulse" />
            ))}
          </div>
        ) : repos.length === 0 ? (
          <div className="bg-slate-900 border border-slate-800 rounded-2xl p-12 text-center">
            <div className="w-16 h-16 bg-slate-800 rounded-full flex items-center justify-center mx-auto mb-6">
              <Database size={24} className="text-slate-400" />
            </div>
            <h3 className="text-xl font-semibold text-slate-50 mb-2">No repositories indexed yet.</h3>
            <p className="text-slate-400 max-w-md mx-auto mb-8">
              Upload a repository to begin semantic analysis, architecture discovery, and AI-powered exploration.
            </p>
            <div className="flex justify-center gap-4">
              <Link to="/upload" className="px-5 py-2.5 bg-indigo-600 hover:bg-indigo-700 text-white rounded-lg font-medium transition-colors">
                Upload Repository
              </Link>
            </div>
          </div>
        ) : (
          <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3 gap-6">
            {repos.map(repo => (
              <RepoCard key={repo.id} repo={repo} />
            ))}
          </div>
        )}
      </section>
    </div>
  );
}

function RepoCard({ repo }) {
  const isReady = repo.status === "ready";
  const language = repo.repo_metadata?.primary_language || "Python";
  
  return (
    <div className="bg-slate-900 border border-slate-800 rounded-2xl p-6 hover:border-indigo-500/50 transition-colors flex flex-col h-full">
      <div className="flex justify-between items-start mb-4">
        <h3 className="text-lg font-bold text-slate-50 truncate flex-1 pr-4" title={repo.name}>
          {repo.name.split('/').pop() || repo.name}
        </h3>
        {isReady ? (
          <span className="flex items-center gap-1 text-xs font-medium text-emerald-400 bg-emerald-400/10 px-2.5 py-1 rounded-full border border-emerald-400/20 shrink-0">
            <CheckCircle2 size={12} /> Ready
          </span>
        ) : (
          <span className="flex items-center gap-1 text-xs font-medium text-indigo-400 bg-indigo-400/10 px-2.5 py-1 rounded-full border border-indigo-400/20 shrink-0">
            <Clock size={12} /> Indexing
          </span>
        )}
      </div>

      <div className="grid grid-cols-2 gap-4 mb-6 text-sm text-slate-400">
        <div>
          <span className="block text-slate-500 text-xs mb-1">Language</span>
          <span className="font-medium text-slate-300">{language}</span>
        </div>
        <div>
          <span className="block text-slate-500 text-xs mb-1">Indexed</span>
          <span className="font-medium text-slate-300">{timeAgo(repo.created_at)}</span>
        </div>
        <div>
          <span className="block text-slate-500 text-xs mb-1">Files</span>
          <span className="font-medium text-slate-300">{repo.total_files || 0}</span>
        </div>
        <div>
          <span className="block text-slate-500 text-xs mb-1">Chunks</span>
          <span className="font-medium text-slate-300">{repo.total_chunks || 0}</span>
        </div>
      </div>

      <div className="mt-auto pt-4 border-t border-slate-800 flex items-center justify-between gap-2">
        <Link 
          to={`/search?repo=${repo.id}`}
          className="flex-1 py-2 text-center text-sm font-medium text-indigo-400 bg-indigo-500/10 hover:bg-indigo-500/20 rounded-lg transition-colors"
        >
          Search
        </Link>
        <Link 
          to={`/qa?repo=${repo.id}`}
          className="flex-1 py-2 text-center text-sm font-medium text-slate-300 bg-slate-800 hover:bg-slate-700 rounded-lg transition-colors"
        >
          Ask
        </Link>
        <Link 
          to={`/architecture?repo=${repo.id}`}
          className="flex-1 py-2 text-center text-sm font-medium text-slate-300 bg-slate-800 hover:bg-slate-700 rounded-lg transition-colors"
        >
          Analyze
        </Link>
      </div>
    </div>
  );
}
