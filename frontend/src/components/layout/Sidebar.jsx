//provides navigation to each page needed
import React, { useState } from "react";
import { NavLink, useLocation } from "react-router-dom";
import {
  LayoutDashboard, Upload, Search, MessageSquare, Zap, GitBranch,
  Building2, Shuffle, ShieldAlert, Settings, ChevronLeft, ChevronRight, Zap as LogoIcon
} from "lucide-react";

//store evrything in one array
const NAV_GROUPS = [
  {
    title: "Repositories",
    items: [
      { to: "/dashboard", icon: LayoutDashboard, label: "Dashboard" },
      { to: "/upload", icon: Upload, label: "Upload" },
    ]
  },
  {
    title: "AI Analysis",
    items: [
      { to: "/search", icon: Search, label: "Semantic Search" },
      { to: "/qa", icon: MessageSquare, label: "Repo Q&A" },
      { to: "/explain", icon: Zap, label: "Explain Code" },
      { to: "/review", icon: ShieldAlert, label: "AI Review" },
    ]
  },
  {
    title: "Architecture",
    items: [
      { to: "/graph", icon: GitBranch, label: "Dependency Graph" },
      { to: "/impact", icon: Shuffle, label: "Impact Analysis" },
      { to: "/architecture", icon: Building2, label: "Architecture" },
    ]
  },
  {
    title: "Account",
    items: [
      { to: "/settings", icon: Settings, label: "Settings" },
    ]
  }
];

export default function Sidebar() {
  const [collapsed, setCollapsed] = useState(false); //sidebar expanded or collapsed
  const location = useLocation(); //gets current URL

  return (
    <aside //aside --- html tag for side panel
      className={`relative flex flex-col transition-all duration-300 ease-in-out border-r border-slate-800 bg-slate-950 ${
        collapsed ? "w-16" : "w-64"
      }`}
    >
      {/* Logo */}
      <div className="flex items-center gap-3 px-4 py-5 h-16 border-b border-slate-800 shrink-0">
        <div className="w-8 h-8 rounded-lg bg-indigo-600 flex items-center justify-center flex-shrink-0 shadow-glow">
          <LogoIcon size={16} className="text-white" />
        </div>
        {!collapsed && (
          <span className="font-semibold text-lg text-slate-50 tracking-tight">
            CodeSense
          </span>
        )}
      </div>

      {/* Nav */}
      <nav className="flex-1 overflow-y-auto py-4 scrollbar-none">
        {NAV_GROUPS.map((group, idx) => (
          <div key={idx} className="mb-6 px-3">
            {!collapsed && (
              <h3 className="px-3 mb-2 text-xs font-semibold text-slate-500 uppercase tracking-wider">
                {group.title}
              </h3>
            )}
            <div className="space-y-1">
              {group.items.map(({ to, icon: Icon, label }) => {
                const isActive = location.pathname.startsWith(to);
                return (
                  <NavLink
                    key={to}
                    to={to}
                    title={collapsed ? label : undefined}
                    className={`flex items-center gap-3 px-3 py-2 rounded-md text-sm transition-all group ${
                      isActive
                        ? "bg-indigo-500/10 text-indigo-400 font-medium"
                        : "text-slate-400 hover:text-slate-100 hover:bg-slate-800/50"
                    }`}
                  >
                    <Icon
                      size={16}
                      className={`flex-shrink-0 ${
                        isActive ? "text-indigo-400" : "text-slate-500 group-hover:text-slate-300"
                      }`}
                    />
                    {!collapsed && <span className="truncate">{label}</span>}
                  </NavLink>
                );
              })}
            </div>
          </div>
        ))}
      </nav>

      {/* Collapse toggle */}
      <button
        onClick={() => setCollapsed(!collapsed)}
        className="absolute -right-3 top-20 w-6 h-6 rounded-full bg-slate-800 border border-slate-700 flex items-center justify-center text-slate-400 hover:text-white transition-all z-10 hover:scale-110"
      >
        {collapsed ? <ChevronRight size={14} /> : <ChevronLeft size={14} />}
      </button>
    </aside>
  );
}
