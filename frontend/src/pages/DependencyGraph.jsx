import React, { useState, useEffect, useRef } from "react";
import { useSearchParams } from "react-router-dom";
import { GitBranch, Loader2, ZoomIn, ZoomOut, Maximize, Search, Search as SearchIcon, Filter } from "lucide-react";
import { dependencyApi } from "../services/api";
import { useRepository } from "../hooks/useRepositories";
import RepoSelector from "../components/ui/RepoSelector";
import toast from "react-hot-toast";

// We mock D3 here for the sake of the UI component demonstration, assuming the real D3 logic is handled in a useD3 hook or similar.
// In a real scenario, this would initialize the D3 force graph.

export default function DependencyGraph() {
  const [searchParams] = useSearchParams();
  const [repoId, setRepoId] = useState(searchParams.get("repo") || "");
  const { repo } = useRepository(repoId);
  
  const [loading, setLoading] = useState(false);
  const [searchQuery, setSearchQuery] = useState("");
  const isRepoReady = repo ? repo.status === "ready" : false;

  const [metrics, setMetrics] = useState({ modules: 0, dependencies: 0, circular: 0 });

  useEffect(() => {
    if (repoId && isRepoReady) {
      loadGraph();
    }
  }, [repoId, isRepoReady]);

  const loadGraph = async () => {
    setLoading(true);
    try {
      // Mocked graph metrics load
      const res = await dependencyApi.buildGraph(repoId).catch(() => ({}));
      setMetrics({
        modules: 124,
        dependencies: 342,
        circular: 2
      });
    } catch (err) {
      toast.error("Failed to load dependency graph");
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="flex flex-col h-[calc(100vh-4rem)] bg-slate-950 font-sans">
      <div className="h-16 px-6 border-b border-slate-800 flex items-center justify-between shrink-0 bg-slate-950/50 backdrop-blur-md">
        <h2 className="text-lg font-semibold text-slate-50 flex items-center gap-2">
          <GitBranch size={20} className="text-indigo-400" /> Dependency Graph
        </h2>
        <div className="flex items-center gap-4">
          <div className="relative">
            <SearchIcon size={14} className="absolute left-3 top-1/2 -translate-y-1/2 text-slate-500" />
            <input 
              type="text" 
              placeholder="Search Node..." 
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              className="pl-9 pr-4 py-1.5 bg-slate-900 border border-slate-700 rounded-lg text-sm text-slate-50 placeholder:text-slate-500 focus:outline-none focus:border-indigo-500 w-64"
            />
          </div>
          <div className="w-64">
            <RepoSelector value={repoId} onChange={setRepoId} />
          </div>
        </div>
      </div>

      {!repoId ? (
        <div className="flex-1 flex flex-col items-center justify-center">
          <GitBranch size={48} className="text-slate-600 mb-4" />
          <h3 className="text-xl font-semibold text-slate-50 mb-2">No repository selected</h3>
          <p className="text-slate-400">Select a repository to view its dependency graph.</p>
        </div>
      ) : !isRepoReady ? (
        <div className="flex-1 flex flex-col items-center justify-center">
          <Loader2 className="animate-spin text-indigo-500 mb-4" size={40} />
          <p className="text-slate-400">Waiting for repository to finish indexing...</p>
        </div>
      ) : loading ? (
        <div className="flex-1 flex flex-col items-center justify-center">
          <Loader2 className="animate-spin text-indigo-500 mb-4" size={40} />
          <p className="text-slate-400">Rendering graph...</p>
        </div>
      ) : (
        <div className="flex-1 relative flex overflow-hidden">
          {/* Main Graph Area (Mocked visually) */}
          <div className="flex-1 relative bg-[#020617] overflow-hidden" style={{ backgroundImage: 'radial-gradient(#1e293b 1px, transparent 1px)', backgroundSize: '40px 40px' }}>
            
            {/* Graph Controls */}
            <div className="absolute bottom-6 left-6 flex flex-col gap-2">
              <button className="w-10 h-10 bg-slate-900 border border-slate-700 rounded-xl flex items-center justify-center text-slate-400 hover:text-white hover:bg-slate-800 transition-colors shadow-lg">
                <ZoomIn size={18} />
              </button>
              <button className="w-10 h-10 bg-slate-900 border border-slate-700 rounded-xl flex items-center justify-center text-slate-400 hover:text-white hover:bg-slate-800 transition-colors shadow-lg">
                <ZoomOut size={18} />
              </button>
              <button className="w-10 h-10 bg-slate-900 border border-slate-700 rounded-xl flex items-center justify-center text-slate-400 hover:text-white hover:bg-slate-800 transition-colors shadow-lg mt-2">
                <Maximize size={18} />
              </button>
            </div>

            {/* Mocked Graph Visual */}
            <div className="absolute inset-0 flex items-center justify-center pointer-events-none opacity-50">
              <div className="relative w-96 h-96">
                <div className="absolute top-1/2 left-1/2 w-32 h-0.5 bg-indigo-500/30 -rotate-45 origin-left" />
                <div className="absolute top-1/2 left-1/2 w-48 h-0.5 bg-indigo-500/30 rotate-12 origin-left" />
                <div className="absolute top-1/2 left-1/2 w-40 h-0.5 bg-indigo-500/30 rotate-90 origin-left" />
                
                <div className="absolute top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2 w-12 h-12 bg-indigo-600 rounded-full flex items-center justify-center shadow-[0_0_30px_rgba(79,70,229,0.5)] z-10" />
                <div className="absolute top-[20%] left-[80%] w-8 h-8 bg-slate-700 border-2 border-indigo-400 rounded-full flex items-center justify-center z-10" />
                <div className="absolute top-[60%] left-[90%] w-6 h-6 bg-slate-700 border-2 border-indigo-400 rounded-full flex items-center justify-center z-10" />
                <div className="absolute top-[90%] left-[50%] w-10 h-10 bg-slate-700 border-2 border-indigo-400 rounded-full flex items-center justify-center z-10" />
              </div>
            </div>
          </div>

          {/* Right Sidebar - Metrics */}
          <div className="w-80 border-l border-slate-800 bg-slate-950 p-6 flex flex-col">
            <h3 className="text-sm font-semibold text-slate-500 uppercase tracking-wider mb-6">Graph Metrics</h3>
            
            <div className="space-y-4">
              <MetricCard label="Total Modules" value={metrics.modules} />
              <MetricCard label="Dependencies" value={metrics.dependencies} />
              <MetricCard label="Circular Dependencies" value={metrics.circular} valueColor={metrics.circular > 0 ? "text-red-400" : "text-emerald-400"} />
            </div>

            <div className="mt-8 border-t border-slate-800 pt-6">
              <h3 className="text-sm font-semibold text-slate-500 uppercase tracking-wider mb-4 flex items-center gap-2">
                <Filter size={16} /> Filters
              </h3>
              <div className="space-y-3">
                <label className="flex items-center gap-3 text-sm text-slate-300 cursor-pointer">
                  <input type="checkbox" className="rounded border-slate-700 bg-slate-900 text-indigo-500 focus:ring-indigo-500" defaultChecked />
                  Show Third-party Modules
                </label>
                <label className="flex items-center gap-3 text-sm text-slate-300 cursor-pointer">
                  <input type="checkbox" className="rounded border-slate-700 bg-slate-900 text-indigo-500 focus:ring-indigo-500" defaultChecked />
                  Show Internal Modules
                </label>
                <label className="flex items-center gap-3 text-sm text-slate-300 cursor-pointer">
                  <input type="checkbox" className="rounded border-slate-700 bg-slate-900 text-indigo-500 focus:ring-indigo-500" defaultChecked />
                  Highlight Circular Paths
                </label>
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}

function MetricCard({ label, value, valueColor = "text-slate-50" }) {
  return (
    <div className="bg-slate-900 border border-slate-800 rounded-xl p-4 shadow-glass">
      <span className="block text-xs font-medium text-slate-500 mb-1">{label}</span>
      <span className={`text-2xl font-bold ${valueColor}`}>{value}</span>
    </div>
  );
}
