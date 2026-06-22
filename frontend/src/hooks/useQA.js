// src/hooks/useQA.js
import { useState, useCallback } from "react";
import { qaApi } from "../services/api"; //communicate with backend QA endpoint
//custom hook or function for a specific repo
export function useQA(repoId) {
  const [messages, setMessages] = useState([]); //stores entire chat
  const [loading, setLoading] = useState(false); //show spinner
  const [error, setError] = useState(null); //stores errors

  const ask = useCallback(
    async (question) => {
      if (!question.trim() || !repoId) return; //stop if no question or no repo

      const userMsg = { role: "user", content: question, ts: Date.now() }; //creates msg for user
      setMessages((prev) => [...prev, userMsg]); //adds the msg to chat
      setLoading(true);
      setError(null);

      try {
        const data = await qaApi.ask({ repo_id: repoId, question }); //API call
        //creates chat bubble
        const assistantMsg = {
          role: "assistant",
          content: data.answer,
          sources: data.sources || data.context_chunks || [], //which chunks were used to answer
          latency_ms: data.latency_ms, //time taken to respond
          is_fallback: data.is_fallback, //did llm fail
          ts: Date.now(),
        };
        setMessages((prev) => [...prev, assistantMsg]);
      } catch (err) {
        setError(err.message);
        const errMsg = { //add assistant message
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
  //reset chat
  const clearHistory = useCallback(() => {
    setMessages([]);
    setError(null);
  }, []);

  return { messages, loading, error, ask, clearHistory };
}
