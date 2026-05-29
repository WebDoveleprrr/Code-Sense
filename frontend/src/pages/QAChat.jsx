// src/pages/QAChat.jsx
import React, { useRef, useEffect, useState } from "react";
import { useSearchParams } from "react-router-dom";
import {
  MessageSquare, Send, Trash2, User, Cpu,
  ChevronDown, FileCode2, Clock, Loader2
} from "lucide-react";
import { useQA } from "../hooks/useQA";
import { Card, Button, SectionHeader, EmptyState, Badge } from "../components/ui";
import RepoSelector from "../components/ui/RepoSelector";
import CodeBlock from "../components/ui/CodeBlock";
import { formatMs, timeAgo } from "../utils/helpers";

const EXAMPLE_QUESTIONS = [
  "How does the authentication flow work?",
  "What are the main entry points of this application?",
  "How are database connections managed?",
  "Explain the error handling strategy",
  "What design patterns are used?",
  "How is the embedding pipeline structured?",
];

function SourceChip({ source }) {
  return (
    <div className="inline-flex items-center gap-1.5 bg-ink-800 border border-ink-600 rounded-md px-2 py-1 text-xs font-mono text-frost-dim">
      <FileCode2 size={10} className="text-plasma-light" />
      <span className="truncate max-w-[200px]">{source.file_path}</span>
      {source.start_line && (
        <span className="text-ink-500">L{source.start_line}</span>
      )}
    </div>
  );
}

function Message({ msg }) {
  const isUser = msg.role === "user";
  const [showSources, setShowSources] = useState(false);

  return (
    <div
      className={`flex gap-3 animate-slide-up ${
        isUser ? "flex-row-reverse" : "flex-row"
      }`}
    >
      {/* Avatar */}
      <div
        className={`w-8 h-8 rounded-lg flex items-center justify-center flex-shrink-0 mt-0.5 ${
          isUser
            ? "bg-acid/10 border border-acid/20 text-acid"
            : msg.isError
            ? "bg-danger/10 border border-danger/20 text-danger"
            : "bg-plasma-muted border border-plasma/20 text-plasma-light"
        }`}
      >
        {isUser ? <User size={14} /> : <Cpu size={14} />}
      </div>

      {/* Bubble */}
      <div className={`flex-1 max-w-[80%] ${isUser ? "items-end" : "items-start"} flex flex-col gap-1`}>
        <div
          className={`rounded-xl px-4 py-3 text-sm font-body leading-relaxed ${
            isUser
              ? "bg-acid/10 border border-acid/10 text-frost"
              : msg.isError
              ? "bg-danger/5 border border-danger/20 text-danger"
              : "glass border border-ink-600 text-frost"
          }`}
        >
          {/* Render answer with basic markdown-like code detection */}
          {msg.content.split(/(```[\s\S]*?```)/g).map((part, i) => {
            if (part.startsWith("```")) {
              const lines = part.replace(/^```\w*\n?/, "").replace(/```$/, "");
              return (
                <div key={i} className="my-2">
                  <CodeBlock code={lines} language="python" compact showCopy />
                </div>
              );
            }
            return (
              <span key={i} className="whitespace-pre-wrap">
                {part}
              </span>
            );
          })}
        </div>

        {/* Sources */}
        {msg.sources?.length > 0 && (
          <div className="w-full">
            <button
              onClick={() => setShowSources(!showSources)}
              className="flex items-center gap-1 text-xs font-mono text-frost-dim hover:text-acid transition-colors"
            >
              <FileCode2 size={11} />
              {msg.sources.length} source{msg.sources.length !== 1 ? "s" : ""}
              <ChevronDown
                size={11}
                className={`transition-transform ${showSources ? "rotate-180" : ""}`}
              />
            </button>
            {showSources && (
              <div className="flex flex-wrap gap-1.5 mt-2 animate-slide-up">
                {msg.sources.map((src, i) => (
                  <SourceChip key={i} source={src} />
                ))}
              </div>
            )}
          </div>
        )}

        {/* Meta */}
        <div className="flex items-center gap-3 text-xs font-mono text-ink-500">
          <span>{new Date(msg.ts).toLocaleTimeString()}</span>
          {msg.latency_ms && (
            <span className="flex items-center gap-1">
              <Clock size={9} />
              {formatMs(msg.latency_ms)}
            </span>
          )}
          {msg.is_fallback && (
            <Badge variant="warning" className="ml-auto bg-warning-muted text-warning border-warning/20">
              Fallback Extractive Mode
            </Badge>
          )}
        </div>
      </div>
    </div>
  );
}

