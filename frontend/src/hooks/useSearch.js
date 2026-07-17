// src/hooks/useSearch.js ----- actual search logic
import { useState, useCallback, useRef, useEffect } from "react"; //usecallback for reuse a function without creating it everytime
import { searchApi } from "../services/api"; //api.js
//custom hook function for searching
export function useSearch() {
  const [results, setResults] = useState([]);
  const [loading, setLoading] = useState(false); //controls spinner,searching,disable button
  const [error, setError] = useState(null); //error occurred
  const [meta, setMeta] = useState(null); //extra info of a repo
  const abortControllerRef = useRef(null);
  //main function
  const search = useCallback(async (payload) => {
    if (abortControllerRef.current) {
      abortControllerRef.current.abort();
    }
    const controller = new AbortController();
    abortControllerRef.current = controller;

    setLoading(true);
    setError(null);
    try {
      const data = await searchApi.search(payload, { signal: controller.signal }); //POST /search
      setResults(data.results || []); //save results
      setMeta({ query: data.query, latency_ms: data.latency_ms });
    } catch (err) {
      if (err.name === 'CanceledError' || err.message === 'canceled' || err.code === 'ERR_CANCELED') {
        return; // ignore cancelled requests
      }
      setError(err.message); //save error
      setResults([]);
    } finally {
      if (abortControllerRef.current === controller) {
        setLoading(false);
      }
    }
  }, []);  //Can be used like: const {results,loading,error,meta,search,clear} = useSearch(); inside SemanticSearch.jsx

  // Cleanup on unmount
  useEffect(() => {
    return () => {
      if (abortControllerRef.current) {
        abortControllerRef.current.abort();
      }
    };
  }, []);

  const clear = useCallback(() => {
    setResults([]);
    setMeta(null);
    setError(null);
  }, []);

  return { results, loading, error, meta, search, clear };
}
