// src/components/ui/RepoSelector.jsx
import React, { useState, useRef, useEffect } from "react"; //useref stores ref or address to html element
import { ChevronDown, Database, CheckCircle } from "lucide-react";
import { useRepositories } from "../../hooks/useRepositories";
import { statusDot } from "../../utils/helpers";

export default function RepoSelector({ value, onChange, filterStatus = "ready" }) {
  const { repos, loading } = useRepositories(); //current selected repo get /repo
  const [open, setOpen] = useState(false); //controls dropdowm
  const ref = useRef(null);
  //filtered based on status of repo(embedded or finished etc)
  const filtered = filterStatus
    ? repos.filter((r) => r.status === filterStatus)
    : repos;

  const selected = repos.find((r) => r.id === value);

  useEffect(() => {
    const handleClick = (e) => {
      if (ref.current && !ref.current.contains(e.target)) setOpen(false);
    };
    document.addEventListener("mousedown", handleClick);
    return () => document.removeEventListener("mousedown", handleClick);
  }, []);

  return (
    <div ref={ref} className="relative">
      <button
        onClick={() => setOpen(!open)}
        className="flex items-center gap-3 w-full bg-ink-800 border border-ink-600 hover:border-acid/30 text-sm font-mono rounded-lg px-4 py-2.5 transition-all text-left"
      >
        <Database size={14} className="text-frost-dim flex-shrink-0" />
        <span className={selected ? "text-frost" : "text-frost-dim"}>
          {loading
            ? "Loading…"
            : selected
            ? selected.name
            : "Select a repository"}
        </span>
        <ChevronDown
          size={14}
          className={`ml-auto text-frost-dim transition-transform ${open ? "rotate-180" : ""}`}
        />
      </button>
      {/* dropdown list */}
      {open && (
        <div className="absolute top-full left-0 right-0 mt-1 bg-ink-800 border border-ink-600 rounded-xl shadow-glass z-50 overflow-hidden max-h-64 overflow-y-auto">
          {filtered.length === 0 ? (
            <div className="px-4 py-3 text-xs text-frost-dim font-mono">
              {filterStatus === "ready"
                ? "No indexed repositories yet"
                : "No repositories found"}
            </div>
          ) : (
            filtered.map((repo) => (
              <button
                key={repo.id}
                onClick={() => {
                  onChange(repo.id);
                  setOpen(false);
                }}
                className={`flex items-center gap-3 w-full px-4 py-2.5 text-sm font-mono text-left transition-colors hover:bg-ink-700 ${
                  value === repo.id ? "bg-acid-muted text-acid" : "text-frost"
                }`}
              >
                <span className={`w-2 h-2 rounded-full flex-shrink-0 ${statusDot(repo.status)}`} />
                <span className="flex-1 truncate">{repo.name}</span>
                {repo.owner && (
                  <span className="text-xs text-frost-dim">@{repo.owner}</span>
                )}
                {value === repo.id && (
                  <CheckCircle size={12} className="text-acid" />
                )}
              </button>
            ))
          )}
        </div>
      )}
    </div>
  );
}
