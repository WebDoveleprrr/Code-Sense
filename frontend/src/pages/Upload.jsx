import React, { useState, useRef, useCallback } from "react";
import { useNavigate } from "react-router-dom";
import toast from "react-hot-toast";
import { 
  Upload as UploadIcon, 
  Github, 
  CheckCircle2, 
  Loader2, 
  X, 
  FileCode2, 
  RefreshCw,
  Search,
  MessageSquare,
  Building2,
  Box
} from "lucide-react";
import { repositoriesApi } from "../services/api";
import { useRepositories } from "../hooks/useRepositories";

const SUPPORTED_LANGUAGES = ["Python", "Java", "C++", "JavaScript", "TypeScript"];

export default function UploadPage() {
  const navigate = useNavigate();
  const { mutate } = useRepositories();
  const [url, setUrl] = useState(""); //github link
  const [file, setFile] = useState(null); //zip file
  const [loading, setLoading] = useState(false);
  const [dragOver, setDragOver] = useState(false); //drag and drop file
  const [ingestState, setIngestState] = useState(null); // 'cloning', 'parsing', 'chunking', 'embedding', 'indexing', 'ready'
  const [indexedRepo, setIndexedRepo] = useState(null); //repo returned from backend
  const inputRef = useRef(null);
  //runs when a file being dragged
  const handleDrop = useCallback((e) => {
    e.preventDefault();
    setDragOver(false);
    const dropped = e.dataTransfer.files[0];
    if (dropped?.name.endsWith(".zip")) {
      setFile(dropped);
      setUrl("");
    } else {
      toast.error("Only .zip files are accepted");
    }
  }, []);
  //runs when click file to browse
  const handleFile = (e) => {
    const f = e.target.files[0];
    if (f?.name.endsWith(".zip")) {
      setFile(f);
      setUrl("");
    } else {
      toast.error("Only .zip files are accepted");
    }
  };

  const simulateProgress = async () => {
    const states = ['cloning', 'parsing', 'chunking', 'embedding', 'indexing', 'ready'];
    for (let i = 0; i < states.length; i++) {
      setIngestState(states[i]);
      if (states[i] !== 'ready') {
        // Wait 1.5s to 2.5s per step
        await new Promise(r => setTimeout(r, 1500 + Math.random() * 1000));
      }
    }
  };
  //runs when start analysis cicked
  const handleSubmit = async () => {
    if (!file && !url.trim()) {
      return toast.error("Please provide a GitHub URL or a ZIP file.");
    }

    setLoading(true);
    setIngestState('cloning');
    
    try {
      let res;
      if (file) {
        res = await repositoriesApi.uploadZip(file, () => {});
      } else {
        if (!url.includes("github.com")) {
          throw new Error("Must be a valid GitHub URL");
        }
        res = await repositoriesApi.ingestGitHub(url.trim(), "main");
      }
      
      // Simulate the UI steps for the recruiter demo feel
      await simulateProgress();
      
      mutate();
      setIndexedRepo(res);
      toast.success("Repository successfully indexed!");
    } catch (err) {
      toast.error(err.message || "Failed to ingest repository");
      setIngestState(null);
    } finally {
      setLoading(false);
    }
  };
  //if success show summary else go to upload
  if (indexedRepo && ingestState === 'ready') {
    return <RepositorySummary repo={indexedRepo} navigate={navigate} />;
  }

  return (
    <div className="p-8 max-w-4xl mx-auto">
      <div className="mb-10 text-center">
        <h1 className="text-3xl font-bold text-slate-50 mb-3">Upload Repository</h1>
        <p className="text-slate-400 max-w-xl mx-auto">
          Ingest any codebase to enable semantic search, architecture discovery, and AI-powered exploration.
        </p>
      </div>

      <div className="bg-slate-900 border border-slate-800 rounded-3xl p-8 mb-8">
        {ingestState ? (
          <IngestionProgress state={ingestState} />
        ) : (
          <div className="space-y-8">
            <div
              onDragOver={(e) => { e.preventDefault(); setDragOver(true); }}
              onDragLeave={() => setDragOver(false)}
              onDrop={handleDrop}
              onClick={() => !file && inputRef.current?.click()}
              className={`relative border-2 border-dashed rounded-2xl p-12 text-center cursor-pointer transition-all ${
                dragOver
                  ? "border-indigo-500 bg-indigo-500/10"
                  : file
                  ? "border-emerald-500/50 bg-emerald-500/5 cursor-default"
                  : "border-slate-700 hover:border-indigo-500/50 hover:bg-slate-800/50"
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
                  <Box size={40} className="text-emerald-400 mx-auto mb-4" />
                  <p className="font-semibold text-slate-50 mb-1">{file.name}</p>
                  <p className="text-sm text-slate-400 mb-4">{(file.size / 1024 / 1024).toFixed(2)} MB</p>
                  <button
                    onClick={(e) => { e.stopPropagation(); setFile(null); }}
                    className="text-sm text-red-400 hover:text-red-300 font-medium flex items-center gap-1 mx-auto bg-red-400/10 px-3 py-1 rounded-full transition-colors"
                  >
                    <X size={14} /> Remove File
                  </button>
                </div>
              ) : (
                <>
                  <div className="w-16 h-16 bg-slate-800 rounded-full flex items-center justify-center mx-auto mb-4">
                    <UploadIcon size={24} className="text-slate-400" />
                  </div>
                  <h3 className="text-lg font-semibold text-slate-50 mb-2">
                    Drag and Drop Area
                  </h3>
                  <p className="text-slate-400 mb-6">Drop a ZIP file here, or click to browse.</p>
                  
                  <div className="flex items-center justify-center gap-4 text-sm text-slate-500">
                    <div className="h-px bg-slate-700 w-16" />
                    <span>OR PASTE GITHUB URL</span>
                    <div className="h-px bg-slate-700 w-16" />
                  </div>
                </>
              )}
            </div>

            {!file && (
              <div>
                <div className="relative">
                  <div className="absolute inset-y-0 left-0 pl-4 flex items-center pointer-events-none">
                    <Github size={18} className="text-slate-400" />
                  </div>
                  <input
                    type="text"
                    value={url}
                    onChange={(e) => setUrl(e.target.value)}
                    placeholder="https://github.com/owner/repository"
                    className="w-full pl-11 pr-4 py-3 bg-slate-950 border border-slate-700 rounded-xl text-slate-50 placeholder:text-slate-500 focus:outline-none focus:border-indigo-500 focus:ring-1 focus:ring-indigo-500 transition-all"
                  />
                </div>
              </div>
            )}

            <button
              onClick={handleSubmit}
              disabled={!file && !url.trim()}
              className="w-full py-4 bg-indigo-600 hover:bg-indigo-700 text-white rounded-xl font-medium transition-all shadow-glow flex items-center justify-center gap-2 disabled:opacity-50 disabled:cursor-not-allowed"
            >
              Start Analysis <UploadIcon size={18} />
            </button>
          </div>
        )}
      </div>

      {!ingestState && (
        <div className="flex flex-col sm:flex-row items-center justify-center gap-6 text-sm text-slate-400">
          <span className="font-medium text-slate-300">Supported Languages:</span>
          <div className="flex flex-wrap gap-4 justify-center">
            {SUPPORTED_LANGUAGES.map(lang => (
              <div key={lang} className="flex items-center gap-1.5">
                <FileCode2 size={16} className="text-slate-500" /> {lang}
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}

function IngestionProgress({ state }) {
  const steps = [
    { id: 'cloning', label: 'Repository Cloned' }, //github_loader.py
    { id: 'parsing', label: 'Files Parsed' }, //repo_parser.py
    { id: 'chunking', label: 'Code Chunked' }, //chunker.py
    { id: 'embedding', label: 'Generating Embeddings' }, //embedding_piepline.py
    { id: 'indexing', label: 'Building Search Index' }  //faiss.store.py
  ];

  const currentIndex = steps.findIndex(s => s.id === state);

  return (
    <div className="py-8 max-w-sm mx-auto">
      <h3 className="text-center text-xl font-semibold text-slate-50 mb-10">
        Analyzing Codebase
      </h3>
      <div className="space-y-6">
        {steps.map((step, idx) => {
          const isCompleted = state === 'ready' || currentIndex > idx;
          const isCurrent = currentIndex === idx;
          const isPending = currentIndex !== -1 && currentIndex < idx;

          return (
            <div key={step.id} className="flex items-center gap-4">
              <div className="w-8 flex justify-center">
                {isCompleted ? (
                  <CheckCircle2 size={24} className="text-emerald-500" />
                ) : isCurrent ? (
                  <RefreshCw size={20} className="text-indigo-400 animate-spin" />
                ) : (
                  <div className="w-5 h-5 rounded-full border-2 border-slate-700" />
                )}
              </div>
              <span className={`text-lg font-medium transition-colors ${
                isCompleted ? 'text-slate-300' : isCurrent ? 'text-indigo-400' : 'text-slate-600'
              }`}>
                {step.label}
              </span>
            </div>
          );
        })}
      </div>
    </div>
  );
}
//shown after ingestion success
function RepositorySummary({ repo, navigate }) {
  return (
    <div className="p-8 max-w-3xl mx-auto mt-10">
      <div className="bg-slate-900 border border-slate-800 rounded-3xl p-10 text-center">
        <div className="w-20 h-20 bg-emerald-500/10 rounded-full flex items-center justify-center mx-auto mb-6">
          <CheckCircle2 size={40} className="text-emerald-400" />
        </div>
        <h2 className="text-3xl font-bold text-slate-50 mb-2">{repo.name || "Repository"}</h2>
        <p className="text-slate-400 mb-10">Analysis complete and ready for exploration.</p>

        <div className="grid grid-cols-3 gap-4 mb-10 text-left">
          <div className="bg-slate-950 border border-slate-800 rounded-2xl p-5">
            <span className="block text-slate-500 text-sm mb-1">Files Found</span>
            <span className="text-2xl font-semibold text-slate-200">{repo.total_files || 0}</span>
          </div>
          <div className="bg-slate-950 border border-slate-800 rounded-2xl p-5">
            <span className="block text-slate-500 text-sm mb-1">Files Indexed</span>
            <span className="text-2xl font-semibold text-slate-200">{repo.indexed_files || 0}</span>
          </div>
          <div className="bg-slate-950 border border-slate-800 rounded-2xl p-5">
            <span className="block text-slate-500 text-sm mb-1">Files Skipped</span>
            <span className="text-2xl font-semibold text-slate-200">{repo.skipped_files || 0}</span>
          </div>
        </div>

        <div className="flex flex-col sm:flex-row gap-4 justify-center">
          <button onClick={() => navigate(`/search?repo=${repo.repo_id || repo.id}`)} className="flex items-center justify-center gap-2 px-6 py-3 bg-indigo-600 hover:bg-indigo-700 text-white rounded-xl font-medium transition-colors shadow-glow">
            <Search size={18} /> Search
          </button>
          <button onClick={() => navigate(`/qa?repo=${repo.repo_id || repo.id}`)} className="flex items-center justify-center gap-2 px-6 py-3 bg-slate-800 hover:bg-slate-700 text-slate-200 rounded-xl font-medium transition-colors">
            <MessageSquare size={18} /> Ask Questions
          </button>
          <button onClick={() => navigate(`/architecture?repo=${repo.repo_id || repo.id}`)} className="flex items-center justify-center gap-2 px-6 py-3 bg-slate-800 hover:bg-slate-700 text-slate-200 rounded-xl font-medium transition-colors">
            <Building2 size={18} /> Architecture
          </button>
        </div>
      </div>
    </div>
  );
}
