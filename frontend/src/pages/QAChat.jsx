import React, { useState, useRef, useEffect } from "react";
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
  
  const [messages, setMessages] = useState([]);
  const [input, setInput] = useState("");
  const [loading, setLoading] = useState(false);
  const [sources, setSources] = useState([]);
  const [selectedSource, setSelectedSource] = useState(null);
  
  const messagesEndRef = useRef(null);
  const inputRef = useRef(null);

  const isRepoReady = repo ? repo.status === "ready" : false;

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  };

  useEffect(() => {
    scrollToBottom();
  }, [messages, loading]);

  useEffect(() => {
    inputRef.current?.focus();
  }, []);

  const handleAsk = async (text) => {
    const query = text || input;
    if (!query.trim() || !repoId || !isRepoReady) return;

    const userMsg = { role: "user", content: query.trim() };
    setMessages((prev) => [...prev, userMsg]);
    setInput("");
    setLoading(true);

    try {
      const res = await qaApi.ask({
        repo_id: repoId,
        question: query.trim(),
        history: messages.map(m => ({ role: m.role, content: m.content }))
      });
      
      setMessages((prev) => [...prev, { role: "assistant", content: res.answer }]);
      if (res.sources && res.sources.length > 0) {
        setSources(res.sources);
      }
    } catch (err) {
      toast.error(err.message || "Failed to answer question");
      setMessages((prev) => [...prev, { role: "assistant", content: "Sorry, I encountered an error while processing your request." }]);
    } finally {
      setLoading(false);
    }
  };

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
          <div className="w-64">
            <RepoSelector value={repoId} onChange={setRepoId} />
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
                        <ReactMarkdown>{msg.content}</ReactMarkdown>
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

      {/* Right Sidebar - Sources Panel */}
      <div className="w-80 bg-slate-950 flex flex-col shrink-0 hidden lg:flex">
        <div className="h-16 px-4 border-b border-slate-800 flex items-center shrink-0">
          <h3 className="text-sm font-semibold text-slate-300 flex items-center gap-2">
            <Info size={16} className="text-indigo-400" /> Sources Panel
          </h3>
        </div>

        <div className="flex-1 overflow-y-auto p-4 scrollbar-none space-y-4">
          {sources.length === 0 ? (
            <div className="text-center py-10">
              <FileCode2 size={32} className="text-slate-700 mx-auto mb-3" />
              <p className="text-sm text-slate-500">Referenced files will appear here when you ask questions.</p>
            </div>
          ) : (
            <>
              <h4 className="text-xs font-semibold text-slate-500 uppercase tracking-wider mb-2">Files Referenced</h4>
              <div className="space-y-2">
                {sources.map((src, idx) => (
                  <button
                    key={idx}
                    onClick={() => setSelectedSource(selectedSource === idx ? null : idx)}
                    className={`w-full text-left p-3 rounded-xl border transition-all ${
                      selectedSource === idx 
                        ? 'bg-indigo-500/10 border-indigo-500/30' 
                        : 'bg-slate-900 border-slate-800 hover:border-slate-700'
                    }`}
                  >
                    <div className="flex items-center justify-between mb-1">
                      <span className="text-sm font-medium text-slate-200 truncate pr-2">
                        {src.file_path.split('/').pop()}
                      </span>
                      <ArrowRight size={14} className={`text-slate-500 transition-transform ${selectedSource === idx ? 'rotate-90 text-indigo-400' : ''}`} />
                    </div>
                    <p className="text-xs text-slate-500 truncate">{src.file_path}</p>
                  </button>
                ))}
              </div>
            </>
          )}

          {/* Source Preview */}
          {selectedSource !== null && sources[selectedSource] && (
            <div className="mt-6 border-t border-slate-800 pt-6 animate-fade-in">
              <h4 className="text-xs font-semibold text-slate-500 uppercase tracking-wider mb-3">Code Preview</h4>
              <div className="bg-slate-900 border border-slate-800 rounded-xl overflow-hidden">
                <div className="px-3 py-2 border-b border-slate-800 bg-slate-950">
                  <span className="text-xs text-slate-400 font-mono">Lines {sources[selectedSource].start_line}-{sources[selectedSource].end_line}</span>
                </div>
                <div className="max-h-64 overflow-y-auto scrollbar-thin scrollbar-thumb-slate-700">
                  <CodeBlock
                    code={sources[selectedSource].content}
                    language={sources[selectedSource].language || "text"}
                    startLine={sources[selectedSource].start_line}
                    compact
                  />
                </div>
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
