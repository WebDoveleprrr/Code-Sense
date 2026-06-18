// src/App.jsx
import React from "react";
import { BrowserRouter, Routes, Route, Navigate } from "react-router-dom";
import { Toaster } from "react-hot-toast";
import AppShell from "./components/layout/AppShell";
import Dashboard from "./pages/Dashboard";
import UploadPage from "./pages/Upload";
import SemanticSearch from "./pages/SemanticSearch";
import QAChat from "./pages/QAChat";
import ExplainCode from "./pages/ExplainCode";
import DependencyGraph from "./pages/DependencyGraph";
import Architecture from "./pages/Architecture";
import Login from "./pages/Login";
import ImpactAnalysis from "./pages/ImpactAnalysis";
import AIReview from "./pages/AIReview";
import { AuthProvider } from "./context/AuthContext";

function ProtectedRoute({ children }) {
  const token = localStorage.getItem("access_token");
  if (!token) {
    return <Navigate to="/login" replace />;
  }
  return children;
}

export default function App() {
  return (
    <AuthProvider>
    <BrowserRouter future={{ v7_startTransition: true, v7_relativeSplatPath: true }}>
      <Toaster
        position="top-right"
        toastOptions={{
          style: {
            background: "#10101e",
            color: "#e2e8f0",
            border: "1px solid #22223a",
            fontFamily: "'JetBrains Mono', monospace",
            fontSize: "13px",
          },
          success: {
            iconTheme: { primary: "#00ff88", secondary: "#050508" },
          },
          error: {
            iconTheme: { primary: "#ef4444", secondary: "#050508" },
          },
        }}
      />
      <Routes>
        <Route path="/login" element={<Login />} />
        <Route
          path="/*"
          element={
            <ProtectedRoute>
              <AppShell>
                <Routes>
                  <Route path="/" element={<Dashboard />} />
                  <Route path="/upload" element={<UploadPage />} />
                  <Route path="/search" element={<SemanticSearch />} />
                  <Route path="/qa" element={<QAChat />} />
                  <Route path="/explain" element={<ExplainCode />} />
                  <Route path="/graph" element={<DependencyGraph />} />
                  <Route path="/impact" element={<ImpactAnalysis />} />
                  <Route path="/review" element={<AIReview />} />
                  <Route path="/architecture" element={<Architecture />} />
                  <Route path="*" element={<Navigate to="/" replace />} />
                </Routes>
              </AppShell>
            </ProtectedRoute>
          }
        />
      </Routes>
    </BrowserRouter>
    </AuthProvider>
  );
}
