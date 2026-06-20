import React, { createContext, useState, useCallback, useEffect } from "react";
import { authApi } from "../services/api";

export const AuthContext = createContext({
  authenticated: false,
  refreshing: false,
  expired: false,
  user: null,
  login: (accessToken, refreshToken, user) => {},
  restoreSession: async () => {},
  logout: () => {},
});

export function AuthProvider({ children }) {
  const [authenticated, setAuthenticated] = useState(!!localStorage.getItem("access_token"));
  const [refreshing, setRefreshing] = useState(false);
  const [expired, setExpired] = useState(false);
  const [user, setUser] = useState(() => {
    try {
      const u = localStorage.getItem("user");
      return u ? JSON.parse(u) : null;
    } catch {
      return null;
    }
  });

  const login = useCallback((accessToken, refreshToken, userData) => {
    localStorage.setItem("access_token", accessToken);
    localStorage.setItem("refresh_token", refreshToken);
    localStorage.setItem("user", JSON.stringify(userData));
    setAuthenticated(true);
    setUser(userData);
    setExpired(false);
  }, []);

  const logout = useCallback(() => {
    localStorage.removeItem("access_token");
    localStorage.removeItem("refresh_token");
    localStorage.removeItem("user");
    setAuthenticated(false);
    setUser(null);
    setExpired(true);
  }, []);

  const restoreSession = useCallback(async () => {
    if (refreshing) return;
    const refreshToken = localStorage.getItem("refresh_token");
    if (!refreshToken) {
      logout();
      return Promise.reject(new Error("No refresh token available"));
    }

    setRefreshing(true);
    setExpired(false);
    
    try {
      const res = await authApi.refresh(refreshToken);
      localStorage.setItem("access_token", res.access_token);
      localStorage.setItem("refresh_token", res.refresh_token);
      if (res.user) {
        localStorage.setItem("user", JSON.stringify(res.user));
        setUser(res.user);
      }
      setAuthenticated(true);
      return res.access_token;
    } catch (err) {
      console.error("Session restore failed:", err);
      logout();
      return Promise.reject(err);
    } finally {
      setRefreshing(false);
    }
  }, [refreshing, logout]);

  // Provide a global window function or event listener so api.js can trigger restoreSession
  // Since api.js is outside React context, we can expose the restore function on window.
  useEffect(() => {
    window.__codesenseRestoreSession = restoreSession;
    window.__codesenseLogout = logout;
    return () => {
      delete window.__codesenseRestoreSession;
      delete window.__codesenseLogout;
    };
  }, [restoreSession, logout]);

  return (
    <AuthContext.Provider value={{ authenticated, refreshing, expired, user, login, restoreSession, logout }}>
      {refreshing && (
        <div className="fixed top-0 left-0 w-full z-50 bg-acid text-ink-950 py-1.5 px-4 text-center font-mono text-xs font-bold animate-slide-down shadow-md">
          Restoring session...
        </div>
      )}
      {children}
    </AuthContext.Provider>
  );
}
