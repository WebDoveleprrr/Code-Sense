// src/hooks/useAuth.js
import { useState, useEffect } from "react";
import { authApi } from "../services/api";

export default function useAuth() {
  const [user, setUser] = useState(() => {
    try {
      const stored = localStorage.getItem("user");
      return stored ? JSON.parse(stored) : null;
    } catch {
      return null;
    }
  });
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    async function checkSession() {
      const token = localStorage.getItem("access_token");
      if (!token) {
        setUser(null);
        setLoading(false);
        return;
      }
      try {
        const me = await authApi.getMe();
        setUser(me);
        localStorage.setItem("user", JSON.stringify(me));
      } catch (err) {
        console.error("Session verification failed", err);
        // Interceptor will try refresh; if both fail, it redirects to login
      } finally {
        setLoading(false);
      }
    }
    checkSession();
  }, []);

  const loginWithGoogleToken = async (idToken) => {
    setLoading(true);
    try {
      const res = await authApi.loginGoogle(idToken);
      localStorage.setItem("access_token", res.access_token);
      localStorage.setItem("refresh_token", res.refresh_token);
      localStorage.setItem("user", JSON.stringify(res.user));
      setUser(res.user);
      return res.user;
    } catch (err) {
      console.error("Google login failed:", err);
      throw err;
    } finally {
      setLoading(false);
    }
  };

  const logout = () => {
    localStorage.removeItem("access_token");
    localStorage.removeItem("refresh_token");
    localStorage.removeItem("user");
    setUser(null);
    window.location.href = "/login";
  };

  return {
    user,
    loading,
    loginWithGoogleToken,
    logout,
    isAuthenticated: !!user,
  };
}
