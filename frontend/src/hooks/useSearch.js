// src/hooks/useSearch.js ----- actual search logic
import { useState, useCallback } from "react"; //usecallback for reuse a function without creating it everytime
import { searchApi } from "../services/api"; //api.js
//custom hook function for searching
export function useSearch() {
  const [results, setResults] = useState([]);
  const [loading, setLoading] = useState(false); //controls spinner,searching,disable button
  const [error, setError] = useState(null); //error occurred
  const [meta, setMeta] = useState(null); //extra info of a repo
  //main function
  const search = useCallback(async (payload) => {
    setLoading(true);
    setError(null);
    try {
      const data = await searchApi.search(payload); //POST /search
      setResults(data.results || []); //save results
      setMeta({ query: data.query, latency_ms: data.latency_ms });
    } catch (err) {
      setError(err.message); //save error
      setResults([]);
    } finally {
      setLoading(false);
    }
  }, []);  //Can be used like: const {results,loading,error,meta,search,clear} = useSearch(); inside SemanticSearch.jsx

  const clear = useCallback(() => {
    setResults([]);
    setMeta(null);
    setError(null);
  }, []);

  return { results, loading, error, meta, search, clear };
}
