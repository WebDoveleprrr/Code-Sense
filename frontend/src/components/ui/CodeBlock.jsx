// src/components/ui/CodeBlock.jsx
import React, { useState } from "react";
import { Prism as SyntaxHighlighter } from "react-syntax-highlighter";
import { Copy, Check } from "lucide-react";

const customTheme = {
  'code[class*="language-"]': {
    color: "#e2e8f0",
    fontFamily: "'JetBrains Mono', monospace",
    fontSize: "12px",
    lineHeight: "1.6",
  },
  'pre[class*="language-"]': {
    background: "transparent",
    margin: 0,
    padding: 0,
    overflow: "auto",
  },
  keyword: { color: "#00ff88" },
  string: { color: "#a855f7" },
  comment: { color: "#4a5568", fontStyle: "italic" },
  function: { color: "#60a5fa" },
  number: { color: "#f59e0b" },
  operator: { color: "#94a3b8" },
  punctuation: { color: "#64748b" },
  "class-name": { color: "#f472b6" },
  variable: { color: "#e2e8f0" },
  builtin: { color: "#00cc6a" },
  boolean: { color: "#f59e0b" },
  "attr-name": { color: "#60a5fa" },
  "attr-value": { color: "#a855f7" },
  tag: { color: "#f472b6" },
  decorator: { color: "#f59e0b" },
  import: { color: "#00ff88" },
};

export default function CodeBlock({
  code,
  language = "python",
  showCopy = true,
  startLine = 1,
  maxHeight = "400px",
  compact = false,
}) {
  const [copied, setCopied] = useState(false);

  const handleCopy = async () => {
    await navigator.clipboard.writeText(code);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  return (
    <div className="relative group rounded-lg overflow-hidden bg-ink-900 border border-ink-600">
      {/* Header bar */}
      <div className="flex items-center justify-between px-4 py-2 bg-ink-800 border-b border-ink-600">
        <div className="flex items-center gap-2">
          <div className="flex gap-1.5">
            <div className="w-2.5 h-2.5 rounded-full bg-danger/60" />
            <div className="w-2.5 h-2.5 rounded-full bg-signal/60" />
            <div className="w-2.5 h-2.5 rounded-full bg-acid/60" />
          </div>
          <span className="text-xs text-frost-dim font-mono ml-1">{language}</span>
          {startLine > 1 && (
            <span className="text-xs text-frost-dim font-mono">
              L{startLine}
            </span>
          )}
        </div>
        {showCopy && (
          <button
            onClick={handleCopy}
            className="flex items-center gap-1 text-xs text-frost-dim hover:text-acid font-mono transition-colors"
          >
            {copied ? (
              <>
                <Check size={12} className="text-acid" />
                <span className="text-acid">Copied!</span>
              </>
            ) : (
              <>
                <Copy size={12} />
                Copy
              </>
            )}
          </button>
        )}
      </div>

      {/* Code */}
      <div
        className="overflow-auto code-scroll"
        style={{ maxHeight: compact ? "160px" : maxHeight }}
      >
        <div className="px-4 py-3">
          <SyntaxHighlighter
            language={language === "c++" ? "cpp" : language}
            style={customTheme}
            showLineNumbers={!compact}
            startingLineNumber={startLine}
            lineNumberStyle={{
              color: "#22223a",
              minWidth: "2.5em",
              paddingRight: "1em",
              userSelect: "none",
            }}
            customStyle={{ background: "transparent", margin: 0, padding: 0 }}
            wrapLongLines={false}
          >
            {code}
          </SyntaxHighlighter>
        </div>
      </div>
    </div>
  );
}
