// src/pages/SemanticSearch.jsx
import React, { useState, useEffect, useRef } from "react";
import { useSearchParams } from "react-router-dom";
import { Search, Filter, Clock, Code2, Layers, SlidersHorizontal } from "lucide-react";
import { useSearch } from "../hooks/useSearch";
import {
  Card, Button, Input, Select, SectionHeader,
  EmptyState, ErrorAlert, Spinner, ScoreBar, Badge
} from "../components/ui";
import RepoSelector from "../components/ui/RepoSelector";
import CodeBlock from "../components/ui/CodeBlock";
import { formatMs, langColor } from "../utils/helpers";

const LANGUAGES = ["", "python", "javascript", "typescript", "c++", "java", "go", "rust"];
const CHUNK_TYPES = ["", "function", "class", "window"];

function SearchResultCard({ result, index }) {
  const [expanded, setExpanded] = useState(false);
  const lang = result.language || "text";

  return (
    <div className="glass rounded-xl overflow-hidden border border-ink-600 hover:border-acid/20 transition-all animate-slide-up">
      {/* Header */}
      <div className="flex items-center gap-3 px-4 py-3 border-b border-ink-600 bg-ink-900">
        <span className="text-xs font-mono text-frost-dim w-5 text-center">
          #{index + 1}
        </span>
        <div
          className="w-2 h-2 rounded-full flex-shrink-0"
          style={{ backgroundColor: langColor(lang) }}
        />
        <code className="flex-1 text-xs text-frost truncate font-mono">
          {result.file_path}
          <span className="text-frost-dim ml-2">
            L{result.start_line}–{result.end_line}
          </span>
        </code>
        <div className="flex items-center gap-2">
          {result.symbol_name && (
            <Badge variant="plasma">
              <Code2 size={10} />
              {result.symbol_name}
            </Badge>
          )}
          {result.chunk_type && result.chunk_type !== "window" && (
            <Badge variant="acid">{result.chunk_type}</Badge>
          )}
        </div>
        <div className="w-24">
          <ScoreBar score={result.score} />
        </div>
      </div>

      {/* Code */}
      <div className="p-0">
        <div style={{ maxHeight: expanded ? "none" : "160px", overflow: "hidden" }}>
          <CodeBlock
            code={result.content}
            language={lang}
            startLine={result.start_line}
            showCopy
            compact={!expanded}
            maxHeight="none"
          />
        </div>
        {result.content.split("\n").length > 8 && (
          <button
            onClick={() => setExpanded(!expanded)}
            className="w-full text-xs font-mono text-frost-dim hover:text-acid py-2 border-t border-ink-600 transition-colors bg-ink-900"
          >
            {expanded ? "▲ Collapse" : `▼ Show all ${result.content.split("\n").length} lines`}
          </button>
        )}
      </div>
    </div>
  );
}

