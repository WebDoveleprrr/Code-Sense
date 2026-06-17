// src/pages/Login.jsx
import React, { useState } from "react";
import { useNavigate } from "react-router-dom";
import toast from "react-hot-toast";
import { GoogleLogin } from "@react-oauth/google";

export default function Login() {
  const navigate = useNavigate();
  const [loading, setLoading] = useState(false);
  const [mockEmail, setMockEmail] = useState("developer@codesense.ai");
  const isDev = import.meta.env.DEV === true;

  const handleMockLogin = async (e) => {
    e.preventDefault(); //prevent refresh on form submit
    setLoading(true); //shhow loading spinner
    try {
      // In development/testing, prefix with mock_token_ to trigger bypass on backend
      const token = `mock_token_${mockEmail.split("@")[0]}`;
      const response = await fetch(`${import.meta.env?.VITE_API_URL || "http://localhost:8000/api/v1"}/auth/google`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ id_token: token }),
      });
      const data = await response.json();
      if (response.ok) {
        localStorage.setItem("access_token", data.access_token);
        localStorage.setItem("refresh_token", data.refresh_token);
        localStorage.setItem("user", JSON.stringify(data.user));
        toast.success(`Welcome back, ${data.user.name}!`);
        // Navigate to dashboard
        navigate("/");
      } else {
        toast.error(data.detail || "Authentication failed");
      }
    } catch (err) {
      toast.error("Could not reach backend server");
      console.error(err);
    } finally {
      setLoading(false);
    }
  };

  const handleGoogleSuccess = async (credentialResponse) => {
    setLoading(true);
    try {
      const response = await fetch(`${import.meta.env?.VITE_API_URL || "http://localhost:8000/api/v1"}/auth/google`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ id_token: credentialResponse.credential }),
      });
      const data = await response.json();
      if (response.ok) {
        localStorage.setItem("access_token", data.access_token);
        localStorage.setItem("refresh_token", data.refresh_token);
        localStorage.setItem("user", JSON.stringify(data.user));
        toast.success(`Welcome back, ${data.user.name}!`);
        // Navigate to dashboard
        navigate("/");
      } else {
        toast.error(data.detail || "Authentication failed");
      }
    } catch (err) {
      toast.error("Could not connect to backend server");
      console.error(err);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="relative flex items-center justify-center min-h-screen overflow-hidden bg-slate-950 font-sans">
      {/* Background Orbs */}
      <div className="absolute top-1/4 left-1/4 w-96 h-96 bg-purple-600/20 rounded-full blur-[128px] animate-pulse"></div>
      <div className="absolute bottom-1/4 right-1/4 w-96 h-96 bg-emerald-500/10 rounded-full blur-[128px] animate-pulse delay-1000"></div>

      {/* Grid Pattern */}
      <div className="absolute inset-0 bg-[linear-gradient(to_right,#0f172a_1px,transparent_1px),linear-gradient(to_bottom,#0f172a_1px,transparent_1px)] bg-[size:4rem_4rem] [mask-image:radial-gradient(ellipse_60%_50%_at_50%_50%,#000_70%,transparent_100%)] opacity-30"></div>

      {/* Glass Container */}
      <div className="relative z-10 w-full max-w-md p-8 bg-slate-900/60 backdrop-blur-xl border border-slate-800 rounded-3xl shadow-2xl shadow-purple-950/20 transition-all duration-300 hover:border-slate-700/80">
        
        {/* Logo and Title */}
        <div className="text-center mb-8">
          <div className="inline-flex items-center justify-center w-16 h-16 rounded-2xl bg-gradient-to-tr from-purple-600 to-indigo-500 shadow-lg shadow-purple-500/30 mb-4 animate-bounce duration-[3000ms]">
            <svg className="w-8 h-8 text-white" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
              <path strokeLinecap="round" strokeLinejoin="round" d="M13 10V3L4 14h7v7l9-11h-7z" />
            </svg>
          </div>
          <h1 className="text-3xl font-extrabold tracking-tight bg-gradient-to-r from-purple-200 via-slate-100 to-emerald-200 bg-clip-text text-transparent">
            CodeSense
          </h1>
          <p className="text-slate-400 mt-2 text-sm">
            AI-powered semantic repository intelligence
          </p>
        </div>

        {/* Action Buttons */}
        <div className="space-y-4 flex flex-col items-center">
          <div className="w-full flex justify-center">
            <GoogleLogin
              onSuccess={handleGoogleSuccess}
              onError={() => toast.error("Google Sign-In failed")}
              useOneTap
              theme="filled_black"
              shape="pill"
            />
          </div>

          {isDev && (
            <div className="w-full">
              <div className="relative my-6 text-center">
                <span className="absolute inset-x-0 top-1/2 h-[1px] bg-slate-800"></span>
                <span className="relative z-10 px-3 bg-slate-900/60 backdrop-blur-xl text-xs uppercase tracking-widest text-slate-500 font-semibold">
                  Or developer bypass
                </span>
              </div>

              <form onSubmit={handleMockLogin} className="space-y-4">
                <div>
                  <label className="block text-xs font-semibold text-slate-400 uppercase tracking-wider mb-2">
                    Developer Email
                  </label>
                  <input
                    type="email"
                    value={mockEmail}
                    onChange={(e) => setMockEmail(e.target.value)}
                    required
                    className="w-full px-4 py-3 bg-slate-950/80 border border-slate-800 rounded-xl text-slate-200 placeholder-slate-600 focus:outline-none focus:ring-2 focus:ring-purple-500/40 focus:border-purple-500 transition-all duration-200 font-mono text-sm"
                  />
                </div>

                <button
                  type="submit"
                  disabled={loading}
                  className="relative w-full py-3 bg-gradient-to-r from-purple-600 to-indigo-600 hover:from-purple-500 hover:to-indigo-500 text-white rounded-xl font-medium shadow-lg shadow-purple-500/10 hover:shadow-purple-500/20 hover:scale-[1.01] active:scale-[0.99] transition-all duration-200 disabled:opacity-50"
                >
                  {loading ? (
                    <div className="flex items-center justify-center">
                      <div className="w-5 h-5 border-2 border-white/30 border-t-white rounded-full animate-spin"></div>
                    </div>
                  ) : (
                    "Bypass Sign In"
                  )}
                </button>
              </form>
            </div>
          )}
        </div>

        <div className="mt-8 text-center text-xs text-slate-500 font-mono">
          Security Mode: JWT Authentication Active
        </div>
      </div>
    </div>
  );
}
