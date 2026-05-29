// src/hooks/useQA.js
import { useState, useCallback } from "react";
import { qaApi } from "../services/api";

export function useQA(repoId) {
  const [messages, setMessages] = useState([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);

  const ask = useCallback(
    async (question) => {
      if (!question.trim() || !repoId) return;

      const userMsg = { role: "user", content: question, ts: Date.now() };
      setMessages((prev) => [...prev, userMsg]);
      setLoading(true);
      setError(null);

      try {
        const data = await qaApi.ask({ repo_id: repoId, question });
        const assistantMsg = {
          role: "assistant",
          content: data.answer,
          sources: data.sources || data.context_chunks || [],
          latency_ms: data.latency_ms,
          is_fallback: data.is_fallback,
          ts: Date.now(),
        };
        setMessages((prev) => [...prev, assistantMsg]);
      } catch (err) {
        setError(err.message);
        const errMsg = {
          role: "assistant",
          content: `Error: ${err.message}`,
          isError: true,
          ts: Date.now(),
        };
        setMessages((prev) => [...prev, errMsg]);
      } finally {
        setLoading(false);
      }
    },
    [repoId]
  );

  const clearHistory = useCallback(() => {
    setMessages([]);
    setError(null);
  }, []);

  return { messages, loading, error, ask, clearHistory };
}
