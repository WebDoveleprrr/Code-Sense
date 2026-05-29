// src/hooks/useSearch.js
import { useState, useCallback } from "react";
import { searchApi } from "../services/api";

export function useSearch() {
  const [results, setResults] = useState([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const [meta, setMeta] = useState(null);

  const search = useCallback(async (payload) => {
    setLoading(true);
    setError(null);
    try {
      const data = await searchApi.search(payload);
      setResults(data.results || []);
      setMeta({ query: data.query, latency_ms: data.latency_ms });
    } catch (err) {
      setError(err.message);
      setResults([]);
    } finally {
      setLoading(false);
    }
  }, []);

  const clear = useCallback(() => {
    setResults([]);
    setMeta(null);
    setError(null);
  }, []);

  return { results, loading, error, meta, search, clear };
}
