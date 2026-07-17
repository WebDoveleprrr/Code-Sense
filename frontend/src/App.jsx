// src/App.jsx --- connects whole frontend
import React, { useContext, Suspense, lazy } from "react"; //usecontext access global data
import { BrowserRouter, Routes, Route, Navigate } from "react-router-dom"; //without browserrouter only 1 page will work,with it all pages work
import { Toaster } from "react-hot-toast"; //popup mmsg like repo uploaded,etc
import AppShell from "./components/layout/AppShell";
import LandingPage from "./pages/LandingPage";      //route defines a path(road) while navigate uses the path and goes to a page(vehicle)
import Login from "./pages/Login";
import { AuthProvider, AuthContext } from "./context/AuthContext";
import { Loader2 } from "lucide-react";
//authprovider --- stores login state , authcontext --- gives access to login state

// Lazy loaded routes
const Dashboard = lazy(() => import("./pages/Dashboard"));
const UploadPage = lazy(() => import("./pages/Upload"));
const SemanticSearch = lazy(() => import("./pages/SemanticSearch"));
const QAChat = lazy(() => import("./pages/QAChat"));
const ExplainCode = lazy(() => import("./pages/ExplainCode"));
const DependencyGraph = lazy(() => import("./pages/DependencyGraph"));
const Architecture = lazy(() => import("./pages/Architecture"));
const ImpactAnalysis = lazy(() => import("./pages/ImpactAnalysis"));
const AIReview = lazy(() => import("./pages/AIReview"));
const Settings = lazy(() => import("./pages/Settings"));

//this func used to secure routes.this uses authcontext and checks authenticated state
function ProtectedRoute({ children }) {
  const { authenticated } = useContext(AuthContext);
  if (!authenticated) {
    return <Navigate to="/login" replace />;
  }
  return children; //allow page access if user is authorised
}

const LoadingFallback = () => (
  <div className="flex-1 flex flex-col items-center justify-center h-full">
    <Loader2 size={40} className="text-indigo-500 animate-spin mb-4" />
    <p className="text-slate-400">Loading module...</p>
  </div>
);

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
                <Suspense fallback={<LoadingFallback />}>
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
                </Suspense>
              </AppShell>
            </ProtectedRoute>
          }
        />
      </Routes>
    </BrowserRouter>
    </AuthProvider>
  );
}
