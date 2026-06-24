import React, { useState, useEffect } from "react";
import { useSearchParams } from "react-router-dom"; //Read URL for github repo
import { Zap, Loader2, FileCode2, Play, GitMerge, AlertTriangle, ArrowRight, Layers } from "lucide-react";
import { explainApi } from "../services/api"; //bridge to backend
import { useRepository } from "../hooks/useRepositories";
import RepoSelector from "../components/ui/RepoSelector"; //choose repository context
import toast from "react-hot-toast";

export default function ExplainCode() {
  const [searchParams] = useSearchParams();
  const [repoId, setRepoId] = useState(searchParams.get("repo") || "");
  const { repo } = useRepository(repoId); //get repository status
  
  const [code, setCode] = useState(""); //Stores pasted code
  const [loading, setLoading] = useState(false);
  const [explanation, setExplanation] = useState(null); //Stores AI result(initially null)
  const [activeTab, setActiveTab] = useState("summary"); // summary, detailed, complexity
  
  const isRepoReady = repo ? repo.status === "ready" : false; //Prevent explanation before indexing

  //main function(send code to backend and receive explanation)
  const handleExplain = async () => {
    if (!code.trim() || !repoId || !isRepoReady) return; //Prevent invalid requests.
    
    setLoading(true);
    setExplanation(null); //clear old explanation
    
    try { //actual backend call
      const res = await explainApi.explain({
        repo_id: repoId,
        code: code.trim(),
      });
      const formatArray = (arr) => Array.isArray(arr) && arr.length > 0 ? arr.join(", ") : "None";
      const data = res.explanation || {};
      
      setExplanation({
        summary: data.summary || "No summary available.",
        detailed: data.detailed || "No detailed breakdown available.",
        complexity: data.complexity || "Unknown complexity.",
        purpose: data.purpose || "Not specified.",
        inputs: formatArray(data.inputs),
        outputs: formatArray(data.outputs),
        dependencies: formatArray(data.dependencies),
        improvements: formatArray(data.improvements)
      });
    } catch (err) {
      toast.error(err.message || "Failed to explain code");
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="flex flex-col lg:flex-row h-[calc(100vh-4rem)] bg-slate-950 font-sans">
      
      {/* Left Panel - Code Input */}
      <div className="w-full lg:w-1/2 flex flex-col border-r border-slate-800 bg-slate-950">
        <div className="p-6 border-b border-slate-800">
          <h2 className="text-xl font-bold text-slate-50 mb-2">Explain Code</h2>
          <p className="text-sm text-slate-400 mb-6">Paste any snippet from your repository to get an AI-powered breakdown of its purpose and logic.</p>
          
          <label className="block text-sm font-medium text-slate-400 mb-2">Repository Context</label>
          <RepoSelector value={repoId} onChange={setRepoId} filterStatus={null} />
        </div>
        
        <div className="flex-1 p-6 flex flex-col relative">
          <label className="block text-sm font-medium text-slate-400 mb-2 flex items-center justify-between">
            Code Snippet
            <button 
              onClick={() => setCode("def example():\n    pass")}
              className="text-xs text-indigo-400 hover:underline"
            >
              Insert example
            </button>
          </label>
          <div className="flex-1 border border-slate-700 rounded-2xl overflow-hidden focus-within:border-indigo-500 focus-within:ring-1 focus-within:ring-indigo-500 transition-all bg-slate-900 shadow-glass">
            <textarea
              value={code}
              onChange={(e) => setCode(e.target.value)}
              placeholder="Paste code here..."
              disabled={!isRepoReady || loading}
              className="w-full h-full bg-transparent text-slate-200 font-mono text-sm p-4 resize-none outline-none disabled:opacity-50"
            />
          </div>
          
          <div className="mt-6">
            <button
              onClick={handleExplain}
              disabled={!code.trim() || !isRepoReady || loading}
              className="w-full py-4 bg-indigo-600 hover:bg-indigo-700 disabled:bg-slate-800 disabled:text-slate-500 text-white rounded-xl font-medium transition-all shadow-glow flex items-center justify-center gap-2"
            >
              {loading ? (
                <><Loader2 size={18} className="animate-spin" /> Analyzing Code...</>
              ) : (
                <><Zap size={18} /> Generate Explanation</>
              )}
            </button>
          </div>
        </div>
      </div>

      {/* Right Panel - Results */}
      <div className="w-full lg:w-1/2 flex flex-col bg-slate-900">
        {!explanation && !loading ? (
          <div className="flex-1 flex flex-col items-center justify-center p-12 text-center">
            <div className="w-20 h-20 bg-slate-800 rounded-3xl flex items-center justify-center mb-6 shadow-glass">
              <FileCode2 size={32} className="text-slate-500" />
            </div>
            <h3 className="text-2xl font-bold text-slate-50 mb-3">AI Code Analysis</h3>
            <p className="text-slate-400 max-w-sm">
              Paste code and hit generate to see a breakdown of its purpose, inputs, dependencies, and complexity.
            </p>
          </div>
        ) : loading ? (
          <div className="flex-1 flex flex-col items-center justify-center">
            <Loader2 size={40} className="text-indigo-500 animate-spin mb-4" />
            <p className="text-slate-400">Processing analysis...</p>
          </div>
        ) : (
          <div className="flex-1 flex flex-col overflow-hidden animate-fade-in">
            
            {/* Tabs */}
            <div className="flex items-center gap-2 px-6 pt-6 border-b border-slate-800 shrink-0">
              {[
                { id: "summary", label: "Summary", icon: Layers },
                { id: "detailed", label: "Detailed Explanation", icon: FileCode2 },
                { id: "complexity", label: "Complexity Analysis", icon: Zap }
              ].map(t => (
                <button
                  key={t.id}
                  onClick={() => setActiveTab(t.id)}
                  className={`px-4 py-3 text-sm font-medium border-b-2 transition-colors flex items-center gap-2 ${
                    activeTab === t.id 
                      ? "border-indigo-500 text-indigo-400" 
                      : "border-transparent text-slate-400 hover:text-slate-200"
                  }`}
                >
                  <t.icon size={16} /> {t.label}
                </button>
              ))}
            </div>

            <div className="flex-1 overflow-y-auto p-6 scrollbar-thin scrollbar-thumb-slate-700">
              
              {/* Tab Content */}
              <div className="mb-8">
                {activeTab === 'summary' && (
                  <div className="prose prose-invert prose-sm max-w-none text-slate-300">
                    <p className="text-base leading-relaxed">{explanation.summary}</p>
                  </div>
                )}
                {activeTab === 'detailed' && (
                  <div className="prose prose-invert prose-sm max-w-none text-slate-300">
                    <p className="text-base leading-relaxed">{explanation.detailed}</p>
                  </div>
                )}
                {activeTab === 'complexity' && (
                  <div className="prose prose-invert prose-sm max-w-none text-slate-300">
                    <pre className="bg-slate-950 p-4 rounded-xl border border-slate-800">{explanation.complexity}</pre>
                  </div>
                )}
              </div>

              {/* Information Cards Grid */}
              <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                <InfoCard icon={Play} title="Purpose" content={explanation.purpose} />
                <InfoCard icon={ArrowRight} title="Inputs" content={explanation.inputs} />
                <InfoCard icon={ArrowRight} title="Outputs" content={explanation.outputs} />
                <InfoCard icon={GitMerge} title="Dependencies" content={explanation.dependencies} />
                <InfoCard icon={AlertTriangle} title="Potential Improvements" content={explanation.improvements} className="sm:col-span-2 bg-indigo-500/5 border-indigo-500/20" />
              </div>
              
            </div>
          </div>
        )}
      </div>
    </div>
  );
}

//Reusable component
function InfoCard({ icon: Icon, title, content, className = "" }) {
  return (
    <div className={`p-5 rounded-2xl bg-slate-950 border border-slate-800 shadow-glass ${className}`}>
      <div className="flex items-center gap-2 mb-3">
        <Icon size={16} className="text-indigo-400" />
        <h4 className="text-sm font-semibold text-slate-200">{title}</h4>
      </div>
      <p className="text-sm text-slate-400 leading-relaxed">{content}</p>
    </div>
  );
}
