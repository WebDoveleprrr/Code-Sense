// src/App.jsx --- connects whole frontend
import React, { useContext } from "react"; //usecontext access global data
import { BrowserRouter, Routes, Route, Navigate } from "react-router-dom"; //without browserrouter only 1 page will work,with it all pages work
import { Toaster } from "react-hot-toast"; //popup mmsg like repo uploaded,etc
import AppShell from "./components/layout/AppShell";
import LandingPage from "./pages/LandingPage";      //route defines a path(road) while navigate uses the path and goes to a page(vehicle)
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
import Settings from "./pages/Settings";
import { AuthProvider, AuthContext } from "./context/AuthContext";
//authprovider --- stores login state , authcontext --- gives access to login state

//this func used to secure routes.this uses authcontext and checks authenticated state
function ProtectedRoute({ children }) {
  const { authenticated } = useContext(AuthContext);
  if (!authenticated) {
    return <Navigate to="/login" replace />;
  }
  return children; //allow page access if user is authorised
}

export default function App() {
  return (
    <AuthProvider>
    <BrowserRouter future={{ v7_startTransition: true, v7_relativeSplatPath: true }}>
      <Toaster
        position="top-right"
        toastOptions={{
          style: {
            background: "#0f172a",
            color: "#f8fafc",
            border: "1px solid #1e293b",
            fontFamily: "'Inter', sans-serif",
            fontSize: "13px",
          },
          success: {
            iconTheme: { primary: "#6366f1", secondary: "#ffffff" },
          },
          error: {
            iconTheme: { primary: "#ef4444", secondary: "#ffffff" },
          },
        }}
      />
      <Routes> {/* similar to switch() case: in cpp */}
        <Route path="/" element={<LandingPage />} />
        <Route path="/login" element={<Login />} />
        <Route
          path="/*"
          element={
            <ProtectedRoute> {/* route only given to authoried users */}
              <AppShell> {/* structure in common for all pages(sidebar,layout,etc) */}
                <Routes>
                  <Route path="/dashboard" element={<Dashboard />} />
                  <Route path="/upload" element={<UploadPage />} />
                  <Route path="/search" element={<SemanticSearch />} />
                  <Route path="/qa" element={<QAChat />} />
                  <Route path="/explain" element={<ExplainCode />} />
                  <Route path="/graph" element={<DependencyGraph />} />
                  <Route path="/impact" element={<ImpactAnalysis />} />
                  <Route path="/review" element={<AIReview />} />
                  <Route path="/architecture" element={<Architecture />} />
                  <Route path="/settings" element={<Settings />} />
                  <Route path="*" element={<Navigate to="/dashboard" replace />} />
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
