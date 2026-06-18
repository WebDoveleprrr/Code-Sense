import React from 'react';

export default function Settings() {
  return (
    <div className="p-8 max-w-4xl mx-auto">
      <div className="mb-8">
        <h1 className="text-3xl font-bold text-slate-50 mb-2">Settings</h1>
        <p className="text-slate-400">Manage your account, preferences, and API integrations.</p>
      </div>

      <div className="space-y-6">
        <section className="p-6 bg-slate-900 border border-slate-800 rounded-2xl">
          <h2 className="text-xl font-semibold mb-4 text-slate-50">Profile</h2>
          <div className="text-slate-400">Profile settings coming soon...</div>
        </section>
        
        <section className="p-6 bg-slate-900 border border-slate-800 rounded-2xl">
          <h2 className="text-xl font-semibold mb-4 text-slate-50">Theme</h2>
          <div className="text-slate-400">Theme customization coming soon...</div>
        </section>

        <section className="p-6 bg-slate-900 border border-slate-800 rounded-2xl">
          <h2 className="text-xl font-semibold mb-4 text-slate-50">About CodeSense</h2>
          <div className="text-slate-400">Version 1.0.0. Premium AI Developer Platform.</div>
        </section>
      </div>
    </div>
  );
}
