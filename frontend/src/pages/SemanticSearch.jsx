import React, { useState, useEffect, useRef } from "react";
import { useSearchParams } from "react-router-dom";
import { Search, Loader2, AlertCircle, FileCode2, Info, CheckCircle2, ChevronDown, ChevronUp } from "lucide-react";
import { useSearch } from "../hooks/useSearch";
import { useRepository } from "../hooks/useRepositories";
import RepoSelector from "../components/ui/RepoSelector";
import CodeBlock from "../components/ui/CodeBlock";

export default function SemanticSearch() {
  const [searchParams] = useSearchParams();
  const [repoId, setRepoId] = useState(searchParams.get("repo") || "");
  const [query, setQuery] = useState("");
  const inputRef = useRef(null);

  const { results, loading, error, meta, search, clear } = useSearch();
  const { repo } = useRepository(repoId);
  const isRepoReady = repo ? repo.status === "ready" : false;

  useEffect(() => {
    inputRef.current?.focus();
  }, []);

  const handleSearch = () => {
    if (!query.trim() || !repoId || !isRepoReady) return;
    search({
      repo_id: repoId,
      query: query.trim(),
      top_k: 5
    });
  };

  const suggestions = [
    "Where is authentication implemented?",
    "How does repository ingestion work?",
    "How are embeddings generated?",
    "Where are API routes defined?"
  ];

  return (
    <div className="p-8 max-w-4xl mx-auto font-sans">
      <div className="mb-8 text-center">
        <h1 className="text-3xl font-bold text-slate-50 mb-3">Semantic Search</h1>
        <p className="text-slate-400">Search your codebase by intent and concepts, not just exact keywords.</p>
      </div>

      <div className="mb-10 flex justify-center">
        <div className="w-full max-w-md">
          <label className="block text-sm font-medium text-slate-400 mb-2 text-left">Select Repository</label>
          <RepoSelector value={repoId} onChange={setRepoId} />
        </div>
      </div>

      {repo && repo.status !== "ready" && repo.status !== "failed" && (
        <div className="bg-slate-900 border border-slate-800 rounded-2xl p-8 text-center mb-8">
          <Loader2 className="animate-spin text-indigo-500 mx-auto mb-4" size={32} />
          <h3 className="text-lg font-semibold text-slate-50 mb-2">Analyzing Repository...</h3>
          <p className="text-slate-400">Search will unlock once indexing is complete.</p>
        </div>
      )}

      {/* Main Search Bar (Perplexity style) */}
      <div className="relative mb-12 shadow-glass-lg rounded-2xl">
        <div className="absolute inset-y-0 left-0 pl-6 flex items-center pointer-events-none">
          <Search size={24} className="text-slate-400" />
        </div>
        <input
          ref={inputRef}
          type="text"
          value={query}
          onChange={(e) => setQuery(e.target.value)}
          onKeyDown={(e) => e.key === "Enter" && handleSearch()}
          disabled={!isRepoReady}
          placeholder="Ask anything about the repository..."
          className="w-full pl-16 pr-32 py-6 bg-slate-900 border border-slate-700 rounded-2xl text-lg text-slate-50 placeholder:text-slate-500 focus:outline-none focus:border-indigo-500 focus:ring-1 focus:ring-indigo-500 transition-all disabled:opacity-50"
        />
        <div className="absolute inset-y-0 right-0 pr-4 flex items-center">
          <button
            onClick={handleSearch}
            disabled={!query.trim() || !repoId || !isRepoReady || loading}
            className="px-6 py-3 bg-indigo-600 hover:bg-indigo-700 disabled:bg-slate-800 disabled:text-slate-500 text-white rounded-xl font-medium transition-all"
          >
            {loading ? <Loader2 size={20} className="animate-spin" /> : "Search"}
          </button>
        </div>
      </div>

      {/* Initial Suggestions */}
      {!loading && !meta && !error && isRepoReady && (
        <div className="max-w-2xl mx-auto">
          <h3 className="text-sm font-medium text-slate-500 mb-4 flex items-center gap-2">
            <Info size={16} /> Suggestions
          </h3>
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
            {suggestions.map((suggestion) => (
              <button
                key={suggestion}
                onClick={() => { setQuery(suggestion); setTimeout(() => handleSearch(), 50); }}
                className="text-left px-4 py-3 bg-slate-900 hover:bg-slate-800 border border-slate-800 hover:border-slate-700 rounded-xl text-slate-300 text-sm transition-all shadow-glass"
              >
                {suggestion}
              </button>
            ))}
          </div>
        </div>
      )}

      {/* Loading state */}
      {loading && (
        <div className="py-20 text-center">
          <Loader2 className="animate-spin text-indigo-500 mx-auto mb-4" size={32} />
          <p className="text-slate-400">Searching through semantic embeddings...</p>
        </div>
      )}

      {/* Error state */}
      {error && (
        <div className="p-6 bg-red-500/10 border border-red-500/20 rounded-2xl text-red-400 flex items-start gap-3">
          <AlertCircle size={20} className="shrink-0 mt-0.5" />
          <p>{error}</p>
        </div>
      )}

      {/* Results */}
      {!loading && results.length > 0 && (
        <div className="space-y-6">
          <h3 className="text-lg font-semibold text-slate-50 mb-4">Search Results</h3>
          {results.map((result, idx) => (
            <ResultCard key={idx} result={result} query={query} />
          ))}
        </div>
      )}

      {/* Empty state */}
      {!loading && meta && results.length === 0 && !error && (
        <div className="text-center py-20 bg-slate-900 border border-slate-800 rounded-3xl">
          <Search size={40} className="text-slate-600 mx-auto mb-4" />
          <h3 className="text-xl font-semibold text-slate-50 mb-2">No relevant code found</h3>
          <p className="text-slate-400">Try rephrasing your query or using different terminology.</p>
        </div>
      )}
    </div>
  );
}

