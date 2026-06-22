// src/context/AuthContext.jsx
import React, { createContext, useState, useCallback, useEffect } from "react"; //usecallback ---- reuse an already created function without letting it created for every render
import { authApi } from "../services/api";
//creates a global container
export const AuthContext = createContext({
  authenticated: false,
  refreshing: false,
  expired: false,
  user: null,
  login: (accessToken, refreshToken, user) => {},
  restoreSession: async () => {},
  logout: () => {},
});

// AuthContext acts as the Global Authentication Manager.

// Without AuthContext:
// App
// └── Dashboard
//     └── Sidebar
//         └── Profile
//
// User information would need to be passed through
// multiple component levels using props
// (called Prop Drilling).
//
// With AuthContext:
//
// Any component can access authentication state using:
//
// const { user, authenticated } = useContext(AuthContext);
//
// This provides:
//
// - Current user information
// - Login function
// - Logout function
// - Session restoration logic
// - Authentication status
//
// from anywhere in the React application.
//
// AuthContext also synchronizes React state with
// localStorage so authentication survives page refreshes.

//global authentication
export function AuthProvider({ children }) {
  const [authenticated, setAuthenticated] = useState(!!localStorage.getItem("access_token")); //"!!" converts the term beside to boolean
  const [refreshing, setRefreshing] = useState(false); //when access token is expired, we call refresh API during this period this state becomes true
  const [expired, setExpired] = useState(false); //toggles when session is expired
  const [user, setUser] = useState(() => { //useState(() => ...)   lazy initialisation (runs only first time) but normally for use state it runs for every render
    try {
      const u = localStorage.getItem("user");
      return u ? JSON.parse(u) : null;
    } catch {
      return null;
    }
  });

  //browser remembers access token,refresh token and user
  const login = useCallback((accessToken, refreshToken, userData) => {
    localStorage.setItem("access_token", accessToken);
    localStorage.setItem("refresh_token", refreshToken);
    localStorage.setItem("user", JSON.stringify(userData));
    setAuthenticated(true);  //updates react so dashboard visible
    setUser(userData);
    setExpired(false);
  }, []);
  //deletes all the above stored items
  const logout = useCallback(() => {
    localStorage.removeItem("access_token");
    localStorage.removeItem("refresh_token");
    localStorage.removeItem("user");
    setAuthenticated(false); //user logged out
    setUser(null);
    setExpired(true);
  }, []);

  //when access token expires normally we get errors saying unauthorised from backend
  //but here refresh token is created and a new access token also and the session continues without user noticing
  //called by window.__codesenseRestoreSession() in api.js
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
      return res.access_token; //api.js needs access token
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
      // Cleanup to prevent memory leaks
      delete window.__codesenseRestoreSession;
      delete window.__codesenseLogout;
    };
  }, [restoreSession, logout]);

  return (
    <AuthContext.Provider value={{ authenticated, refreshing, expired, user, login, restoreSession, logout }}> //everything stored globally
      {refreshing && (
        <div className="fixed top-0 left-0 w-full z-50 bg-acid text-ink-950 py-1.5 px-4 text-center font-mono text-xs font-bold animate-slide-down shadow-md">
          Restoring session...
        </div>
      )}
      {children}
    </AuthContext.Provider>
  );
}
