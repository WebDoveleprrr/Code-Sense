// src/pages/ExplainCode.jsx
import React, { useState } from "react";
import { useSearchParams } from "react-router-dom";
import { Zap, FileCode2, Hash, ChevronRight, BookOpen, Loader2, AlertTriangle } from "lucide-react";
import toast from "react-hot-toast";
import { explainApi } from "../services/api";
import {
  Card, Button, Input, SectionHeader, EmptyState,
  ErrorAlert, Badge
} from "../components/ui";
import RepoSelector from "../components/ui/RepoSelector";
import CodeBlock from "../components/ui/CodeBlock";
import { formatMs } from "../utils/helpers";

const EXAMPLE_SNIPPETS = [
  { file: "app/ml/embedder.py", start: 1, end: 40 },
  { file: "app/services/search_service.py", start: 1, end: 50 },
  { file: "app/api/v1/repositories.py", start: 1, end: 30 },
];

function ExplanationPanel({ explanation }) {
  if (!explanation) return null;

  const {
    explanation: text,
    file_path,
    start_line,
    end_line,
    language,
    code_snippet,
    latency_ms,
  } = explanation;

  // Parse sections from explanation text
  const sections = text.split(/\n(?=###|##|\*\*[A-Z])/g);

  return (
    <div className="space-y-4 animate-slide-up">
      {explanation.is_fallback && (
        <div className="bg-warning/10 border border-warning/20 text-warning px-4 py-3 rounded-xl text-sm font-body flex items-center gap-3">
          <AlertTriangle size={16} className="text-warning flex-shrink-0" />
          <span>Generated locally because LLM quota is unavailable.</span>
        </div>
      )}

      {/* Meta */}
      <div className="flex items-center gap-3 text-xs font-mono text-frost-dim flex-wrap">
        <span className="flex items-center gap-1">
          <FileCode2 size={11} />
          {file_path}
        </span>
        <span>L{start_line}–{end_line}</span>
        <Badge variant="acid">{language}</Badge>
        {latency_ms && (
          <span className="ml-auto text-ink-500">{formatMs(latency_ms)}</span>
        )}
      </div>

      {/* Code */}
      {code_snippet && (
        <CodeBlock
          code={code_snippet}
          language={language || "text"}
          startLine={start_line}
          showCopy
          maxHeight="280px"
        />
      )}

      {/* Explanation text */}
      <Card>
        <div className="flex items-center gap-2 mb-4">
          <BookOpen size={15} className="text-acid" />
          <span className="font-mono text-xs font-bold text-acid uppercase tracking-widest">
            AI Explanation
          </span>
        </div>
        <div className="prose-like space-y-3">
          {text.split("\n\n").map((para, i) => {
            if (para.startsWith("###") || para.startsWith("**")) {
              return (
                <h4 key={i} className="font-mono text-sm font-bold text-acid mt-4">
                  {para.replace(/^#{1,3}\s*|\*\*/g, "")}
                </h4>
              );
            }
            if (para.startsWith("- ") || para.startsWith("* ")) {
              return (
                <ul key={i} className="space-y-1">
                  {para.split("\n").map((item, j) => (
                    <li
                      key={j}
                      className="flex items-start gap-2 text-sm text-frost font-body"
                    >
                      <ChevronRight size={12} className="text-acid mt-1 flex-shrink-0" />
                      {item.replace(/^[-*]\s*/, "")}
                    </li>
                  ))}
                </ul>
              );
            }
            if (para.startsWith("`") && para.includes("`\n")) {
              return (
                <CodeBlock
                  key={i}
                  code={para.replace(/^`+|`+$/g, "")}
                  language={language || "text"}
                  compact
                  showCopy={false}
                />
              );
            }
            return (
              <p key={i} className="text-sm text-frost font-body leading-relaxed">
                {para}
              </p>
            );
          })}
        </div>
      </Card>
    </div>
  );
}

export default function ExplainCode() {
  const [searchParams] = useSearchParams();
  const [repoId, setRepoId] = useState(searchParams.get("repo") || "");
  const [filePath, setFilePath] = useState("");
  const [startLine, setStartLine] = useState("1");
  const [endLine, setEndLine] = useState("50");
  const [provider, setProvider] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const [result, setResult] = useState(null);

  const handleExplain = async () => {
    if (!repoId || !filePath.trim()) {
      toast.error("Select a repository and enter a file path");
      return;
    }

    setLoading(true);
    setError(null);
    try {
      const data = await explainApi.explain({
        repo_id: repoId,
        file_path: filePath.trim(),
        start_line: parseInt(startLine) || 1,
        end_line: parseInt(endLine) || 50,
        provider: provider || undefined,
      });
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
        title="Explain Code"
        subtitle="AI-powered explanations for any code range in your repository"
      />

      <div className="grid grid-cols-1 lg:grid-cols-5 gap-6">
        {/* Control panel */}
        <div className="lg:col-span-2 space-y-4">
          <Card>
            <div className="space-y-4">
              <div>
                <label className="block text-xs font-mono text-frost-dim uppercase tracking-widest mb-2">
                  Repository
                </label>
                <RepoSelector value={repoId} onChange={setRepoId} />
              </div>

              <div>
                <label className="block text-xs font-mono text-frost-dim uppercase tracking-widest mb-2">
                  File Path
                </label>
                <Input
                  placeholder="app/ml/embedder.py"
                  value={filePath}
                  onChange={(e) => setFilePath(e.target.value)}
                  icon={<FileCode2 size={13} />}
                />
              </div>

              <div className="grid grid-cols-2 gap-3">
                <div>
                  <label className="block text-xs font-mono text-frost-dim uppercase tracking-widest mb-2">
                    Start Line
                  </label>
                  <Input
                    type="number"
                    min="1"
                    placeholder="1"
                    value={startLine}
                    onChange={(e) => setStartLine(e.target.value)}
                  />
                </div>
                <div>
                  <label className="block text-xs font-mono text-frost-dim uppercase tracking-widest mb-2">
                    End Line
                  </label>
                  <Input
                    type="number"
                    min="1"
                    placeholder="50"
                    value={endLine}
                    onChange={(e) => setEndLine(e.target.value)}
                  />
                </div>
              </div>

              <Button
                onClick={handleExplain}
                loading={loading}
                disabled={!repoId || !filePath.trim()}
                className="w-full justify-center"
                icon={<Zap size={14} />}
              >
                {loading ? "Generating explanation…" : "Explain Code"}
              </Button>
            </div>
          </Card>

          {/* Examples */}
          <Card>
            <h3 className="font-mono text-xs font-bold text-frost-dim uppercase tracking-widest mb-3">
              Example Files
            </h3>
            <div className="space-y-2">
              {EXAMPLE_SNIPPETS.map((ex) => (
                <button
                  key={ex.file}
                  onClick={() => {
                    setFilePath(ex.file);
                    setStartLine(String(ex.start));
                    setEndLine(String(ex.end));
                  }}
                  className="w-full text-left text-xs font-mono px-3 py-2 bg-ink-800 border border-ink-600 rounded-lg text-frost-dim hover:text-acid hover:border-acid/30 transition-all"
                >
                  <span className="text-frost">{ex.file}</span>
                  <span className="text-ink-500 ml-2">L{ex.start}–{ex.end}</span>
                </button>
              ))}
            </div>
          </Card>
        </div>

        {/* Result panel */}
        <div className="lg:col-span-3">
          {error && <ErrorAlert message={error} onRetry={handleExplain} />}

          {loading && (
            <div className="flex flex-col items-center justify-center py-24">
              <div className="w-16 h-16 rounded-2xl bg-acid-muted border border-acid/20 flex items-center justify-center mb-4">
                <Loader2 size={28} className="text-acid animate-spin" />
              </div>
              <p className="font-mono text-sm text-frost-dim">Reading code…</p>
              <p className="font-mono text-xs text-ink-500 mt-1">
                Generating AI explanation
              </p>
            </div>
          )}

          {!loading && !error && result && (
            <ExplanationPanel explanation={result} />
          )}

          {!loading && !error && !result && (
            <EmptyState
              icon={Zap}
              title="Explain any code range"
              description="Select a repository, enter a file path and line range, then get an AI-powered explanation of what the code does."
            />
          )}
        </div>
      </div>
    </div>
  );
}
