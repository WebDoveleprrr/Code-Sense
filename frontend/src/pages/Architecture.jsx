// src/pages/Architecture.jsx
import React, { useState } from "react";
import { useSearchParams } from "react-router-dom";
import {
  Building2, RefreshCw, Layers, GitBranch, Code2,
  Package, AlertTriangle, ChevronRight, Cpu
} from "lucide-react";
import toast from "react-hot-toast";
import { architectureApi } from "../services/api";
import {
  Card, Button, SectionHeader, EmptyState,
  ErrorAlert, Spinner, Badge
} from "../components/ui";
import RepoSelector from "../components/ui/RepoSelector";
import { langColor, formatMs } from "../utils/helpers";

function LangBar({ breakdown }) {
  if (!breakdown || Object.keys(breakdown).length === 0) return null;
  const total = Object.values(breakdown).reduce((a, b) => a + b, 0);
  const sorted = Object.entries(breakdown).sort((a, b) => b[1] - a[1]);

  return (
    <div>
      <div className="flex h-2 rounded-full overflow-hidden gap-px mb-2">
        {sorted.map(([lang, count]) => (
          <div
            key={lang}
            style={{
              width: `${(count / total) * 100}%`,
              backgroundColor: langColor(lang),
            }}
          />
        ))}
      </div>
      <div className="flex flex-wrap gap-2">
        {sorted.map(([lang, count]) => (
          <div key={lang} className="flex items-center gap-1.5 text-xs font-mono">
            <div
              className="w-2 h-2 rounded-full"
              style={{ backgroundColor: langColor(lang) }}
            />
            <span className="text-frost">{lang}</span>
            <span className="text-frost-dim">{((count / total) * 100).toFixed(0)}%</span>
          </div>
        ))}
      </div>
    </div>
  );
}

function MetricGrid({ metrics }) {
  const items = [
    { label: "Files", value: metrics.total_files, icon: Code2 },
    { label: "Functions", value: metrics.total_functions, icon: Cpu },
    { label: "Classes", value: metrics.total_classes, icon: Layers },
    { label: "Lines", value: metrics.total_lines?.toLocaleString(), icon: GitBranch },
    { label: "Imports", value: metrics.total_imports, icon: Package },
    { label: "Chunks", value: metrics.total_chunks?.toLocaleString(), icon: Building2 },
  ];

  return (
    <div className="grid grid-cols-3 gap-3">
      {items.map(({ label, value, icon: Icon }) => (
        <div key={label} className="bg-ink-800 border border-ink-600 rounded-xl p-3 text-center">
          <Icon size={14} className="text-acid mx-auto mb-1" />
          <p className="text-lg font-display font-bold text-frost">{value ?? "—"}</p>
          <p className="text-xs font-mono text-frost-dim">{label}</p>
        </div>
      ))}
    </div>
  );
}

function SummarySection({ title, content, icon: Icon }) {
  if (!content) return null;
  return (
    <div>
      <div className="flex items-center gap-2 mb-3">
        <Icon size={14} className="text-acid" />
        <h3 className="font-mono text-xs font-bold text-acid uppercase tracking-widest">
          {title}
        </h3>
      </div>
      <div className="space-y-2">
        {Array.isArray(content) ? (
          content.map((item, i) => (
            <div key={i} className="flex items-start gap-2 text-sm font-body text-frost">
              <ChevronRight size={12} className="text-acid mt-1 flex-shrink-0" />
              <span>{item}</span>
            </div>
          ))
        ) : (
          <p className="text-sm font-body text-frost leading-relaxed">{content}</p>
        )}
      </div>
    </div>
  );
}

