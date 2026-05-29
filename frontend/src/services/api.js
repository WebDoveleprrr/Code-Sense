// src/services/api.js
import axios from "axios";

const BASE_URL = import.meta.env?.VITE_API_URL || "https://codesense-backend-18lv.onrender.com/api/v1";

const api = axios.create({
  baseURL: BASE_URL,
  timeout: 60000,
  headers: { "Content-Type": "application/json" },
});

// Request interceptor
api.interceptors.request.use((config) => {
  return config;
});

// Response interceptor — normalize errors
api.interceptors.response.use(
  (res) => res.data,
  (err) => {
    const msg =
      err.response?.data?.detail ||
      err.response?.data?.message ||
      err.message ||
      "Unknown error";
    return Promise.reject(new Error(msg));
  }
);

// ─── Repositories ────────────────────────────────────────────────────────────

export const repositoriesApi = {
  /** List all repositories, optional status filter */
  list: (status) =>
    api.get("/repositories", { params: status ? { status } : {} }),

  /** Get detailed info for one repo */
  get: (repoId) => api.get(`/repositories/${repoId}`),

  /** Get parsed files for a repo */
  getFiles: (repoId) => api.get(`/repositories/${repoId}/files`),

  /** Get chunk documents */
  getChunks: (repoId, params = {}) =>
    api.get(`/repositories/${repoId}/chunks`, { params }),

  /** Ingest from GitHub URL */
  ingestGitHub: (githubUrl, branch = "main") =>
    api.post("/repositories/github", { github_url: githubUrl, branch }),

  /** Upload ZIP file */
  uploadZip: (file, onProgress) => {
    const formData = new FormData();
    formData.append("file", file);
    return api.post("/repositories/upload", formData, {
      headers: { "Content-Type": "multipart/form-data" },
      onUploadProgress: onProgress,
    });
  },

  /** Delete a repository */
  delete: (repoId) => api.delete(`/repositories/${repoId}`),
};

// ─── Semantic Search ──────────────────────────────────────────────────────────

export const searchApi = {
  /** Semantic code search */
  search: (payload) => api.post("/search", payload),

  /** Batch search */
  batchSearch: (payload) => api.post("/search/batch", payload),

  /** Embedding model info */
  info: () => api.get("/search/info"),
};

// ─── Q&A ─────────────────────────────────────────────────────────────────────

export const qaApi = {
  /** Ask a question about a repository */
  ask: (payload) => api.post("/qa", payload),
};

// ─── Explain ─────────────────────────────────────────────────────────────────

export const explainApi = {
  /** Explain a code range */
  explain: (payload) => api.post("/explain", payload),
};

// ─── Dependency Graph ─────────────────────────────────────────────────────────

export const dependencyApi = {
  /** Build dependency graph for a repo */
  buildGraph: (repoId) => api.get(`/dependency/${repoId}`),
};

// ─── Architecture ─────────────────────────────────────────────────────────────

export const architectureApi = {
  /** Get architecture summary */
  summarise: (repoId, provider) =>
    api.get(`/architecture/${repoId}`, {
      params: provider ? { provider } : {},
    }),
};

// ─── Health ───────────────────────────────────────────────────────────────────

export const healthApi = {
  ping: () => api.get("/health"),
};

export default api;
