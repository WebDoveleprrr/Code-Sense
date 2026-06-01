// src/pages/ImpactAnalysis.jsx
import React, { useState, useEffect } from "react";
import { repositoriesApi, impactApi } from "../services/api";
import toast from "react-hot-toast";
import { Play, Activity, Share2, Layers, AlertOctagon, HelpCircle } from "lucide-react";

export default function ImpactAnalysis() {
  const [repos, setRepos] = useState([]);
  const [selectedRepo, setSelectedRepo] = useState("");
  const [filePath, setFilePath] = useState("");
  const [symbolName, setSymbolName] = useState("");
  const [algorithm, setAlgorithm] = useState("bfs");
  const [loading, setLoading] = useState(false);
  const [result, setResult] = useState(null);

  useEffect(() => {
    repositoriesApi.list()
      .then((data) => {
        setRepos(data);
        if (data.length > 0) setSelectedRepo(data[0].id);
      })
      .catch((err) => toast.error("Failed to load repositories: " + err.message));
  }, []);

  const handleRunAnalysis = async (e) => {
    e.preventDefault();
    if (!filePath) {
      toast.error("Please enter a target file path.");
      return;
    }
    setLoading(true);
    try {
      const res = await impactApi.analyze({
        repo_id: selectedRepo,
        file_path: filePath,
        symbol_name: symbolName || null,
        algorithm,
      });
      setResult(res);
      toast.success("Impact analysis completed!");
    } catch (err) {
      toast.error(err.message || "Failed to run impact analysis");
    } finally {
      setLoading(false);
    }
  };

  const getRiskColor = (score) => {
    if (score < 3.0) return "text-emerald-400 border-emerald-500/20 bg-emerald-500/5";
    if (score < 7.0) return "text-amber-400 border-amber-500/20 bg-amber-500/5";
    return "text-rose-400 border-rose-500/20 bg-rose-500/5";
  };

  return (
    <div className="p-8 max-w-7xl mx-auto space-y-8 font-sans text-slate-200">
      {/* Header */}
      <div>
        <h1 className="text-3xl font-extrabold bg-gradient-to-r from-purple-400 via-indigo-300 to-emerald-400 bg-clip-text text-transparent">
          Impact Analysis
        </h1>
        <p className="text-slate-400 mt-2 text-sm">
          Simulate changes to predict code breakage using BFS/DFS graph traversals.
        </p>
      </div>

      {/* Control Card */}
      <div className="p-6 bg-slate-900/40 backdrop-blur-md border border-slate-800 rounded-2xl shadow-xl">
        <form onSubmit={handleRunAnalysis} className="grid grid-cols-1 md:grid-cols-4 gap-6 items-end">
          <div>
            <label className="block text-xs font-semibold text-slate-400 uppercase tracking-wider mb-2">
              Repository
            </label>
            <select
              value={selectedRepo}
              onChange={(e) => setSelectedRepo(e.target.value)}
              className="w-full px-4 py-2.5 bg-slate-950/80 border border-slate-800 rounded-xl text-slate-200 focus:outline-none focus:ring-2 focus:ring-purple-500/40"
            >
              {repos.map((r) => (
                <option key={r.id} value={r.id}>
                  {r.name}
                </option>
              ))}
            </select>
          </div>

          <div>
            <label className="block text-xs font-semibold text-slate-400 uppercase tracking-wider mb-2">
              File Path (e.g. main.py)
            </label>
            <input
              type="text"
              value={filePath}
              onChange={(e) => setFilePath(e.target.value)}
              placeholder="src/utils.py"
              required
              className="w-full px-4 py-2.5 bg-slate-950/80 border border-slate-800 rounded-xl text-slate-200 placeholder-slate-600 focus:outline-none focus:ring-2 focus:ring-purple-500/40"
            />
          </div>

          <div>
            <label className="block text-xs font-semibold text-slate-400 uppercase tracking-wider mb-2">
              Symbol Name (Optional)
            </label>
            <input
              type="text"
              value={symbolName}
              onChange={(e) => setSymbolName(e.target.value)}
              placeholder="clean_data"
              className="w-full px-4 py-2.5 bg-slate-950/80 border border-slate-800 rounded-xl text-slate-200 placeholder-slate-600 focus:outline-none focus:ring-2 focus:ring-purple-500/40"
            />
          </div>

          <div className="flex gap-4">
            <div className="flex-1">
              <label className="block text-xs font-semibold text-slate-400 uppercase tracking-wider mb-2">
                Traversal
              </label>
              <select
                value={algorithm}
                onChange={(e) => setAlgorithm(e.target.value)}
                className="w-full px-4 py-2.5 bg-slate-950/80 border border-slate-800 rounded-xl text-slate-200 focus:outline-none focus:ring-2 focus:ring-purple-500/40"
              >
                <option value="bfs">BFS (Breadth-First)</option>
                <option value="dfs">DFS (Depth-First)</option>
              </select>
            </div>

            <button
              type="submit"
              disabled={loading}
              className="px-6 py-2.5 bg-gradient-to-r from-purple-600 to-indigo-600 hover:from-purple-500 hover:to-indigo-500 text-white rounded-xl font-medium shadow-lg shadow-purple-500/10 hover:shadow-purple-500/20 transition-all duration-200 disabled:opacity-50 flex items-center justify-center gap-2"
            >
              {loading ? (
                <div className="w-5 h-5 border-2 border-white/30 border-t-white rounded-full animate-spin"></div>
              ) : (
                <>
                  <Play size={16} />
                  Analyze
                </>
              )}
            </button>
          </div>
        </form>
      </div>

      {/* Result Display */}
      {result && (
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-8">
          
          {/* Risk Card */}
          <div className={`p-6 border rounded-2xl flex flex-col items-center justify-center text-center ${getRiskColor(result.risk_score)}`}>
            <Activity className="w-12 h-12 mb-3" />
            <div className="text-sm font-semibold tracking-wider uppercase mb-1">Calculated Change Risk</div>
            <div className="text-6xl font-extrabold">{result.risk_score}</div>
            <div className="text-xs text-slate-400 mt-3 max-w-xs font-mono">
              Formula: file_count_weight + function_count_weight + depth_weight
            </div>
          </div>

          {/* Affected Files & Functions */}
          <div className="p-6 bg-slate-900/40 border border-slate-800 rounded-2xl space-y-6">
            <div>
              <div className="flex items-center gap-2 font-semibold text-purple-300 mb-3 text-sm">
                <AlertOctagon size={16} />
                Affected Files ({result.affected_files.length})
              </div>
              <div className="max-h-40 overflow-y-auto space-y-1.5 scrollbar-thin">
                {result.affected_files.length > 0 ? (
                  result.affected_files.map((f, i) => (
                    <div key={i} className="px-3 py-1.5 bg-slate-950/60 rounded border border-slate-800/40 text-xs font-mono truncate">
                      {f}
                    </div>
                  ))
                ) : (
                  <div className="text-xs text-slate-500 font-mono">No files affected.</div>
                )}
              </div>
            </div>

            <div>
              <div className="flex items-center gap-2 font-semibold text-emerald-300 mb-3 text-sm">
                <Layers size={16} />
                Affected Symbols / Functions ({result.affected_functions.length})
              </div>
              <div className="max-h-40 overflow-y-auto space-y-1.5 scrollbar-thin">
                {result.affected_functions.length > 0 ? (
                  result.affected_functions.map((fn, i) => (
                    <div key={i} className="px-3 py-1.5 bg-slate-950/60 rounded border border-slate-800/40 text-xs font-mono truncate">
                      {fn}
                    </div>
                  ))
                ) : (
                  <div className="text-xs text-slate-500 font-mono">No functions affected.</div>
                )}
              </div>
            </div>
          </div>

          {/* Dependency Chains */}
          <div className="p-6 bg-slate-900/40 border border-slate-800 rounded-2xl space-y-4">
            <div className="flex items-center gap-2 font-semibold text-indigo-300 text-sm">
              <Share2 size={16} />
              Propagation Chains ({result.dependency_chain.length})
            </div>
            <div className="max-h-80 overflow-y-auto space-y-3 scrollbar-thin">
              {result.dependency_chain.length > 0 ? (
                result.dependency_chain.map((chain, i) => (
                  <div key={i} className="p-3 bg-slate-950/60 border border-slate-800/40 rounded-xl space-y-2">
                    <div className="text-slate-500 text-[10px] font-mono uppercase tracking-widest">Chain #{i + 1}</div>
                    <div className="flex flex-wrap items-center gap-1.5">
                      {chain.map((node, nodeIdx) => (
                        <React.Fragment key={nodeIdx}>
                          <span className="px-2 py-1 bg-slate-900 border border-slate-800 rounded text-[10px] font-mono truncate max-w-[140px]">
                            {node.split("::").pop()}
                          </span>
                          {nodeIdx < chain.length - 1 && <span className="text-slate-600 text-xs">→</span>}
                        </React.Fragment>
                      ))}
                    </div>
                  </div>
                ))
              ) : (
                <div className="text-xs text-slate-500 font-mono">No propagation chains.</div>
              )}
            </div>
          </div>

        </div>
      )}
    </div>
  );
}