export default function SemanticSearch() {
  const [searchParams] = useSearchParams();
  const [repoId, setRepoId] = useState(searchParams.get("repo") || "");
  const [query, setQuery] = useState("");
  const [topK, setTopK] = useState(5);
  const [language, setLanguage] = useState("");
  const [chunkType, setChunkType] = useState("");
  const [minScore, setMinScore] = useState(0.0);
  const [showFilters, setShowFilters] = useState(false);
  const inputRef = useRef(null);

  const { results, loading, error, meta, search, clear } = useSearch();

  const handleSearch = () => {
    if (!query.trim() || !repoId) return;
    search({
      repo_id: repoId,
      query: query.trim(),
      top_k: topK,
      language_filter: language || undefined,
      chunk_type_filter: chunkType || undefined,
      min_score: minScore,
    });
  };

  useEffect(() => {
    inputRef.current?.focus();
  }, []);

  return (
    <div className="p-8 max-w-5xl mx-auto">
      <SectionHeader
        title="Semantic Search"
        subtitle="Natural language code search powered by sentence-transformers + FAISS"
      />

      {/* Search bar */}
      <Card className="mb-6">
        <div className="space-y-4">
          {/* Repo selector */}
          <div>
            <label className="block text-xs font-mono text-frost-dim uppercase tracking-widest mb-2">
              Repository
            </label>
            <RepoSelector value={repoId} onChange={setRepoId} />
          </div>

          {/* Query input */}
          <div>
            <label className="block text-xs font-mono text-frost-dim uppercase tracking-widest mb-2">
              Search Query
            </label>
            <div className="flex gap-2">
              <div className="relative flex-1">
                <Search
                  size={15}
                  className="absolute left-3 top-1/2 -translate-y-1/2 text-frost-dim"
                />
                <Input
                  ref={inputRef}
                  placeholder="how are embeddings generated…"
                  value={query}
                  onChange={(e) => setQuery(e.target.value)}
                  onKeyDown={(e) => e.key === "Enter" && handleSearch()}
                  className="pl-10"
                />
              </div>
              <Button
                onClick={handleSearch}
                loading={loading}
                disabled={!query.trim() || !repoId}
              >
                Search
              </Button>
              <Button
                onClick={() => setShowFilters(!showFilters)}
                variant={showFilters ? "secondary" : "ghost"}
                icon={<SlidersHorizontal size={14} />}
              >
                Filters
              </Button>
            </div>
          </div>

          {/* Filters */}
          {showFilters && (
            <div className="flex flex-wrap gap-4 pt-2 border-t border-ink-600 animate-slide-up">
              <div className="flex items-center gap-2">
                <label className="text-xs font-mono text-frost-dim">Language:</label>
                <Select value={language} onChange={(e) => setLanguage(e.target.value)}>
                  {LANGUAGES.map((l) => (
                    <option key={l} value={l}>{l || "Any"}</option>
                  ))}
                </Select>
              </div>
              <div className="flex items-center gap-2">
                <label className="text-xs font-mono text-frost-dim">Type:</label>
                <Select value={chunkType} onChange={(e) => setChunkType(e.target.value)}>
                  {CHUNK_TYPES.map((t) => (
                    <option key={t} value={t}>{t || "Any"}</option>
                  ))}
                </Select>
              </div>
              <div className="flex items-center gap-2">
                <label className="text-xs font-mono text-frost-dim">Top-K:</label>
                <Select
                  value={topK}
                  onChange={(e) => setTopK(parseInt(e.target.value))}
                  className="w-20"
                >
                  {[3, 5, 10, 15, 20].map((k) => (
                    <option key={k} value={k}>{k}</option>
                  ))}
                </Select>
              </div>
              <div className="flex items-center gap-2">
                <label className="text-xs font-mono text-frost-dim">Min Score:</label>
                <input
                  type="range"
                  min="0"
                  max="1"
                  step="0.05"
                  value={minScore}
                  onChange={(e) => setMinScore(parseFloat(e.target.value))}
                  className="accent-acid w-24"
                />
                <span className="text-xs font-mono text-acid w-8">
                  {Math.round(minScore * 100)}%
                </span>
              </div>
            </div>
          )}
        </div>
      </Card>

      {/* Meta info */}
      {meta && (
        <div className="flex items-center gap-4 mb-4 text-xs font-mono text-frost-dim">
          <span className="flex items-center gap-1">
            <Layers size={12} />
            {results.length} results
          </span>
          <span className="flex items-center gap-1">
            <Clock size={12} />
            {formatMs(meta.latency_ms)}
          </span>
          <span className="text-frost-dim">for "{meta.query}"</span>
          <button onClick={clear} className="ml-auto text-frost-dim hover:text-danger transition-colors">
            Clear
          </button>
        </div>
      )}

      {/* Error */}
      {error && <ErrorAlert message={error} onRetry={handleSearch} />}

      {/* Loading */}
      {loading && (
        <div className="flex items-center justify-center py-20">
          <div className="flex flex-col items-center gap-3">
            <Spinner size={28} />
            <span className="text-xs font-mono text-frost-dim">
              Searching embeddings…
            </span>
          </div>
        </div>
      )}

      {/* Results */}
      {!loading && results.length > 0 && (
        <div className="space-y-4">
          {results.map((result, i) => (
            <SearchResultCard key={`${result.chunk_id}-${i}`} result={result} index={i} />
          ))}
        </div>
      )}

      {/* Empty */}
      {!loading && !error && meta && results.length === 0 && (
        <EmptyState
          icon={Search}
          title="No results found"
          description="Try a different query, adjust the filters, or lower the minimum score threshold."
        />
      )}

      {/* Initial state */}
      {!loading && !meta && !error && (
        <div className="flex flex-col items-center justify-center py-20 text-center">
          <div className="w-20 h-20 rounded-2xl bg-ink-800 border border-ink-600 flex items-center justify-center mb-5">
            <Search size={36} className="text-ink-500" />
          </div>
          <p className="font-display text-frost text-lg font-bold mb-2">
            Search your codebase
          </p>
          <p className="text-frost-dim text-sm font-body max-w-sm">
            Use natural language to find functions, classes, patterns, and logic across your repository.
          </p>
          <div className="mt-6 grid grid-cols-2 gap-2 max-w-md w-full">
            {[
              "authentication middleware",
              "database connection pooling",
              "error handling patterns",
              "embedding generation function",
            ].map((ex) => (
              <button
                key={ex}
                onClick={() => setQuery(ex)}
                className="text-left text-xs font-mono px-3 py-2 bg-ink-800 border border-ink-600 rounded-lg text-frost-dim hover:text-acid hover:border-acid/30 transition-all"
              >
                "{ex}"
              </button>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}
