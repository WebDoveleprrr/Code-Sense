import React, { useState, useRef, useEffect } from "react"; //useref stores ref or address to a DOM element, useeffect runs when a component loads or state changes
import { useSearchParams } from "react-router-dom";
import { Send, Loader2, Bot, User, FileCode2, Info, ArrowRight } from "lucide-react";
import { qaApi } from "../services/api";
import { useRepository } from "../hooks/useRepositories";
import RepoSelector from "../components/ui/RepoSelector";
import ReactMarkdown from "react-markdown";
import CodeBlock from "../components/ui/CodeBlock";
import toast from "react-hot-toast";

export default function QAChat() {
  const [searchParams] = useSearchParams();
  const [repoId, setRepoId] = useState(searchParams.get("repo") || "");
  const { repo } = useRepository(repoId);
  
  const [messages, setMessages] = useState([]); //store chat history
  const [input, setInput] = useState(""); //question asked
  const [loading, setLoading] = useState(false); //shows spinner
  const [sources, setSources] = useState([]); //stores retirved chunks
  const [selectedSource, setSelectedSource] = useState(null); //tracks which source file user clicked
  
  const [strictMode, setStrictMode] = useState(false);
  
  const messagesEndRef = useRef(null);
  const inputRef = useRef(null);
  const abortControllerRef = useRef(null);
  const isRepoReady = repo ? repo.status === "ready" : false;
  
  const groupedSources = React.useMemo(() => {
    if (!sources || sources.length === 0) return [];
    
    const groups = {};
    sources.forEach(src => {
      const path = src.file_path;
      if (!groups[path]) {
        groups[path] = {
          file_path: path,
          language: src.language || 'text',
          chunks: [],
          maxScore: 0
        };
      }
      groups[path].chunks.push(src);
      const score = src.final_score || src.composite_score || src.score || 0;
      if (score > groups[path].maxScore) groups[path].maxScore = score;
    });

    return Object.values(groups).map(group => {
      group.chunks.sort((a, b) => a.start_line - b.start_line);
      const ranges = group.chunks.map(c => `${c.start_line}-${c.end_line}`).join(', ');
      group.lineRanges = ranges;
      let relevance = "Low Relevance";
      if (group.maxScore > 0.8) relevance = "Highly Relevant";
      else if (group.maxScore > 0.5) relevance = "Relevant";
      else if (group.maxScore > 0.3) relevance = "Moderately Relevant";
      group.relevance = relevance;
      return group;
    });
  }, [sources]);
  
  //auto scroll when new message arrives
  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  };

  useEffect(() => {
    scrollToBottom();
  }, [messages, loading]);

  useEffect(() => {
    inputRef.current?.focus();
  }, []);
  //main function called when press enter or click send
  const handleAsk = async (text) => {
    const query = text || input; //dfault uestion or asked question
    if (!query.trim() || !repoId || !isRepoReady) return;

    if (abortControllerRef.current) {
      abortControllerRef.current.abort();
    }
    const controller = new AbortController();
    abortControllerRef.current = controller;

    const userMsg = { role: "user", content: query.trim() }; //create user message
    setMessages((prev) => [...prev, userMsg]); //append to chat
    setInput("");
    setLoading(true);
    //ask AI
    try {
      const res = await qaApi.ask({
        repo_id: repoId,
        question: query.trim(),
        history: messages.map(m => ({ role: m.role, content: m.content })),
        strict_mode: strictMode
      }, { signal: controller.signal });
      //store answer from AI
      setMessages((prev) => [...prev, { 
        role: "assistant", 
        content: res.answer, 
        confidence: res.confidence,
        sources: res.sources || []
      }]);
    } catch (err) { //error handling
      if (err.name === 'CanceledError' || err.message === 'canceled' || err.code === 'ERR_CANCELED') {
        return;
      }
      toast.error(err.message || "Failed to answer question");
      setMessages((prev) => [...prev, { role: "assistant", content: "Sorry, I encountered an error while processing your request." }]);
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
  //starter or example prompts
  const suggestions = [
    "Explain the architecture",
    "Show authentication flow",
    "How does ingestion work?",
    "Which files are most important?"
  ];

  return (
    <div className="flex h-[calc(100vh-4rem)] bg-slate-950 font-sans">
      {/* Main Chat Area */}
      <div className="flex-1 flex flex-col min-w-0 border-r border-slate-800">
        <div className="h-16 px-6 border-b border-slate-800 flex items-center justify-between shrink-0 bg-slate-950/50 backdrop-blur-md">
          <h2 className="text-lg font-semibold text-slate-50">Repository Q&A</h2>
          <div className="flex items-center gap-6">
            <div className="flex items-center gap-2">
              <input 
                type="checkbox" 
                id="strict_mode" 
                checked={strictMode} 
                onChange={(e) => setStrictMode(e.target.checked)}
                className="w-4 h-4 rounded border-slate-700 bg-slate-900 text-indigo-600 focus:ring-indigo-600"
              />
              <label htmlFor="strict_mode" className="text-xs text-slate-400 select-none cursor-pointer">Strict Mode (No Hallucinations)</label>
            </div>
            <div className="w-64">
              <RepoSelector value={repoId} onChange={setRepoId} />
            </div>
          </div>
        </div>

        <div className="flex-1 overflow-y-auto p-6 scrollbar-thin scrollbar-thumb-slate-700">
          {messages.length === 0 ? (
            <div className="h-full flex flex-col items-center justify-center max-w-2xl mx-auto text-center animate-fade-in">
              <div className="w-16 h-16 bg-indigo-500/10 rounded-2xl flex items-center justify-center mb-6">
                <Bot size={32} className="text-indigo-400" />
              </div>
              <h1 className="text-3xl font-bold text-slate-50 mb-4">Ask anything about this repository</h1>
              <p className="text-slate-400 mb-10">
                I can explain architecture, trace flows, and help you understand complex logic.
              </p>
              
              <div className="grid grid-cols-1 sm:grid-cols-2 gap-4 w-full">
                {suggestions.map((suggestion) => (
                  <button
                    key={suggestion}
                    disabled={!isRepoReady}
                    onClick={() => handleAsk(suggestion)}
                    className="p-4 bg-slate-900 border border-slate-800 rounded-xl hover:border-indigo-500/50 hover:bg-slate-800/50 text-left transition-all group disabled:opacity-50 disabled:cursor-not-allowed"
                  >
                    <p className="text-sm font-medium text-slate-300 group-hover:text-indigo-400 mb-1">{suggestion}</p>
                    <p className="text-xs text-slate-500">Generate an AI response</p>
                  </button>
                ))}
              </div>
            </div>
          ) : (
            <div className="max-w-3xl mx-auto space-y-6 pb-6">
              {messages.map((msg, i) => (
                <div key={i} className={`flex gap-4 ${msg.role === 'user' ? 'justify-end' : 'justify-start'}`}>
                  {msg.role === 'assistant' && (
                    <div className="w-8 h-8 rounded-lg bg-indigo-600 flex items-center justify-center shrink-0">
                      <Bot size={16} className="text-white" />
                    </div>
                  )}
                  
                  <div className={`max-w-[85%] rounded-2xl p-5 ${
                    msg.role === 'user' 
                      ? 'bg-indigo-600 text-white' 
                      : 'bg-slate-900 border border-slate-800 text-slate-200 shadow-glass'
                  }`}>
                    {msg.role === 'user' ? (
                      <p className="text-sm">{msg.content}</p>
                    ) : (
                      <div className="prose prose-invert prose-sm max-w-none prose-pre:bg-slate-950 prose-pre:border prose-pre:border-slate-800">
                        {msg.confidence !== undefined && (
                          <div className="mb-4 pb-2 border-b border-slate-800 flex items-center gap-2 text-xs">
                            <span className="text-slate-400 font-semibold uppercase tracking-wider">Confidence Score:</span>
                            <span className={`font-mono px-2 py-0.5 rounded-full ${msg.confidence > 80 ? 'bg-emerald-500/10 text-emerald-400 border border-emerald-500/20' : msg.confidence > 50 ? 'bg-indigo-500/10 text-indigo-400 border border-indigo-500/20' : 'bg-amber-500/10 text-amber-400 border border-amber-500/20'}`}>
                              {msg.confidence}%
                            </span>
                          </div>
                        )}
                        <ReactMarkdown>{msg.content}</ReactMarkdown>
                        {msg.sources && msg.sources.length > 0 && (
                          <div className="mt-4 pt-4 border-t border-slate-700/50">
                            <div className="flex items-center justify-between mb-2">
                              <div className="flex items-center gap-2 text-xs font-semibold text-slate-400 uppercase tracking-wider">
                                <FileCode2 size={14} /> Sources
                              </div>
                              <div className="flex items-center gap-2">
                                <button 
                                  onClick={() => {
                                    navigator.clipboard.writeText(msg.content);
                                    toast.success("Answer copied to clipboard!");
                                  }}
                                  className="text-xs text-slate-500 hover:text-indigo-400 transition-colors"
                                >
                                  Copy Answer
                                </button>
                              </div>
                            </div>
                            <div className="flex flex-col gap-2">
                              {msg.sources.map((source, idx) => (
                                <details key={idx} className="group border border-slate-700/50 rounded-xl overflow-hidden bg-slate-800/20">
                                  <summary className="flex items-center justify-between p-3 cursor-pointer hover:bg-slate-800/40 transition-colors">
                                    <div className="flex items-center gap-2">
                                      <FileCode2 size={14} className="text-indigo-400" />
                                      <span className="text-sm font-medium text-slate-200">
                                        {source.file_path.split('/').pop()}
                                      </span>
                                      <span className="text-xs text-slate-500">
                                        Lines {source.start_line}-{source.end_line}
                                      </span>
                                    </div>
                                    <span className="text-xs text-slate-500 group-open:hidden">View Snippet</span>
                                    <span className="text-xs text-slate-500 hidden group-open:block">Hide Snippet</span>
                                  </summary>
                                  <div className="p-4 bg-slate-900 border-t border-slate-700/50 relative">
                                    <div className="absolute top-2 right-2 flex gap-2">
                                      <button 
                                        onClick={(e) => {
                                          e.preventDefault();
                                          navigator.clipboard.writeText(source.content || source.snippet || "");
                                          toast.success("Snippet copied!");
                                        }}
                                        className="px-2 py-1 bg-slate-800 hover:bg-slate-700 text-xs text-slate-300 rounded border border-slate-600 transition-colors"
                                      >
                                        Copy Code
                                      </button>
                                      <button 
                                        onClick={(e) => {
                                          e.preventDefault();
                                          navigator.clipboard.writeText(source.file_path);
                                          toast.success("Path copied!");
                                        }}
                                        className="px-2 py-1 bg-slate-800 hover:bg-slate-700 text-xs text-slate-300 rounded border border-slate-600 transition-colors"
                                      >
                                        Copy Path
                                      </button>
                                    </div>
                                    <pre className="text-xs font-mono text-slate-300 overflow-x-auto whitespace-pre-wrap mt-6">
                                      {source.content || source.snippet || "Snippet not available"}
                                    </pre>
                                  </div>
                                </details>
                              ))}
                            </div>
                          </div>
                        )}
                      </div>
                    )}
                  </div>

                  {msg.role === 'user' && (
                    <div className="w-8 h-8 rounded-lg bg-slate-700 flex items-center justify-center shrink-0">
                      <User size={16} className="text-slate-300" />
                    </div>
                  )}
                </div>
              ))}
              
              {loading && (
                <div className="flex gap-4 justify-start">
                  <div className="w-8 h-8 rounded-lg bg-indigo-600 flex items-center justify-center shrink-0">
                    <Loader2 size={16} className="text-white animate-spin" />
                  </div>
                  <div className="bg-slate-900 border border-slate-800 rounded-2xl p-5 shadow-glass flex items-center gap-2 text-slate-400">
                    <span className="w-2 h-2 rounded-full bg-slate-500 animate-pulse" />
                    <span className="w-2 h-2 rounded-full bg-slate-500 animate-pulse delay-75" />
                    <span className="w-2 h-2 rounded-full bg-slate-500 animate-pulse delay-150" />
                  </div>
                </div>
              )}
              <div ref={messagesEndRef} />
            </div>
          )}
        </div>

        {/* Input Area */}
        <div className="p-4 border-t border-slate-800 bg-slate-950">
          <div className="max-w-3xl mx-auto relative">
            <textarea
              ref={inputRef}
              value={input}
              onChange={(e) => setInput(e.target.value)}
              onKeyDown={(e) => {
                if (e.key === "Enter" && !e.shiftKey) {
                  e.preventDefault();
                  handleAsk();
                }
              }}
              disabled={!isRepoReady || loading}
              placeholder={isRepoReady ? "Message CodeSense..." : "Select a ready repository to start..."}
              className="w-full bg-slate-900 border border-slate-700 rounded-2xl pl-4 pr-14 py-4 text-sm text-slate-50 placeholder:text-slate-500 focus:outline-none focus:border-indigo-500 focus:ring-1 focus:ring-indigo-500 resize-none min-h-[56px] max-h-48 scrollbar-none disabled:opacity-50"
              rows={1}
            />
            <button
              onClick={() => handleAsk()}
              disabled={!input.trim() || !isRepoReady || loading}
              className="absolute right-2 top-1/2 -translate-y-1/2 w-10 h-10 rounded-xl bg-indigo-600 hover:bg-indigo-700 disabled:bg-slate-800 disabled:text-slate-500 text-white flex items-center justify-center transition-colors"
            >
              <Send size={16} />
            </button>
          </div>
          <div className="text-center mt-2">
            <span className="text-[10px] text-slate-500 uppercase tracking-wider">CodeSense AI can make mistakes. Check important information.</span>
          </div>
        </div>
      </div>

    </div>
  );
}
