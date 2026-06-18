import React, { useState } from "react";
import { useSearchParams } from "react-router-dom";
import { Shuffle, Loader2, FileCode2, ArrowRight, Server, Globe, FileStack } from "lucide-react";
import { useRepository } from "../hooks/useRepositories";
import RepoSelector from "../components/ui/RepoSelector";

export default function ImpactAnalysis() {
  const [searchParams] = useSearchParams();
  const [repoId, setRepoId] = useState(searchParams.get("repo") || "");
  const { repo } = useRepository(repoId);
  
  const [loading, setLoading] = useState(false);
  const [selectedFile, setSelectedFile] = useState("auth/middleware.py");
  const isRepoReady = repo ? repo.status === "ready" : false;

  const handleAnalyze = () => {
    setLoading(true);
    setTimeout(() => setLoading(false), 1500); // Mock analysis time
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
                value={selectedFile}
                onChange={(e) => setSelectedFile(e.target.value)}
                className="w-full bg-slate-900 border border-slate-700 rounded-lg px-3 py-2 text-sm text-slate-50 focus:border-indigo-500 outline-none"
              />
            </div>
            <button
              onClick={handleAnalyze}
              className="w-full py-3 bg-indigo-600 hover:bg-indigo-700 text-white rounded-xl font-medium transition-colors shadow-glow flex items-center justify-center gap-2"
            >
              Analyze Blast Radius
            </button>
          </div>

          {/* Main Area */}
          <div className="flex-1 p-8 overflow-y-auto bg-slate-900">
            {loading ? (
              <div className="h-full flex flex-col items-center justify-center">
                <Loader2 size={40} className="text-indigo-500 animate-spin mb-4" />
                <p className="text-slate-400">Calculating dependency blast radius...</p>
              </div>
            ) : (
              <div className="max-w-5xl mx-auto space-y-8 animate-fade-in">
                
                {/* Summary Metrics */}
                <div className="bg-slate-950 border border-slate-800 rounded-3xl p-8 shadow-glass">
                  <div className="flex items-center gap-4 mb-8">
                    <div className="w-12 h-12 bg-indigo-500/10 rounded-xl flex items-center justify-center">
                      <FileCode2 size={24} className="text-indigo-400" />
                    </div>
                    <div>
                      <h2 className="text-xl font-bold text-slate-50">{selectedFile}</h2>
                      <p className="text-sm text-slate-400">Impact Analysis Summary</p>
                    </div>
                  </div>

                  <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
                    <MetricBox icon={FileStack} label="Files Affected" value="23" color="text-amber-400" />
                    <MetricBox icon={Server} label="Services Affected" value="4" color="text-rose-400" />
                    <MetricBox icon={Globe} label="Imports Affected" value="12" color="text-sky-400" />
                  </div>
                </div>

                {/* Visual Flow Diagram Mock */}
                <div className="bg-slate-950 border border-slate-800 rounded-3xl p-8 shadow-glass">
                  <h3 className="text-lg font-semibold text-slate-50 mb-8">Impact Flow</h3>
                  
                  <div className="flex flex-col lg:flex-row items-stretch justify-center gap-8">
                    {/* Origin */}
                    <div className="flex flex-col justify-center items-center">
                      <div className="px-6 py-4 bg-indigo-600/10 border-2 border-indigo-500 rounded-2xl text-center shadow-[0_0_20px_rgba(99,102,241,0.2)]">
                        <FileCode2 size={24} className="text-indigo-400 mx-auto mb-2" />
                        <span className="font-mono text-sm text-indigo-300">{selectedFile}</span>
                      </div>
                    </div>

                    <div className="hidden lg:flex flex-col justify-center items-center">
                      <ArrowRight size={24} className="text-slate-600" />
                    </div>

                    {/* Level 1 */}
                    <div className="flex flex-col gap-4 justify-center">
                      <FlowBox label="api/routers/users.py" type="file" />
                      <FlowBox label="api/routers/auth.py" type="file" />
                      <FlowBox label="services/auth_service.py" type="service" />
                    </div>

                    <div className="hidden lg:flex flex-col justify-center items-center">
                      <ArrowRight size={24} className="text-slate-600" />
                    </div>

                    {/* Level 2 */}
                    <div className="flex flex-col gap-4 justify-center">
                      <FlowBox label="Frontend API Client" type="external" />
                      <FlowBox label="User Microservice" type="external" />
                    </div>
                  </div>
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

function FlowBox({ label, type }) {
  const getStyle = () => {
    switch(type) {
      case 'file': return 'bg-slate-800 border-slate-700 text-slate-300';
      case 'service': return 'bg-amber-900/20 border-amber-500/30 text-amber-300';
      case 'external': return 'bg-rose-900/20 border-rose-500/30 text-rose-300';
      default: return 'bg-slate-800 border-slate-700 text-slate-300';
    }
  };

  return (
    <div className={`px-4 py-3 border rounded-xl font-mono text-sm text-center ${getStyle()}`}>
      {label}
    </div>
  );
}
