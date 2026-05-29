// src/components/layout/Sidebar.jsx
import React, { useState } from "react";
import { NavLink, useLocation } from "react-router-dom";
import {
  LayoutDashboard,
  Upload,
  Search,
  MessageSquare,
  Zap,
  GitBranch,
  Building2,
  ChevronLeft,
  ChevronRight,
  Cpu,
} from "lucide-react";

const NAV_ITEMS = [
  { to: "/", icon: LayoutDashboard, label: "Dashboard" },
  { to: "/upload", icon: Upload, label: "Upload Repo" },
  { to: "/search", icon: Search, label: "Semantic Search" },
  { to: "/qa", icon: MessageSquare, label: "Repo Q&A" },
  { to: "/explain", icon: Zap, label: "Explain Code" },
  { to: "/graph", icon: GitBranch, label: "Dependency Graph" },
  { to: "/architecture", icon: Building2, label: "Architecture" },
];

export default function Sidebar() {
  const [collapsed, setCollapsed] = useState(false);
  const location = useLocation();

  return (
    <aside
      className={`relative flex flex-col transition-all duration-300 ease-in-out border-r border-ink-600 bg-ink-900 ${
        collapsed ? "w-16" : "w-60"
      }`}
      style={{ minHeight: "100vh" }}
    >
      {/* Logo */}
      <div className="flex items-center gap-3 px-4 py-5 border-b border-ink-600">
        <div className="w-8 h-8 rounded-lg bg-acid flex items-center justify-center flex-shrink-0">
          <Cpu size={16} className="text-ink-950" />
        </div>
        {!collapsed && (
          <div className="overflow-hidden">
            <span className="font-display text-sm font-bold tracking-widest text-acid text-glow-acid">
              CODESENSE
            </span>
            <div className="text-xs text-frost-dim font-mono mt-0.5">v1.0.0</div>
          </div>
        )}
      </div>

      {/* Nav */}
      <nav className="flex-1 px-2 py-4 space-y-1">
        {NAV_ITEMS.map(({ to, icon: Icon, label }) => {
          const isActive =
            to === "/"
              ? location.pathname === "/"
              : location.pathname.startsWith(to);
          return (
            <NavLink
              key={to}
              to={to}
              title={collapsed ? label : undefined}
              className={`flex items-center gap-3 px-3 py-2.5 rounded-lg text-sm font-body transition-all duration-150 group ${
                isActive
                  ? "bg-acid-muted text-acid border border-acid/20"
                  : "text-frost-dim hover:text-frost hover:bg-ink-700"
              }`}
            >
              <Icon
                size={16}
                className={`flex-shrink-0 transition-colors ${
                  isActive ? "text-acid" : "text-frost-dim group-hover:text-frost"
                }`}
              />
              {!collapsed && (
                <span className="truncate">{label}</span>
              )}
              {isActive && !collapsed && (
                <div className="ml-auto w-1 h-1 rounded-full bg-acid" />
              )}
            </NavLink>
          );
        })}
      </nav>

      {/* Collapse toggle */}
      <button
        onClick={() => setCollapsed(!collapsed)}
        className="absolute -right-3 top-20 w-6 h-6 rounded-full bg-ink-700 border border-ink-600 flex items-center justify-center text-frost-dim hover:text-acid hover:border-acid/30 transition-all z-10"
      >
        {collapsed ? <ChevronRight size={12} /> : <ChevronLeft size={12} />}
      </button>

      {/* Footer */}
      <div className="px-3 py-4 border-t border-ink-600">
        {!collapsed ? (
          <div className="text-xs text-frost-dim font-mono opacity-50">
            AI-Powered Repo Intel
          </div>
        ) : (
          <div className="w-2 h-2 rounded-full bg-acid mx-auto status-dot-ready" />
        )}
      </div>
    </aside>
  );
}
