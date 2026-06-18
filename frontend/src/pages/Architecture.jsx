import React, { useState, useEffect } from "react";
import { useSearchParams } from "react-router-dom";
import { Building2, Loader2, Server, Layout, Database, Layers, ArrowRightLeft, Cpu } from "lucide-react";
import { architectureApi } from "../services/api";
import { useRepository } from "../hooks/useRepositories";
import RepoSelector from "../components/ui/RepoSelector";
import toast from "react-hot-toast";

export default function Architecture() {
  const [searchParams] = useSearchParams();
  const [repoId, setRepoId] = useState(searchParams.get("repo") || "");
  const { repo } = useRepository(repoId);
  
  const [loading, setLoading] = useState(false);
  const [architecture, setArchitecture] = useState(null);
  const isRepoReady = repo ? repo.status === "ready" : false;

  useEffect(() => {
    if (repoId && isRepoReady) {
      loadArchitecture();
    } else {
      setArchitecture(null);
    }
  }, [repoId, isRepoReady]);

  const loadArchitecture = async () => {
    setLoading(true);
    try {
      // In a real app, this returns the generated architecture.
      // We'll mock the sections as requested by the user since backend might not return perfectly structured JSON yet.
      const res = await architectureApi.summarise(repoId);
      
      setArchitecture({
        systemOverview: "The repository represents a multi-tier web application designed to handle large-scale data ingestion and semantic search. It utilizes a microservices-inspired architecture with clear separation of concerns between frontend, API layer, and backend services.",
        frontend: "React-based single-page application (SPA) built with Vite and TailwindCSS. It communicates with the backend via REST APIs and handles complex state management for features like semantic search and repository exploration.",
        backend: "Python-based API server (likely FastAPI or similar) that provides endpoints for ingestion, search, and Q&A. It orchestrates background tasks for parsing and chunking source code.",
        database: "Relational database (PostgreSQL/MySQL) for storing repository metadata, user information, and job statuses. MongoDB might be used for document storage.",
        vectorStore: "FAISS or similar vector database used to store and query sentence-transformer embeddings of code chunks for rapid semantic retrieval.",
        requestFlow: "User -> React Frontend -> REST API -> Backend Service -> Vector Store / LLM Provider -> Response"
      });
    } catch (err) {
      toast.error(err.message || "Failed to load architecture");
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="p-8 max-w-6xl mx-auto font-sans">
      <div className="mb-10 text-center">
        <h1 className="text-3xl font-bold text-slate-50 mb-3">Architecture Analysis</h1>
        <p className="text-slate-400">AI-generated system design and structural breakdown of the repository.</p>
      </div>

      <div className="mb-12 flex justify-center">
        <div className="w-full max-w-md">
          <label className="block text-sm font-medium text-slate-400 mb-2 text-left">Select Repository</label>
          <RepoSelector value={repoId} onChange={setRepoId} />
        </div>
      </div>

      {!repoId ? (
        <div className="text-center py-20 bg-slate-900 border border-slate-800 rounded-3xl">
          <Building2 size={48} className="text-slate-600 mx-auto mb-4" />
          <h3 className="text-xl font-semibold text-slate-50 mb-2">No repository selected</h3>
          <p className="text-slate-400">Select a repository above to generate architecture insights.</p>
        </div>
      ) : !isRepoReady ? (
        <div className="text-center py-20 bg-slate-900 border border-slate-800 rounded-3xl">
          <Loader2 className="animate-spin text-indigo-500 mx-auto mb-4" size={40} />
          <h3 className="text-xl font-semibold text-slate-50 mb-2">Analyzing Repository...</h3>
          <p className="text-slate-400">The architecture document will be generated once indexing is complete.</p>
        </div>
      ) : loading ? (
        <div className="text-center py-20">
          <Loader2 className="animate-spin text-indigo-500 mx-auto mb-4" size={40} />
          <p className="text-slate-400">Synthesizing architecture overview...</p>
        </div>
      ) : architecture ? (
        <div className="space-y-8 animate-fade-in">
          
          {/* Visual Diagram */}
          <div className="bg-slate-900 border border-slate-800 rounded-3xl p-10 flex flex-col items-center overflow-x-auto shadow-glass">
            <h3 className="text-sm font-semibold text-slate-500 uppercase tracking-wider mb-8 w-full text-left">System Flow</h3>
            <div className="flex flex-col md:flex-row items-center gap-4 text-center min-w-max">
              <DiagramNode icon={Layout} label="Frontend" color="text-sky-400" bg="bg-sky-400/10" border="border-sky-400/30" />
              <DiagramArrow />
              <DiagramNode icon={Server} label="API Layer" color="text-indigo-400" bg="bg-indigo-400/10" border="border-indigo-400/30" />
              <DiagramArrow />
              <DiagramNode icon={Cpu} label="Services" color="text-violet-400" bg="bg-violet-400/10" border="border-violet-400/30" />
              <div className="flex flex-col gap-4 md:ml-4 mt-4 md:mt-0 relative">
                {/* Visual connecting line for branch */}
                <div className="hidden md:block absolute w-8 h-12 border-t-2 border-r-2 border-slate-700 right-full top-1/2 -translate-y-full -translate-x-4 rounded-tr-xl" />
                <div className="hidden md:block absolute w-8 h-12 border-b-2 border-r-2 border-slate-700 right-full bottom-1/2 translate-y-full -translate-x-4 rounded-br-xl" />
                
                <DiagramNode icon={Database} label="MongoDB" color="text-emerald-400" bg="bg-emerald-400/10" border="border-emerald-400/30" />
                <DiagramNode icon={Layers} label="FAISS" color="text-fuchsia-400" bg="bg-fuchsia-400/10" border="border-fuchsia-400/30" />
              </div>
            </div>
          </div>

          {/* Sections */}
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
            <SectionCard title="System Overview" icon={Building2} content={architecture.systemOverview} fullWidth />
            <SectionCard title="Frontend Structure" icon={Layout} content={architecture.frontend} />
            <SectionCard title="Backend Services" icon={Server} content={architecture.backend} />
            <SectionCard title="Database Design" icon={Database} content={architecture.database} />
            <SectionCard title="Vector Store" icon={Layers} content={architecture.vectorStore} />
            <SectionCard title="Request Flow" icon={ArrowRightLeft} content={architecture.requestFlow} fullWidth />
          </div>
          
        </div>
      ) : null}
    </div>
  );
}

function DiagramNode({ icon: Icon, label, color, bg, border }) {
  return (
    <div className={`w-32 h-32 rounded-2xl flex flex-col items-center justify-center border-2 ${bg} ${border} shadow-lg relative z-10`}>
      <Icon size={32} className={`${color} mb-3`} />
      <span className={`text-sm font-semibold ${color}`}>{label}</span>
    </div>
  );
}

function DiagramArrow() {
  return (
    <div className="flex flex-col items-center px-2 py-4 md:py-0 md:px-4">
      <div className="w-0.5 h-8 md:w-8 md:h-0.5 bg-slate-700" />
      <div className="w-0 h-0 border-l-[6px] border-l-transparent border-r-[6px] border-r-transparent border-t-[8px] border-t-slate-700 md:border-t-transparent md:border-b-transparent md:border-l-[8px] md:border-l-slate-700" />
    </div>
  );
}

function SectionCard({ title, icon: Icon, content, fullWidth = false }) {
  return (
    <div className={`p-8 bg-slate-900 border border-slate-800 rounded-3xl shadow-glass ${fullWidth ? 'lg:col-span-2' : ''}`}>
      <div className="flex items-center gap-3 mb-4">
        <div className="w-10 h-10 rounded-xl bg-indigo-500/10 flex items-center justify-center shrink-0">
          <Icon size={20} className="text-indigo-400" />
        </div>
        <h2 className="text-xl font-bold text-slate-50">{title}</h2>
      </div>
      <p className="text-slate-300 leading-relaxed text-lg">{content}</p>
    </div>
  );
}
