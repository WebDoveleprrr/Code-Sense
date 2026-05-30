import { useState, useEffect, useCallback } from "react";
import { repositoriesApi } from "../services/api";

const NON_FINAL_STATUSES = ["pending", "cloning", "parsing", "chunking", "embedding", "indexing", "processing"];

export function useRepositories() {
  const [repos, setRepos] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  const fetchRepos = useCallback(async (isSilent = false) => {
    if (!isSilent) setLoading(true);
    setError(null);
    try {
      const data = await repositoriesApi.list();
      setRepos(data);
    } catch (err) {
      setError(err.message);
    } finally {
      if (!isSilent) setLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchRepos();
  }, [fetchRepos]);

  // Poll silently if any repo is in ingestion processing
  useEffect(() => {
    const hasActive = repos.some(r => NON_FINAL_STATUSES.includes(r.status));
    if (!hasActive) return;

    const interval = setInterval(() => {
      fetchRepos(true);
    }, 4000);

    return () => clearInterval(interval);
  }, [repos, fetchRepos]);

  return { repos, loading, error, refetch: () => fetchRepos() };
}

export function useRepository(repoId) {
  const [repo, setRepo] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  const fetchRepo = useCallback(async (isSilent = false) => {
    if (!repoId) return;
    if (!isSilent) setLoading(true);
    setError(null);
    try {
      const data = await repositoriesApi.get(repoId);
      setRepo(data);
    } catch (err) {
      setError(err.message);
    } finally {
      if (!isSilent) setLoading(false);
    }
  }, [repoId]);

  useEffect(() => {
    fetchRepo();
  }, [fetchRepo]);

  // Poll silently if the selected repo is in ingestion processing
  useEffect(() => {
    if (!repo || !NON_FINAL_STATUSES.includes(repo.status)) return;

    const interval = setInterval(() => {
      fetchRepo(true);
    }, 3000);

    return () => clearInterval(interval);
  }, [repo, repoId, fetchRepo]);

  return { repo, loading, error, refetch: () => fetchRepo() };
}