export default function Architecture() {
  const [searchParams] = useSearchParams();
  const [repoId, setRepoId] = useState(searchParams.get("repo") || "");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const [result, setResult] = useState(null);

  const handleGenerate = async () => {
    if (!repoId) return toast.error("Select a repository first");
    setLoading(true);
    setError(null);
    try {
      const data = await architectureApi.summarise(repoId);
      setResult(data);
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="p-8 max-w-5xl mx-auto">
      <SectionHeader
        title="Architecture Summary"
        subtitle="AI-generated structural analysis of your repository's architecture"
      />

      {/* Controls */}
      <div className="flex items-center gap-3 mb-6">
        <div className="w-80">
          <RepoSelector value={repoId} onChange={setRepoId} />
        </div>
        <Button
          onClick={handleGenerate}
          loading={loading}
          disabled={!repoId}
          icon={loading ? undefined : <Building2 size={14} />}
        >
          {loading ? "Analysing…" : result ? "Regenerate" : "Generate Summary"}
        </Button>
      </div>

      {error && <ErrorAlert message={error} onRetry={handleGenerate} />}

      {loading && (
        <div className="flex flex-col items-center justify-center py-24">
          <div className="w-20 h-20 rounded-2xl bg-ink-800 border border-ink-600 flex items-center justify-center mb-5">
            <Building2 size={36} className="text-acid animate-pulse" />
          </div>
          <p className="font-display text-frost text-lg font-bold mb-2">
            Analysing repository architecture…
          </p>
          <p className="text-frost-dim text-sm font-body">
            Retrieving code samples and generating summary
          </p>
        </div>
      )}

      {!loading && !error && result && (
        <div className="space-y-5 animate-slide-up">
          {result.is_fallback && (
            <div className="bg-warning/10 border border-warning/20 text-warning px-4 py-3 rounded-xl text-sm font-body flex items-center gap-3">
              <AlertTriangle size={16} className="text-warning flex-shrink-0" />
              <span>Local structural analysis mode active.</span>
            </div>
          )}

          {/* Overview card */}
          <Card glow>
            <div className="flex items-start justify-between mb-4">
              <div>
                <h2 className="font-display text-xl font-bold text-frost">
                  {result.repo_name || "Repository Overview"}
                </h2>
                <p className="text-frost-dim text-sm font-body mt-1">
                  Architecture analysis
                </p>
              </div>
              {result.latency_ms && (
                <span className="text-xs font-mono text-frost-dim">
                  {formatMs(result.latency_ms)}
                </span>
              )}
            </div>

            {result.summary && (
              <p className="text-sm font-body text-frost leading-relaxed mb-5 border-l-2 border-acid/30 pl-4">
                {result.summary}
              </p>
            )}

            {result.language_breakdown && (
              <div>
                <p className="text-xs font-mono text-frost-dim uppercase tracking-widest mb-3">
                  Language Distribution
                </p>
                <LangBar breakdown={result.language_breakdown} />
              </div>
            )}
          </Card>

          {/* Metrics */}
          {result.metrics && (
            <Card>
              <h3 className="font-mono text-xs font-bold text-frost-dim uppercase tracking-widest mb-4">
                Structural Metrics
              </h3>
              <MetricGrid metrics={result.metrics} />
            </Card>
          )}

          {/* Sections */}
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-5">
            <Card>
              <SummarySection
                title="Entry Points"
                content={result.entry_points}
                icon={Cpu}
              />
            </Card>
            <Card>
              <SummarySection
                title="Key Modules"
                content={result.key_modules}
                icon={Package}
              />
            </Card>
            <Card>
              <SummarySection
                title="Architecture Patterns"
                content={result.patterns}
                icon={Layers}
              />
            </Card>
            <Card>
              <SummarySection
                title="Dependencies"
                content={result.external_deps}
                icon={GitBranch}
              />
            </Card>
          </div>

          {/* Recommendations */}
          {result.recommendations?.length > 0 && (
            <Card>
              <div className="flex items-center gap-2 mb-4">
                <AlertTriangle size={14} className="text-signal" />
                <h3 className="font-mono text-xs font-bold text-signal uppercase tracking-widest">
                  Recommendations
                </h3>
              </div>
              <div className="space-y-2">
                {result.recommendations.map((rec, i) => (
                  <div
                    key={i}
                    className="flex items-start gap-3 px-3 py-2.5 bg-signal-muted border border-signal/10 rounded-lg"
                  >
                    <span className="text-xs font-mono text-signal w-4 flex-shrink-0">
                      {i + 1}.
                    </span>
                    <p className="text-xs font-body text-frost">{rec}</p>
                  </div>
                ))}
              </div>
            </Card>
          )}
        </div>
      )}

      {!loading && !error && !result && (
        <EmptyState
          icon={Building2}
          title="Generate Architecture Summary"
          description="Select an indexed repository and click 'Generate Summary' to get an AI-powered analysis of your codebase structure, patterns, and entry points."
          action={
            repoId ? (
              <Button onClick={handleGenerate} icon={<Building2 size={14} />}>
                Generate Now
              </Button>
            ) : null
          }
        />
      )}
    </div>
  );
}
