//How is this entire repository designed
import React, { useState, useEffect } from "react";
import { useSearchParams } from "react-router-dom";
import { Building2, Loader2 } from "lucide-react";
import ReactMarkdown from "react-markdown";
import mermaid from "mermaid";
import RepoSelector from "../components/ui/RepoSelector";
import toast from "react-hot-toast";
import { useRepository } from "../hooks/useRepositories";
import { architectureApi } from "../services/api";

export default function Architecture() {
  const [searchParams] = useSearchParams();
  const [repoId, setRepoId] = useState(searchParams.get("repo") || "");
  const { repo } = useRepository(repoId);
  
  const [loading, setLoading] = useState(false);
  const [architecture, setArchitecture] = useState(null);
  const [error, setError] = useState(null);
  const isRepoReady = repo ? repo.status === "ready" : false;
  const abortControllerRef = React.useRef(null);

  useEffect(() => {
    if (repoId && isRepoReady) {
      loadArchitecture();
    } else {
      setArchitecture(null); //initial explanation is null
      setError(null);
    }
  }, [repoId, isRepoReady]);

  const loadArchitecture = async (forceRegenerate = false) => {
    if (abortControllerRef.current) {
      abortControllerRef.current.abort();
    }
    const controller = new AbortController();
    abortControllerRef.current = controller;

    setLoading(true);
    setError(null);
    try {
      const res = await architectureApi.summarise(repoId, undefined, forceRegenerate, { signal: controller.signal });
      
      setArchitecture({
        summary: res.summary || "No architecture summary available.",
        grounding: res.grounding || null
      });
    } catch (err) {
      if (err.name === 'CanceledError' || err.message === 'canceled' || err.code === 'ERR_CANCELED') {
        return;
      }
      setError("Unable to generate architecture. Please try again.");
      toast.error(err.message || "Failed to load architecture");
    } finally {
      if (abortControllerRef.current === controller) {
        setLoading(false);
      }
    }
  };

  useEffect(() => {
    return () => {
      if (abortControllerRef.current) {
        abortControllerRef.current.abort();
      }
    };
  }, []);

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
      ) : error ? (
        <div className="text-center py-20 bg-slate-900 border border-slate-800 rounded-3xl shadow-glass">
          <Building2 size={48} className="text-rose-500 mx-auto mb-4 opacity-80" />
          <h3 className="text-xl font-semibold text-slate-50 mb-2">Analysis Failed</h3>
          <p className="text-slate-400 mb-6">{error}</p>
          <button 
            onClick={() => loadArchitecture(true)}
            className="px-6 py-2.5 bg-indigo-600 hover:bg-indigo-700 text-white rounded-xl transition-colors font-medium shadow-glow"
          >
            Retry Analysis
          </button>
        </div>
      ) : architecture ? (
        <div className="space-y-6 animate-fade-in pb-12">
          {architecture.grounding && (
            <div className="bg-indigo-500/10 border border-indigo-500/20 rounded-2xl p-4 flex items-center justify-between shadow-glass">
              <div className="flex items-center gap-3">
                <div className="w-10 h-10 rounded-full bg-indigo-500/20 flex items-center justify-center shrink-0">
                  <Building2 size={20} className="text-indigo-400" />
                </div>
                <div>
                  <h4 className="text-sm font-semibold text-indigo-300">Evidence-Based Grounding</h4>
                  <p className="text-xs text-indigo-400/80">Architecture synthesized strictly from retrieved context.</p>
                </div>
              </div>
              <div className="flex items-center gap-6 pr-4">
                <div className="text-right">
                  <span className="block text-xl font-bold text-slate-100">{architecture.grounding.files_retrieved}</span>
                  <span className="text-xs text-slate-500 uppercase tracking-wider font-semibold">Files Retrieved</span>
                </div>
                <div className="w-px h-8 bg-slate-700/50"></div>
                <div className="text-right">
                  <span className="block text-xl font-bold text-slate-100">{architecture.grounding.chunks_retrieved}</span>
                  <span className="text-xs text-slate-500 uppercase tracking-wider font-semibold">Chunks Retrieved</span>
                </div>
                <div className="w-px h-8 bg-slate-700/50"></div>
                <div className="text-right">
                  <span className={`block text-xl font-bold ${architecture.grounding.confidence === 'High' ? 'text-emerald-400' : architecture.grounding.confidence === 'Medium' ? 'text-amber-400' : 'text-rose-400'}`}>
                    {architecture.grounding.confidence}
                  </span>
                  <span className="text-xs text-slate-500 uppercase tracking-wider font-semibold">Confidence</span>
                </div>
              </div>
            </div>
          )}

          {parseSections(architecture.summary).map((section, idx) => (
            <div key={idx} className="bg-slate-900 border border-slate-800 rounded-3xl p-8 shadow-glass">
              {section.title !== "Overview" && (
                <h2 className="text-xl font-bold text-slate-50 mb-6 flex items-center gap-2">
                  <span className="text-indigo-400 font-mono text-sm">{idx + 1 < 10 ? `0${idx + 1}` : idx + 1}</span>
                  {section.title.replace(/^\d+\.\s*/, '')}
                </h2>
              )}
              <div className="text-slate-300 leading-relaxed text-[15px] overflow-x-auto prose prose-invert max-w-none prose-p:leading-relaxed prose-pre:bg-slate-950 prose-pre:border prose-pre:border-slate-800 prose-headings:text-slate-100 prose-a:text-indigo-400">
                <ReactMarkdown
                  components={{
                    a: ({node, ...props}) => (
                      <a 
                        {...props} 
                        className="text-indigo-400 hover:text-indigo-300 underline decoration-indigo-500/30 decoration-dashed underline-offset-4 hover:decoration-indigo-400 transition-colors cursor-pointer"
                        title={props.href || props.children}
                      />
                    ),
                    code({ node, inline, className, children, ...props }) {
                      const match = /language-(\w+)/.exec(className || "");
                      if (!inline && match && match[1] === "mermaid") {
                        return <MermaidChart text={String(children).replace(/\n$/, "")} />;
                      }
                      return !inline && match ? (
                        <code className={className} {...props}>
                          {children}
                        </code>
                      ) : (
                        <code className="bg-slate-800 px-1.5 py-0.5 rounded-md text-sm text-indigo-300 font-mono" {...props}>
                          {children}
                        </code>
                      );
                    },
                  }}
                >
                  {section.content}
                </ReactMarkdown>
              </div>
            </div>
          ))}
        </div>
      ) : null}
    </div>
  );
}

