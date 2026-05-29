// src/components/layout/AppShell.jsx
import React from "react";
import Sidebar from "./Sidebar";

export default function AppShell({ children }) {
  return (
    <div className="flex h-screen overflow-hidden bg-ink-950 grid-bg">
      <Sidebar />
      <main className="flex-1 overflow-y-auto">
        <div className="page-enter">{children}</div>
      </main>
    </div>
  );
}
