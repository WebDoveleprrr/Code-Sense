// src/services/api.js
import axios from "axios";

const BASE_URL = import.meta.env?.VITE_API_URL || "http://localhost:8000/api/v1";

const api = axios.create({
  baseURL: BASE_URL,
  timeout: 60000,
  headers: { "Content-Type": "application/json" },
});

// ─────────────────────────────────────────────
// LINES 12-19
// PURPOSE:
// Automatically attaches the JWT Access Token to every outgoing HTTP request.
//
// WHY IT EXISTS:
// Instead of manually passing headers to every `api.get()` or `api.post()` call
// across 50 different React components, this request interceptor centralizes
// the authorization logic.
// ─────────────────────────────────────────────
api.interceptors.request.use((config) => {
  const token = localStorage.getItem("access_token");
  if (token) {
    config.headers.Authorization = `Bearer ${token}`;
  }
  return config;
});

// ─────────────────────────────────────────────
// LINES 21-103
// PURPOSE:
// Global response error handler with an automated JWT Refresh Token rotation queue.
//
// WHY IT EXISTS:
// Access tokens expire quickly (e.g., 60 minutes) for security. When a user
// is active and the token expires, the backend returns a 401 Unauthorized.
// Without this interceptor, the user would be abruptly logged out.
//
// ARCHITECTURE NOTE:
// This implements a "Concurrent Request Queue". If a page loads and fires 4
// API requests simultaneously, and the token is expired, all 4 requests will
// fail with 401. If we simply tried to refresh the token on every 401, we would
// hit the `/auth/refresh` endpoint 4 times in parallel, which often causes race 
// conditions or invalidates the refresh token family.
//
// Instead, `isRefreshing` locks the refresh operation. The first failed request
// initiates the refresh. The other 3 requests are placed into `failedQueue`.
// Once the new token arrives, `processQueue` resolves the 3 waiting requests 
// with the new token, and they seamlessly retry without the user ever noticing.
//
// INTERVIEW NOTE:
// "How do you handle token expiration in a single-page app without disrupting the UX?"
//
// GOOD ANSWER:
// "I implemented an Axios response interceptor with a concurrency queue. When a 401
// occurs, I lock the refresh state. Any subsequent 401s from concurrent requests are
// suspended in a Promise queue. Once the new token is securely fetched, I flush the
// queue, inject the new token into their headers, and automatically replay the original
// requests."
// ─────────────────────────────────────────────

let isRefreshing = false;
let failedQueue = [];

const processQueue = (error, token = null) => {
  // FUNCTION PURPOSE:
  // Flushes the suspended request queue. If the refresh succeeded, it passes
  // the new token to resolve the promises. If it failed, it rejects them.
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
    // FLOW:
    // API Call Fails -> 401
    //   ↓
    // Is another request already refreshing the token?
    //   ├─ YES: Push this request into `failedQueue` and wait.
    //   └─ NO: Lock `isRefreshing = true` and call /auth/refresh
    //        ↓
    //      Refresh Success?
    //        ├─ YES: Save new token, flush queue, retry original request.
    //        └─ NO: Flush queue with errors, purge localStorage, redirect to /login.

    const originalRequest = err.config;
    
    // Only refresh if explicitly told the token is expired.
    // Do NOT refresh on standard 401s (e.g. invalid repo access)
    const isTokenExpired = err.response?.data?.code === "TOKEN_EXPIRED";

    if (isTokenExpired && !originalRequest._retry) {
      if (isRefreshing) {
        // Suspend this request until the lock is released
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
        
        // DEBUGGING NOTE:
        // Because `api.js` is outside the React Tree, it cannot easily access
        // `useContext(AuthContext)`. We use `window.__codesenseRestoreSession` 
        // as a bridge so the AuthContext can manage React State (like `setUser`) 
        // during a silent refresh.
        if (window.__codesenseRestoreSession) {
          newAccessToken = await window.__codesenseRestoreSession();
        } else {
          // Fallback if context not mounted
          const refreshToken = localStorage.getItem("refresh_token");
          if (!refreshToken) throw new Error("No refresh token");
          
          const attemptRefresh = async (retries = 1, delay = 1000) => {
            try {
              return await axios.post(
                `${BASE_URL}/auth/refresh`,
                { refresh_token: refreshToken },
                { headers: { "Content-Type": "application/json" } }
              );
            } catch (e) {
              // Retry on 5xx errors (e.g., backend restarting due to Render ephemerality)
              if (retries > 0 && (!e.response || e.response.status >= 500)) {
                await new Promise(res => setTimeout(res, delay));
                return attemptRefresh(retries - 1, delay * 2);
              }
              throw e;
            }
          };

          const resp = await attemptRefresh();
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

// ─────────────────────────────────────────────
// API ENDPOINT ABSTRACTIONS
// PURPOSE:
// Group all related backend calls into named objects.
//
// WHY IT EXISTS:
// Hardcoding `axios.post('/search', ...)` inside React components makes
// refactoring impossible and scatters business logic. Abstracting them here
// allows React hooks to call `searchApi.search(payload)` cleanly.
// ─────────────────────────────────────────────

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