function parseSections(markdown) {
  const parts = markdown.split(/(?=^### )/m);
  return parts.map(part => {
    const match = part.match(/^### (.+)\n([\s\S]*)$/);
    if (match) {
      return { title: match[1].trim(), content: match[2].trim() };
    }
    return { title: "Overview", content: part.trim() };
  }).filter(s => s.content.length > 0);
}

function MermaidChart({ text }) {
  const containerRef = React.useRef(null);
  const [error, setError] = useState(false);

  React.useEffect(() => {
    if (containerRef.current && text) {
      try {
        mermaid.initialize({ startOnLoad: true, theme: "dark" });
        mermaid.render(`mermaid-${Math.random().toString(36).substring(7)}`, text).then(({ svg }) => {
          if (containerRef.current) {
            containerRef.current.innerHTML = svg;
          }
        }).catch(err => {
          console.error("Mermaid render failed:", err);
          setError(true);
        });
      } catch (err) {
        console.error("Mermaid render failed:", err);
        setError(true);
      }
    }
  }, [text]);

  if (error) {
    return (
      <div className="flex justify-center my-8 w-full p-6 bg-slate-950 border border-slate-800 border-dashed rounded-xl text-slate-500 italic text-sm">
        No architecture diagram could be generated.
      </div>
    );
  }

  return <div ref={containerRef} className="flex justify-center my-8 overflow-x-auto w-full p-6 bg-slate-950 border border-slate-800 rounded-2xl shadow-inner" />;
}