export default function QAChat() {
  const [searchParams] = useSearchParams();
  const [repoId, setRepoId] = useState(searchParams.get("repo") || "");
  const [input, setInput] = useState("");
  const bottomRef = useRef(null);
  const inputRef = useRef(null);

  const { messages, loading, error, ask, clearHistory } = useQA(repoId);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages, loading]);

  const handleSend = () => {
    if (!input.trim() || !repoId || loading) return;
    ask(input.trim());
    setInput("");
  };

  return (
    <div className="flex flex-col h-screen">
      {/* Header */}
      <div className="px-8 pt-8 pb-4 border-b border-ink-700 flex-shrink-0">
        <SectionHeader
          title="Repository Q&A"
          subtitle="RAG-powered question answering over your codebase"
          actions={
            messages.length > 0 && (
              <Button
                variant="ghost"
                size="sm"
                icon={<Trash2 size={13} />}
                onClick={clearHistory}
              >
                Clear
              </Button>
            )
          }
        />

        {/* Repo selector */}
        <div className="max-w-sm">
          <RepoSelector value={repoId} onChange={setRepoId} />
        </div>
      </div>

      {/* Messages area */}
      <div className="flex-1 overflow-y-auto px-8 py-6">
        {!repoId ? (
          <EmptyState
            icon={MessageSquare}
            title="Select a repository"
            description="Choose an indexed repository above to start asking questions."
          />
        ) : messages.length === 0 ? (
          <div className="max-w-2xl mx-auto">
            {/* Welcome */}
            <div className="text-center mb-10">
              <div className="w-16 h-16 rounded-2xl bg-plasma-muted border border-plasma/20 flex items-center justify-center mx-auto mb-4">
                <MessageSquare size={28} className="text-plasma-light" />
              </div>
              <h2 className="font-display text-frost text-xl font-bold mb-2">
                Ask anything about your code
              </h2>
              <p className="text-frost-dim text-sm font-body">
                CodeSense retrieves relevant context and generates accurate answers using RAG.
              </p>
            </div>

            {/* Example questions */}
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-2">
              {EXAMPLE_QUESTIONS.map((q) => (
                <button
                  key={q}
                  onClick={() => { setInput(q); inputRef.current?.focus(); }}
                  className="text-left px-4 py-3 glass rounded-xl text-sm font-body text-frost-dim hover:text-frost hover:border-acid/20 transition-all group"
                >
                  <span className="text-acid mr-2 group-hover:text-acid">→</span>
                  {q}
                </button>
              ))}
            </div>
          </div>
        ) : (
          <div className="max-w-3xl mx-auto space-y-6">
            {messages.map((msg) => (
              <Message key={msg.ts} msg={msg} />
            ))}

            {/* Typing indicator */}
            {loading && (
              <div className="flex gap-3 animate-slide-up">
                <div className="w-8 h-8 rounded-lg bg-plasma-muted border border-plasma/20 flex items-center justify-center">
                  <Cpu size={14} className="text-plasma-light" />
                </div>
                <div className="glass border border-ink-600 rounded-xl px-4 py-3">
                  <div className="flex gap-1 items-center">
                    <div className="w-1.5 h-1.5 rounded-full bg-frost-dim animate-bounce" style={{ animationDelay: "0ms" }} />
                    <div className="w-1.5 h-1.5 rounded-full bg-frost-dim animate-bounce" style={{ animationDelay: "150ms" }} />
                    <div className="w-1.5 h-1.5 rounded-full bg-frost-dim animate-bounce" style={{ animationDelay: "300ms" }} />
                    <span className="text-xs text-frost-dim font-mono ml-2">Searching codebase…</span>
                  </div>
                </div>
              </div>
            )}

            <div ref={bottomRef} />
          </div>
        )}
      </div>

      {/* Input bar */}
      <div className="px-8 py-4 border-t border-ink-700 flex-shrink-0">
        <div className="max-w-3xl mx-auto flex gap-3">
          <div className="relative flex-1">
            <textarea
              ref={inputRef}
              rows={1}
              placeholder={repoId ? "Ask a question about this codebase…" : "Select a repository first"}
              value={input}
              disabled={!repoId}
              onChange={(e) => setInput(e.target.value)}
              onKeyDown={(e) => {
                if (e.key === "Enter" && !e.shiftKey) {
                  e.preventDefault();
                  handleSend();
                }
              }}
              className="w-full bg-ink-800 border border-ink-600 text-frost placeholder-frost-dim font-body text-sm rounded-xl px-4 py-3 pr-4 focus:outline-none focus:border-acid/40 focus:ring-1 focus:ring-acid/20 transition-all resize-none disabled:opacity-40 disabled:cursor-not-allowed"
              style={{ minHeight: "48px", maxHeight: "120px" }}
            />
          </div>
          <Button
            onClick={handleSend}
            disabled={!input.trim() || !repoId}
            loading={loading}
            size="lg"
            className="self-end"
            icon={<Send size={14} />}
          >
            Send
          </Button>
        </div>
        <p className="text-xs text-frost-dim font-mono text-center mt-2 opacity-50">
          Enter to send · Shift+Enter for new line
        </p>
      </div>
    </div>
  );
}
