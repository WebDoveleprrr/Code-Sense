//If I modify a file,what else can break in the repo
//auth/middleware.py imported by auth.py imported by users.py used by Frontend API
//Now if you change: auth/middleware.py you might accidentally break: auth.py,users.py,frontend login
//This chain reaction is called: Blast Radius
import React, { useState } from "react";
import { useSearchParams } from "react-router-dom"; //get url
import { Shuffle, Loader2, FileCode2, ArrowRight, Server, Globe, FileStack } from "lucide-react";
import { useRepository } from "../hooks/useRepositories";
import RepoSelector from "../components/ui/RepoSelector"; //Choose repository
import { impactApi, repositoriesApi } from "../services/api";

export default function ImpactAnalysis() {
  const [searchParams] = useSearchParams();
  const [repoId, setRepoId] = useState(searchParams.get("repo") || "");
  const { repo } = useRepository(repoId);
  
  const [loading, setLoading] = useState(false);
  const [selectedFile, setSelectedFile] = useState(""); //Target file for analysis
  const [impactData, setImpactData] = useState(null);
  const [error, setError] = useState(null);
  const [algorithm, setAlgorithm] = useState("bfs");
  const abortControllerRef = React.useRef(null);

  React.useEffect(() => {
    setImpactData(null);
    setError(null);
    setSelectedFile("");
    return () => {
      if (abortControllerRef.current) {
        abortControllerRef.current.abort();
      }
    };
  }, [repoId]);
  
  const isRepoReady = repo ? repo.status === "ready" : false;
  
  const handleAnalyze = async () => {
    if (!repoId || !selectedFile.trim()) return;
    
    if (abortControllerRef.current) {
      abortControllerRef.current.abort();
    }
    const controller = new AbortController();
    abortControllerRef.current = controller;

    setLoading(true);
    setError(null);
    setImpactData(null);
    
    try {
      const res = await impactApi.analyze({
        repo_id: repoId,
        file_path: selectedFile.trim(),
        algorithm
      }, { signal: controller.signal });
      if (res.success) {
        setImpactData(res);
      } else {
        throw new Error(res.message || "Failed to calculate impact radius.");
      }
    } catch (err) {
      if (err.name === 'CanceledError' || err.message === 'canceled' || err.code === 'ERR_CANCELED') {
        return;
      }
      setError(err.message || "An error occurred during analysis.");
    } finally {
      if (abortControllerRef.current === controller) {
        setLoading(false);
      }
    }
  };

  return (
    <div className="flex flex-col h-[calc(100vh-4rem)] bg-slate-950 font-sans">
      <div className="h-16 px-6 border-b border-slate-800 flex items-center justify-between shrink-0 bg-slate-950/50 backdrop-blur-md">
        <h2 className="text-lg font-semibold text-slate-50 flex items-center gap-2">
          <Shuffle size={20} className="text-indigo-400" /> Impact Analysis
        </h2>
        <div className="w-64">
          <RepoSelector value={repoId} onChange={setRepoId} />
        </div>
      </div>

      {!repoId ? (
        <div className="flex-1 flex flex-col items-center justify-center">
          <Shuffle size={48} className="text-slate-600 mb-4" />
          <h3 className="text-xl font-semibold text-slate-50 mb-2">No repository selected</h3>
          <p className="text-slate-400">Select a repository to analyze impact.</p>
        </div>
      ) : !isRepoReady ? (
        <div className="flex-1 flex flex-col items-center justify-center">
          <Loader2 className="animate-spin text-indigo-500 mb-4" size={40} />
          <p className="text-slate-400">Waiting for repository to finish indexing...</p>
        </div>
      ) : (
        <div className="flex-1 flex overflow-hidden">
          
          {/* Left Sidebar - File Selection */}
          <div className="w-80 border-r border-slate-800 bg-slate-950 p-6 flex flex-col shrink-0">
            <h3 className="text-sm font-semibold text-slate-500 uppercase tracking-wider mb-4">Select Target</h3>
            <div className="mb-6">
              <label className="block text-xs font-medium text-slate-400 mb-2">File Path</label>
              <input 
                type="text" 
                list="file-list"
                value={selectedFile}
                onChange={(e) => setSelectedFile(e.target.value)}
                className="w-full bg-slate-900 border border-slate-700 rounded-lg px-3 py-2 text-sm text-slate-50 focus:border-indigo-500 outline-none"
                placeholder="Start typing file path..."
              />
              <datalist id="file-list">
                {repo?.repo_metadata?.files
                  ?.filter(f => {
                    const path = (f.file_path || (typeof f === 'string' ? f : '')).toLowerCase();
                    return path && !path.includes('docs') && !path.includes('test') && !path.includes('example') && !path.includes('vendor') && !path.includes('cache') && !path.includes('venv') && !path.includes('env') && !path.includes('generated');
                  })
                  .map((f, i) => (
                  <option key={i} value={f.file_path || (typeof f === 'string' ? f : '')} />
                ))}
              </datalist>
            </div>
            <div className="mb-6">
              <label className="block text-xs font-medium text-slate-400 mb-2">Traversal Algorithm</label>
              <div className="flex bg-slate-900 rounded-lg p-1 border border-slate-700">
                <button
                  onClick={() => setAlgorithm("bfs")}
                  className={`flex-1 py-1.5 text-xs font-medium rounded-md transition-colors ${
                    algorithm === "bfs" ? "bg-indigo-600 text-white shadow" : "text-slate-400 hover:text-slate-200"
                  }`}
                >
                  BFS (Breadth-First)
                </button>
                <button
                  onClick={() => setAlgorithm("dfs")}
                  className={`flex-1 py-1.5 text-xs font-medium rounded-md transition-colors ${
                    algorithm === "dfs" ? "bg-indigo-600 text-white shadow" : "text-slate-400 hover:text-slate-200"
                  }`}
                >
                  DFS (Depth-First)
                </button>
              </div>
            </div>
            <button
              onClick={handleAnalyze}
              disabled={loading || !selectedFile.trim() || !isRepoReady}
              className="w-full py-3 bg-indigo-600 hover:bg-indigo-700 disabled:bg-slate-800 disabled:text-slate-500 text-white rounded-xl font-medium transition-colors shadow-glow flex items-center justify-center gap-2"
            >
              {loading ? <Loader2 size={18} className="animate-spin" /> : null} Analyze Blast Radius
            </button>
          </div>

          {/* Main Area */}
          <div className="flex-1 p-8 overflow-y-auto bg-slate-900">
            {loading ? (
              <div className="h-full flex flex-col items-center justify-center">
                <Loader2 size={40} className="text-indigo-500 animate-spin mb-4" />
                <p className="text-slate-400">Calculating dependency blast radius...</p>
              </div>
            ) : error ? (
              <div className="h-full flex flex-col items-center justify-center">
                <Shuffle size={48} className="text-red-500 mb-4" />
                <h3 className="text-xl font-semibold text-slate-50 mb-2">Analysis Failed</h3>
                <p className="text-slate-400">{error}</p>
              </div>
            ) : !impactData ? (
              <div className="h-full flex flex-col items-center justify-center">
                <Shuffle size={48} className="text-slate-600 mb-4 opacity-50" />
                <h3 className="text-xl font-semibold text-slate-50 mb-2">Ready to Analyze</h3>
                <p className="text-slate-400">Enter a target file path and click Analyze.</p>
              </div>
            ) : (
              <div className="max-w-5xl mx-auto space-y-8 animate-fade-in">
                
                {/* Summary Metrics */}
                <div className="bg-slate-950 border border-slate-800 rounded-3xl p-8 shadow-glass">
                  <div className="flex items-center gap-4 mb-8">
                    <div className="w-12 h-12 bg-indigo-500/10 rounded-xl flex items-center justify-center">
                      <FileCode2 size={24} className="text-indigo-400" />
                    </div>
                    <div className="min-w-0 flex-1">
                      <h2 className="text-xl font-bold text-slate-50 truncate" title={selectedFile}>{selectedFile}</h2>
                      <p className="text-sm text-slate-400">Impact Analysis Summary</p>
                    </div>
                  </div>

                  <div className="grid grid-cols-1 md:grid-cols-3 lg:grid-cols-4 gap-6">
                    <MetricBox icon={Globe} label="Impact Score" value={Math.round(impactData.impact_score || 0)} color="text-indigo-400" />
                    <MetricBox icon={Globe} label="Risk Level" value={impactData.risk_level || "Low"} color={impactData.risk_level === 'Critical' ? 'text-rose-500' : impactData.risk_level === 'High' ? 'text-orange-500' : impactData.risk_level === 'Medium' ? 'text-amber-400' : 'text-emerald-400'} />
                    <MetricBox icon={FileStack} label="Files Affected" value={impactData.affected_files?.length || 0} color="text-amber-400" />
                    <MetricBox icon={Server} label="Functions Affected" value={impactData.affected_functions?.length || 0} color="text-rose-400" />
                    <MetricBox icon={Server} label="Classes Affected" value={impactData.affected_classes?.length || 0} color="text-purple-400" />
                    <MetricBox icon={Globe} label="Dependency Depth" value={impactData.dependency_depth || 0} color="text-blue-400" />
                    <MetricBox icon={ArrowRight} label="Fan-In" value={impactData.fan_in || 0} color="text-teal-400" />
                    <MetricBox icon={ArrowRight} label="Fan-Out" value={impactData.fan_out || 0} color="text-teal-400" />
                  </div>
                  
                  {impactData.score_reason && (
                    <div className="mt-6 p-4 bg-slate-900 border border-slate-700 rounded-xl">
                      <h4 className="text-sm font-semibold text-slate-400 mb-2">Score Explanation</h4>
                      <p className="text-slate-300 text-sm">{impactData.score_reason}</p>
                    </div>
                  )}
                </div>

                {/* Visual Flow Diagram */}
                <div className="bg-slate-950 border border-slate-800 rounded-3xl p-8 shadow-glass">
                  <h3 className="text-lg font-semibold text-slate-50 mb-8">Impact Flow (Dependency Graph)</h3>
                  
                  {(!impactData.graph_nodes || impactData.graph_nodes.length === 0) ? (
                    <div className="py-8 text-center text-slate-500">
                      No cascading impact found for this target.
                    </div>
                  ) : (
                    <div className="flex flex-col gap-8">
                      <div className="overflow-x-auto pb-4 bg-slate-900 rounded-2xl p-4 border border-slate-800 min-h-[300px]">
                        <MermaidChart data={impactData} selectedFile={selectedFile} />
                      </div>
                      
                      <div className="bg-slate-900 rounded-2xl p-6 border border-slate-800">
                         <h4 className="text-sm font-semibold text-slate-400 mb-4 tracking-wider uppercase">Traversal Order ({algorithm.toUpperCase()})</h4>
                         <div className="flex flex-wrap gap-2">
                           {impactData.traversal_order?.map((nodeId, idx) => (
                             <div key={idx} className="flex items-center gap-2">
                               <div className="px-3 py-1 bg-slate-800 border border-slate-700 rounded text-xs font-mono text-slate-300 max-w-[200px] truncate" title={nodeId}>
                                 {nodeId.split('::').pop()}
                               </div>
                               {idx < impactData.traversal_order.length - 1 && <ArrowRight size={14} className="text-slate-600" />}
                             </div>
                           ))}
                         </div>
                      </div>
                    </div>
                  )}
                </div>

              </div>
            )}
          </div>
        </div>
      )}
    </div>
  );
}