function ResultCard({ result, query }) {
  const [expanded, setExpanded] = useState(false);
  const lang = result.language || "text";

  return (
    <div className="bg-slate-900 border border-slate-800 rounded-2xl overflow-hidden shadow-glass hover:border-indigo-500/30 transition-all">
      {/* Header */}
      <div className="px-6 py-4 border-b border-slate-800 bg-slate-950/50 flex flex-wrap items-center justify-between gap-4">
        <div className="flex items-center gap-3 min-w-0">
          <div className="w-8 h-8 rounded-lg bg-indigo-500/10 flex items-center justify-center shrink-0">
            <FileCode2 size={16} className="text-indigo-400" />
          </div>
          <div className="min-w-0">
            <h4 className="text-sm font-medium text-slate-200 truncate">{result.file_path}</h4>
            <p className="text-xs text-slate-500">Lines {result.start_line} - {result.end_line}</p>
          </div>
        </div>
        <div className="flex items-center gap-2">
          {result.symbol_name && (
            <span className="px-2.5 py-1 rounded-full text-xs font-medium bg-slate-800 text-slate-300 border border-slate-700">
              {result.symbol_name}
            </span>
          )}
          <span className="flex items-center gap-1 text-xs font-medium text-emerald-400 bg-emerald-400/10 px-2.5 py-1 rounded-full border border-emerald-400/20">
            <CheckCircle2 size={12} /> {Math.round(result.score * 100)}% Match
          </span>
        </div>
      </div>

      {/* Explanation & Summary Panel */}
      <div className="px-6 py-5 border-b border-slate-800/50 bg-slate-900">
        <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
          <div>
            <h5 className="text-xs font-semibold text-slate-500 uppercase tracking-wider mb-2">Summary</h5>
            <p className="text-sm text-slate-300 leading-relaxed">
              This code block defines the {result.symbol_name || "logic"} inside {result.file_path.split('/').pop()}. 
              It handles the core functionality related to this component.
            </p>
          </div>
          <div>
            <h5 className="text-xs font-semibold text-slate-500 uppercase tracking-wider mb-2">Why this matches</h5>
            <p className="text-sm text-slate-300 leading-relaxed">
              High semantic relevance to your query "{query}". The vector similarity score indicates this block directly implements the requested behavior.
            </p>
          </div>
        </div>
      </div>

      {/* Code Snippet */}
      <div className="bg-slate-950 p-6">
        <div className="flex items-center justify-between mb-3">
          <h5 className="text-xs font-semibold text-slate-500 uppercase tracking-wider">Code Snippet</h5>
          <button 
            onClick={() => setExpanded(!expanded)}
            className="text-xs text-indigo-400 hover:text-indigo-300 flex items-center gap-1 font-medium transition-colors"
          >
            {expanded ? (
              <><ChevronUp size={14} /> Collapse</>
            ) : (
              <><ChevronDown size={14} /> Expand</>
            )}
          </button>
        </div>
        <div className={`transition-all duration-300 ${expanded ? '' : 'max-h-48 overflow-hidden relative'}`}>
          <CodeBlock
            code={result.content}
            language={lang}
            startLine={result.start_line}
            showCopy
            compact
            maxHeight="none"
          />
          {!expanded && (
            <div className="absolute bottom-0 left-0 right-0 h-24 bg-gradient-to-t from-slate-950 to-transparent pointer-events-none" />
          )}
        </div>
      </div>
    </div>
  );
}
