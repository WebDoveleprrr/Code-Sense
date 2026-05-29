// src/pages/Upload.jsx
import React, { useState, useRef, useCallback } from "react";
import { useNavigate } from "react-router-dom";
import toast from "react-hot-toast";
import {
  Github, Upload as UploadIcon, FolderOpen, CheckCircle,
  AlertCircle, Loader2, ArrowRight, GitBranch, X
} from "lucide-react";
import { repositoriesApi } from "../services/api";
import { Card, Button, Input, SectionHeader, StatusBadge } from "../components/ui";
import { useRepositories } from "../hooks/useRepositories";
import { timeAgo, formatBytes } from "../utils/helpers";

const TABS = ["github", "zip"];

function GitHubForm() {
  const [url, setUrl] = useState("");
  const [branch, setBranch] = useState("main");
  const [loading, setLoading] = useState(false);
  const navigate = useNavigate();

  const handleSubmit = async () => {
    if (!url.trim()) return toast.error("Enter a GitHub URL");
    if (!url.includes("github.com")) return toast.error("Must be a valid GitHub URL");

    setLoading(true);
    try {
      const res = await repositoriesApi.ingestGitHub(url.trim(), branch);
      toast.success(`Repository ingestion started! ID: ${res.repo_id}`);
      navigate(`/search?repo=${res.repo_id}`);
    } catch (err) {
      toast.error(err.message);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="space-y-5">
      <div>
        <label className="block text-xs font-mono text-frost-dim uppercase tracking-widest mb-2">
          GitHub Repository URL
        </label>
        <Input
          placeholder="https://github.com/owner/repository"
          value={url}
          onChange={(e) => setUrl(e.target.value)}
          onKeyDown={(e) => e.key === "Enter" && handleSubmit()}
        />
        <p className="text-xs text-frost-dim font-body mt-1.5">
          Public repositories only. Private repos require token configuration.
        </p>
      </div>

      <div>
        <label className="block text-xs font-mono text-frost-dim uppercase tracking-widest mb-2">
          Branch
        </label>
        <Input
          placeholder="main"
          value={branch}
          onChange={(e) => setBranch(e.target.value)}
          className="w-40"
        />
      </div>

      <div className="bg-ink-800 rounded-xl border border-ink-600 p-4">
        <p className="text-xs font-mono text-frost-dim mb-3">Supported URL formats:</p>
        <div className="space-y-1">
          {[
            "https://github.com/owner/repo",
            "https://github.com/owner/repo.git",
            "https://github.com/owner/repo/tree/branch",
          ].map((ex) => (
            <button
              key={ex}
              onClick={() => setUrl(ex.includes("tree") ? ex : ex)}
              className="block w-full text-left text-xs font-mono text-plasma-light hover:text-acid transition-colors py-0.5 truncate"
            >
              {ex}
            </button>
          ))}
        </div>
      </div>

      <Button
        onClick={handleSubmit}
        loading={loading}
        disabled={!url.trim()}
        size="lg"
        className="w-full justify-center"
        icon={<Github size={15} />}
      >
        {loading ? "Starting ingestion…" : "Ingest Repository"}
      </Button>
    </div>
  );
}

function ZipForm() {
  const [file, setFile] = useState(null);
  const [progress, setProgress] = useState(0);
  const [loading, setLoading] = useState(false);
  const [dragOver, setDragOver] = useState(false);
  const inputRef = useRef(null);
  const navigate = useNavigate();

  const handleDrop = useCallback((e) => {
    e.preventDefault();
    setDragOver(false);
    const dropped = e.dataTransfer.files[0];
    if (dropped?.name.endsWith(".zip")) setFile(dropped);
    else toast.error("Only .zip files are accepted");
  }, []);

  const handleFile = (e) => {
    const f = e.target.files[0];
    if (f?.name.endsWith(".zip")) setFile(f);
    else toast.error("Only .zip files are accepted");
  };

  const handleUpload = async () => {
    if (!file) return;
    setLoading(true);
    setProgress(0);

    try {
      const res = await repositoriesApi.uploadZip(file, (evt) => {
        if (evt.lengthComputable) {
          setProgress(Math.round((evt.loaded / evt.total) * 100));
        }
      });
      toast.success(`ZIP uploaded! Ingestion started.`);
      navigate(`/search?repo=${res.repo_id}`);
    } catch (err) {
      toast.error(err.message);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="space-y-5">
      {/* Drop zone */}
      <div
        onDragOver={(e) => { e.preventDefault(); setDragOver(true); }}
        onDragLeave={() => setDragOver(false)}
        onDrop={handleDrop}
        onClick={() => !file && inputRef.current?.click()}
        className={`relative border-2 border-dashed rounded-xl p-10 text-center cursor-pointer transition-all ${
          dragOver
            ? "border-acid bg-acid-muted"
            : file
            ? "border-acid/40 bg-acid-muted cursor-default"
            : "border-ink-500 hover:border-acid/30 hover:bg-ink-800"
        }`}
      >
        <input
          ref={inputRef}
          type="file"
          accept=".zip"
          className="hidden"
          onChange={handleFile}
        />

        {file ? (
          <div>
            <CheckCircle size={32} className="text-acid mx-auto mb-3" />
            <p className="font-mono text-sm text-frost mb-1">{file.name}</p>
            <p className="text-xs text-frost-dim">{formatBytes(file.size)}</p>
            <button
              onClick={(e) => { e.stopPropagation(); setFile(null); }}
              className="mt-3 text-xs text-frost-dim hover:text-danger font-mono flex items-center gap-1 mx-auto"
            >
              <X size={11} />
              Remove
            </button>
          </div>
        ) : (
          <>
            <FolderOpen size={32} className="text-frost-dim mx-auto mb-3" />
            <p className="font-mono text-sm text-frost mb-1">
              Drop your ZIP here or{" "}
              <span className="text-acid">browse</span>
            </p>
            <p className="text-xs text-frost-dim">Only .zip archives are accepted</p>
          </>
        )}
      </div>

      {/* Progress */}
      {loading && (
        <div>
          <div className="flex justify-between text-xs font-mono mb-1.5">
            <span className="text-frost-dim">Uploading…</span>
            <span className="text-acid">{progress}%</span>
          </div>
          <div className="h-1 bg-ink-700 rounded-full overflow-hidden">
            <div
              className="h-full bg-acid rounded-full transition-all"
              style={{ width: `${progress}%` }}
            />
          </div>
        </div>
      )}

      <Button
        onClick={handleUpload}
        loading={loading}
        disabled={!file}
        size="lg"
        className="w-full justify-center"
        icon={<UploadIcon size={15} />}
      >
        {loading ? `Uploading… ${progress}%` : "Upload & Ingest"}
      </Button>
    </div>
  );
}

function RepoList() {
  const { repos, loading, refetch } = useRepositories();
  const [deleting, setDeleting] = useState(null);

  const handleDelete = async (id, name) => {
    if (!window.confirm(`Delete "${name}"? This cannot be undone.`)) return;
    setDeleting(id);
    try {
      await repositoriesApi.delete(id);
      toast.success("Repository deleted");
      refetch();
    } catch (err) {
      toast.error(err.message);
    } finally {
      setDeleting(null);
    }
  };

  return (
    <div>
      <h3 className="font-display text-sm font-bold text-frost-dim uppercase tracking-widest mb-3">
        All Repositories ({repos.length})
      </h3>
      <div className="space-y-2">
        {loading ? (
          <div className="text-xs text-frost-dim font-mono py-4">Loading…</div>
        ) : repos.length === 0 ? (
          <div className="text-xs text-frost-dim font-mono py-4">
            No repositories yet. Upload one above.
          </div>
        ) : (
          repos.map((repo) => (
            <div
              key={repo.id}
              className="flex items-center gap-3 px-4 py-3 glass rounded-lg"
            >
              <div className="flex-1 min-w-0">
                <p className="text-sm font-mono text-frost truncate">{repo.name}</p>
                <p className="text-xs text-frost-dim">
                  {repo.source} · {repo.total_files || 0} files · {timeAgo(repo.created_at)}
                </p>
              </div>
              <StatusBadge status={repo.status} />
              <button
                onClick={() => handleDelete(repo.id, repo.name)}
                disabled={deleting === repo.id}
                className="text-xs font-mono text-frost-dim hover:text-danger transition-colors disabled:opacity-40"
              >
                {deleting === repo.id ? (
                  <Loader2 size={12} className="animate-spin" />
                ) : (
                  <X size={14} />
                )}
              </button>
            </div>
          ))
        )}
      </div>
    </div>
  );
}

export default function UploadPage() {
  const [tab, setTab] = useState("github");

  return (
    <div className="p-8 max-w-4xl mx-auto">
      <SectionHeader
        title="Upload Repository"
        subtitle="Ingest a codebase for semantic search and AI analysis"
      />

      <div className="grid grid-cols-1 lg:grid-cols-5 gap-8">
        {/* Upload form */}
        <div className="lg:col-span-3">
          <Card>
            {/* Tab selector */}
            <div className="flex gap-2 mb-6">
              {[
                { key: "github", label: "GitHub URL", icon: Github },
                { key: "zip", label: "ZIP Upload", icon: FolderOpen },
              ].map(({ key, label, icon: Icon }) => (
                <button
                  key={key}
                  onClick={() => setTab(key)}
                  className={`flex items-center gap-2 text-sm font-mono px-4 py-2 rounded-lg transition-all ${
                    tab === key
                      ? "bg-acid text-ink-950 font-bold"
                      : "text-frost-dim hover:text-frost hover:bg-ink-700"
                  }`}
                >
                  <Icon size={14} />
                  {label}
                </button>
              ))}
            </div>

            {tab === "github" ? <GitHubForm /> : <ZipForm />}
          </Card>
        </div>

        {/* Sidebar info + repo list */}
        <div className="lg:col-span-2 space-y-5">
          {/* Pipeline info */}
          <Card>
            <h3 className="font-mono text-xs font-bold text-frost-dim uppercase tracking-widest mb-4">
              Ingestion Pipeline
            </h3>
            <div className="space-y-3">
              {[
                { step: "01", label: "Parse", desc: "Extracts Python, JS, C++, and more" },
                { step: "02", label: "Chunk", desc: "Functions, classes, sliding windows" },
                { step: "03", label: "Embed", desc: "sentence-transformers encoding" },
                { step: "04", label: "Index", desc: "FAISS vector index" },
                { step: "05", label: "Ready", desc: "Search, Q&A, analysis enabled" },
              ].map(({ step, label, desc }) => (
                <div key={step} className="flex gap-3">
                  <span className="text-xs font-mono text-acid w-5 mt-0.5">{step}</span>
                  <div>
                    <span className="text-xs font-mono text-frost">{label}</span>
                    <p className="text-xs text-frost-dim font-body">{desc}</p>
                  </div>
                </div>
              ))}
            </div>
          </Card>

          <RepoList />
        </div>
      </div>
    </div>
  );
}
