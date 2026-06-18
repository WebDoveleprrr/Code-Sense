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
  const token = localStorage.getItem("access_token");
  if (token) {
    config.headers.Authorization = `Bearer ${token}`;
  }
  return config;
});

// Response interceptor — normalize errors & handle token refresh
let isRefreshing = false;
let failedQueue = [];

const processQueue = (error, token = null) => {
  failedQueue.forEach(prom => {
    if (error) {
      prom.reject(error);
    } else {
      prom.resolve(token);
    }
  });
  failedQueue = [];
};

api.interceptors.response.use(
  (res) => res.data,
  async (err) => {
    const originalRequest = err.config;
    
    const isTokenExpired = err.response?.data?.code === "TOKEN_EXPIRED" || err.response?.status === 401;

    if (isTokenExpired && !originalRequest._retry) {
      if (isRefreshing) {
        return new Promise(function(resolve, reject) {
          failedQueue.push({ resolve, reject });
        }).then(token => {
          originalRequest.headers.Authorization = `Bearer ${token}`;
          return api(originalRequest);
        }).catch(err => {
          return Promise.reject(err);
        });
      }

      originalRequest._retry = true;
      isRefreshing = true;

      try {
        let newAccessToken;
        if (window.__codesenseRestoreSession) {
          newAccessToken = await window.__codesenseRestoreSession();
        } else {
          // Fallback if context not mounted
          const refreshToken = localStorage.getItem("refresh_token");
          if (!refreshToken) throw new Error("No refresh token");
          const resp = await axios.post(
            `${BASE_URL}/auth/refresh`,
            { refresh_token: refreshToken },
            { headers: { "Content-Type": "application/json" } }
          );
          newAccessToken = resp.data.access_token;
          localStorage.setItem("access_token", newAccessToken);
          localStorage.setItem("refresh_token", resp.data.refresh_token);
        }
        
        processQueue(null, newAccessToken);
        originalRequest.headers.Authorization = `Bearer ${newAccessToken}`;
        return await api(originalRequest);
        
      } catch (refreshErr) {
        processQueue(refreshErr, null);
        if (window.__codesenseLogout) {
          window.__codesenseLogout();
        } else {
          localStorage.removeItem("access_token");
          localStorage.removeItem("refresh_token");
          localStorage.removeItem("user");
        }
        window.location.href = "/login?expired=1";
        return Promise.reject(refreshErr);
      } finally {
        isRefreshing = false;
      }
    }
    
    const msg =
      err.response?.data?.detail ||
      err.response?.data?.message ||
      err.message ||
      "Unknown error";
    return Promise.reject(new Error(typeof msg === 'string' ? msg : JSON.stringify(msg)));
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

// ─── Impact Analysis ─────────────────────────────────────────────────────────

export const impactApi = {
  /** Run impact analysis for a file/symbol */
  analyze: (payload) => api.post("/impact/analyze", payload),
  rebuild: (repoId) => api.post(`/impact/rebuild?repo_id=${repoId}`),
};

// ─── AI Code Review ──────────────────────────────────────────────────────────

export const reviewApi = {
  /** Run AI code review on the repository */
  analyze: (payload) => api.post("/review/analyze", payload),
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

// ─── Authentication ──────────────────────────────────────────────────────────

export const authApi = {
  loginGoogle: (idToken) => api.post("/auth/google", { id_token: idToken }),
  refresh: (refreshToken) => api.post("/auth/refresh", { refresh_token: refreshToken }),
  getMe: () => api.get("/auth/me"),
};

export default api;
