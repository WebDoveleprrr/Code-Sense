// src/pages/Dashboard.jsx
import React, { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import {
  Upload, Search, MessageSquare, Zap, GitBranch, Building2,
  Database, Cpu, TrendingUp, Clock, CheckCircle, AlertCircle,
  ArrowRight, Activity
} from "lucide-react";
import { useRepositories } from "../hooks/useRepositories";
import { Card, StatusBadge, Skeleton, Badge } from "../components/ui";
import { healthApi } from "../services/api";
import { timeAgo, formatMs } from "../utils/helpers";

const QUICK_ACTIONS = [
  { to: "/upload", icon: Upload, label: "Upload Repo", desc: "GitHub URL or ZIP file", color: "acid" },
  { to: "/search", icon: Search, label: "Semantic Search", desc: "Natural language code search", color: "plasma" },
  { to: "/qa", icon: MessageSquare, label: "Repo Q&A", desc: "Ask questions with RAG", color: "signal" },
  { to: "/explain", icon: Zap, label: "Explain Code", desc: "AI-powered code explanation", color: "acid" },
  { to: "/graph", icon: GitBranch, label: "Dependency Graph", desc: "Visual import mapping", color: "plasma" },
  { to: "/architecture", icon: Building2, label: "Architecture", desc: "System structure summary", color: "signal" },
];

function StatCard({ label, value, icon: Icon, sub, color = "acid" }) {
  const colorMap = {
    acid: "text-acid bg-acid-muted border-acid/10",
    plasma: "text-plasma-light bg-plasma-muted border-plasma/10",
    signal: "text-signal bg-signal-muted border-signal/10",
  };
  return (
    <Card>
      <div className="flex items-start justify-between">
        <div>
          <p className="text-xs text-frost-dim font-mono uppercase tracking-widest mb-1">{label}</p>
          <p className="text-3xl font-display font-bold text-frost">{value}</p>
          {sub && <p className="text-xs text-frost-dim font-body mt-1">{sub}</p>}
        </div>
        <div className={`w-10 h-10 rounded-xl border flex items-center justify-center ${colorMap[color]}`}>
          <Icon size={18} />
        </div>
      </div>
    </Card>
  );
}

function RepoRow({ repo }) {
  return (
    <Link
      to={`/search?repo=${repo.id}`}
      className="flex items-center gap-4 px-4 py-3 hover:bg-ink-700 rounded-lg transition-colors group"
    >
      <div className="w-8 h-8 rounded-lg bg-ink-700 border border-ink-500 flex items-center justify-center flex-shrink-0">
        <Database size={14} className="text-frost-dim group-hover:text-acid transition-colors" />
      </div>
      <div className="flex-1 min-w-0">
        <p className="text-sm font-mono text-frost truncate">{repo.name}</p>
        <p className="text-xs text-frost-dim font-body">
          {repo.total_chunks?.toLocaleString() || 0} chunks · {repo.total_files || 0} files · {timeAgo(repo.created_at)}
        </p>
      </div>
      <StatusBadge status={repo.status} />
      <ArrowRight size={14} className="text-ink-500 group-hover:text-acid transition-colors" />
    </Link>
  );
}

export default function Dashboard() {
  const { repos, loading } = useRepositories();
  const [health, setHealth] = useState(null);

  useEffect(() => {
    healthApi.ping().then(setHealth).catch(() => {});
  }, []);

  const readyRepos = repos.filter((r) => r.status === "ready");
  const totalChunks = repos.reduce((s, r) => s + (r.total_chunks || 0), 0);

  return (
    <div className="p-8 max-w-6xl mx-auto">
      {/* Header */}
      <div className="mb-8">
        <div className="flex items-center gap-2 mb-2">
          <div className="w-2 h-2 rounded-full bg-acid status-dot-ready" />
          <span className="text-xs font-mono text-frost-dim uppercase tracking-widest">
            System {health ? "Online" : "Connecting…"}
          </span>
        </div>
        <h1 className="font-display text-4xl font-bold text-frost tracking-tight">
          CODESENSE{" "}
          <span className="text-acid text-glow-acid">INTELLIGENCE</span>
        </h1>
        <p className="text-frost-dim font-body mt-2 text-base">
          AI-powered semantic repository intelligence platform
        </p>
      </div>

      {/* Stats */}
      <div className="grid grid-cols-2 lg:grid-cols-4 gap-4 mb-8">
        <StatCard
          label="Repositories"
          value={loading ? "—" : repos.length}
          icon={Database}
          sub={`${readyRepos.length} indexed`}
          color="acid"
        />
        <StatCard
          label="Code Chunks"
          value={loading ? "—" : totalChunks.toLocaleString()}
          icon={Cpu}
          sub="Embedded vectors"
          color="plasma"
        />
        <StatCard
          label="Ready"
          value={loading ? "—" : readyRepos.length}
          icon={CheckCircle}
          sub="Repos indexed"
          color="acid"
        />
        <StatCard
          label="Processing"
          value={loading ? "—" : repos.filter((r) => r.status === "processing" || r.status === "indexing").length}
          icon={Activity}
          sub="In progress"
          color="signal"
        />
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-5 gap-6">
        {/* Quick Actions */}
        <div className="lg:col-span-2">
          <h2 className="font-display text-sm font-bold text-frost-dim uppercase tracking-widest mb-4">
            Quick Actions
          </h2>
          <div className="space-y-2">
            {QUICK_ACTIONS.map(({ to, icon: Icon, label, desc, color }) => (
              <Link
                key={to}
                to={to}
                className="flex items-center gap-3 px-4 py-3 glass rounded-xl hover:border-acid/20 transition-all group"
              >
                <div
                  className={`w-8 h-8 rounded-lg flex items-center justify-center flex-shrink-0 ${
                    color === "acid"
                      ? "bg-acid-muted text-acid"
                      : color === "plasma"
                      ? "bg-plasma-muted text-plasma-light"
                      : "bg-signal-muted text-signal"
                  }`}
                >
                  <Icon size={15} />
                </div>
                <div className="flex-1 min-w-0">
                  <p className="text-sm font-mono text-frost group-hover:text-acid transition-colors">
                    {label}
                  </p>
                  <p className="text-xs text-frost-dim font-body truncate">{desc}</p>
                </div>
                <ArrowRight
                  size={14}
                  className="text-ink-500 group-hover:text-acid transition-colors"
                />
              </Link>
            ))}
          </div>
        </div>

        {/* Recent Repositories */}
        <div className="lg:col-span-3">
          <div className="flex items-center justify-between mb-4">
            <h2 className="font-display text-sm font-bold text-frost-dim uppercase tracking-widest">
              Repositories
            </h2>
            <Link
              to="/upload"
              className="text-xs font-mono text-acid hover:text-acid-dim transition-colors flex items-center gap-1"
            >
              <Upload size={11} />
              Add new
            </Link>
          </div>

          <Card className="p-0 overflow-hidden">
            {loading ? (
              <div className="p-4 space-y-3">
                {[1, 2, 3].map((i) => (
                  <Skeleton key={i} className="h-12" />
                ))}
              </div>
            ) : repos.length === 0 ? (
              <div className="flex flex-col items-center py-12 text-center px-6">
                <Database size={32} className="text-ink-500 mb-3" />
                <p className="text-frost font-mono text-sm mb-1">No repositories yet</p>
                <p className="text-frost-dim text-xs font-body mb-4">
                  Upload a GitHub repo or ZIP to get started
                </p>
                <Link
                  to="/upload"
                  className="text-xs font-mono text-acid hover:underline flex items-center gap-1"
                >
                  <Upload size={11} />
                  Upload repository
                </Link>
              </div>
            ) : (
              <div className="p-2">
                {repos.slice(0, 8).map((repo) => (
                  <RepoRow key={repo.id} repo={repo} />
                ))}
              </div>
            )}
          </Card>
        </div>
      </div>
    </div>
  );
}
