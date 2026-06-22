//common layout for all pages
//everything inside this becomes children
import React, { useState, useContext } from "react";
import Sidebar from "./Sidebar";
import { useNavigate } from "react-router-dom";
import { LogOut, Settings, User } from "lucide-react";
import { AuthContext } from "../../context/AuthContext";

export default function AppShell({ children }) {
  const navigate = useNavigate();
  const [menuOpen, setMenuOpen] = useState(false); //handles dropdown for profile icon
  const { user, logout } = useContext(AuthContext);

  const handleLogout = () => {
    logout();
    navigate("/login");
  };

  return (
    <div className="flex h-screen overflow-hidden bg-slate-950 text-slate-50 font-sans selection:bg-indigo-500/30">
      <Sidebar />
      <div className="flex-1 flex flex-col min-w-0 overflow-hidden bg-slate-900">
        {/* Top Header */}
        <header className="h-16 flex items-center justify-between px-6 border-b border-slate-800 bg-slate-950 shrink-0">
          <div className="flex-1" />
          {/* Profile Menu */}
          <div className="relative">
            <button 
              onClick={() => setMenuOpen(!menuOpen)}
              className="flex items-center gap-3 hover:bg-slate-800 p-1.5 pl-3 rounded-full transition-colors border border-slate-800"
            >
              <div className="text-right hidden sm:block">
                <div className="text-sm font-medium leading-none text-slate-200">{user?.name || "Developer"}</div>
                <div className="text-xs text-slate-500 mt-1 leading-none">{user?.email || "dev@codesense.ai"}</div>
              </div>
              <div className="w-8 h-8 rounded-full bg-indigo-600 flex items-center justify-center overflow-hidden shrink-0">
                {user?.picture ? (
                  <img src={user.picture} alt="Profile" className="w-full h-full object-cover" />
                ) : (
                  <User size={16} className="text-white" />
                )}
              </div>
            </button>

            {menuOpen && (
              <>
                <div className="fixed inset-0 z-40" onClick={() => setMenuOpen(false)} />
                <div className="absolute right-0 mt-2 w-48 bg-slate-800 border border-slate-700 rounded-xl shadow-xl z-50 overflow-hidden py-1">
                  <button onClick={() => { setMenuOpen(false); navigate("/settings"); }} className="w-full flex items-center gap-2 px-4 py-2 text-sm text-slate-300 hover:bg-slate-700 hover:text-white transition-colors">
                    <User size={14} /> Profile
                  </button>
                  <button onClick={() => { setMenuOpen(false); navigate("/settings"); }} className="w-full flex items-center gap-2 px-4 py-2 text-sm text-slate-300 hover:bg-slate-700 hover:text-white transition-colors">
                    <Settings size={14} /> Settings
                  </button>
                  <div className="h-px bg-slate-700 my-1" />
                  <button onClick={handleLogout} className="w-full flex items-center gap-2 px-4 py-2 text-sm text-red-400 hover:bg-slate-700 transition-colors">
                    <LogOut size={14} /> Logout
                  </button>
                </div>
              </>
            )}
          </div>
        </header>

        {/* Main Content */}
        <main className="flex-1 overflow-y-auto relative">
          <div className="page-enter min-h-full">
            {children}
          </div>
        </main>
      </div>
    </div>
  );
}