function MetricBox({ icon: Icon, label, value, color }) {
  return (
    <div className="bg-slate-900 border border-slate-800 rounded-2xl p-6">
      <div className="flex items-center gap-3 mb-4">
        <Icon size={20} className="text-slate-500" />
        <span className="text-sm font-medium text-slate-400">{label}</span>
      </div>
      <div className={`text-4xl font-bold ${color}`}>{value}</div>
    </div>
  );
}

import mermaid from "mermaid";
import { useEffect, useRef } from "react";

mermaid.initialize({
  startOnLoad: false,
  theme: 'base',
  themeVariables: {
    fontFamily: 'ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, monospace',
    primaryColor: '#1e293b',
    primaryTextColor: '#f8fafc',
    primaryBorderColor: '#334155',
    lineColor: '#475569',
    secondaryColor: '#312e81',
    tertiaryColor: '#0f172a'
  },
  flowchart: { curve: 'basis', padding: 20 },
  securityLevel: 'loose'
});

function MermaidChart({ data, selectedFile }) {
  const containerRef = useRef(null);
  
  useEffect(() => {
    if (!containerRef.current || !data) return;
    
    let lines = ["graph TD"];
    
    const safeNodeId = (id) => id.replace(/[^a-zA-Z0-9_]/g, "_");
    
    const targetSuffix = selectedFile.trim().replace(/\\/g, '/').replace('./', '').replace(/^[\/]+/, '');
    
    data.graph_nodes?.forEach(n => {
        let label = (n.label || n.id).replace(/"/g, "'");
        let safeId = safeNodeId(n.id);
        lines.push(`${safeId}["${label}"]`);
        
        if (n.id.endsWith(targetSuffix) || n.id.includes(targetSuffix)) {
            lines.push(`style ${safeId} fill:#4f46e5,stroke:#818cf8,stroke-width:2px`);
        } else {
            lines.push(`style ${safeId} fill:#1e293b,stroke:#334155`);
        }
    });
    
    data.graph_edges?.forEach(e => {
        let source = safeNodeId(e.source);
        let target = safeNodeId(e.target);
        lines.push(`${source} --> ${target}`);
    });
    const graphString = lines.join("\n");
    const renderChart = async () => {
      try {
        const id = `mermaid-impact-${Math.random().toString(36).substr(2, 9)}`;
        const { svg } = await mermaid.render(id, graphString);
        if (containerRef.current) {
          containerRef.current.innerHTML = svg;
        }
      } catch (err) {
        console.error("Mermaid rendering failed:", err);
        if (containerRef.current) {
          containerRef.current.innerHTML = `<div class="p-4 text-rose-400 bg-rose-950/20 border border-rose-900 rounded">Failed to render graph.</div>`;
        }
      }
    };
    
    renderChart();
  }, [data, selectedFile]);

  return (
    <div 
      ref={containerRef} 
      className="flex justify-center items-center w-full min-h-[300px]"
    />
  );
}
