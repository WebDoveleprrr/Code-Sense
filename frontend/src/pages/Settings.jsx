import React from 'react';
import { useRepositories } from '../hooks/useRepositories';
import { repositoriesApi } from '../services/api';
import toast from 'react-hot-toast';
import { Trash2, RefreshCw, Edit2, X } from 'lucide-react';

export default function Settings() {
  const { repos, refetch, loading } = useRepositories();

  const handleDelete = async (repoId) => {
    if (!window.confirm("Are you sure you want to delete this repository and all its data?")) return;
    try {
      await repositoriesApi.delete(repoId);
      toast.success("Repository deleted");
      refetch();
    } catch (err) {
      toast.error("Failed to delete repository");
    }
  };

  const handleReindex = async (repoId) => {
    try {
      await repositoriesApi.reindex(repoId);
      toast.success("Re-indexing started. Check back in a few minutes.");
      refetch();
    } catch (err) {
      toast.error("Failed to start re-indexing");
    }
  };

  const [renamingRepo, setRenamingRepo] = React.useState(null);
  const [newName, setNewName] = React.useState("");

  const handleRename = async (e) => {
    e.preventDefault();
    if (!newName.trim()) {
      toast.error("Name cannot be empty");
      return;
    }
    try {
      await repositoriesApi.rename(renamingRepo.id, newName);
      toast.success("Repository renamed");
      setRenamingRepo(null);
      setNewName("");
      refetch();
    } catch (err) {
      toast.error(err.response?.data?.detail || "Failed to rename repository");
    }
  };

  return (
    <div className="p-8 max-w-4xl mx-auto">
      <div className="mb-8">
        <h1 className="text-3xl font-bold text-slate-50 mb-2">Settings</h1>
        <p className="text-slate-400">Manage your account, preferences, and API integrations.</p>
      </div>

      <div className="space-y-6">
        <section className="p-6 bg-slate-900 border border-slate-800 rounded-2xl">
          <h2 className="text-xl font-semibold mb-4 text-slate-50">Manage Repositories</h2>
          <div className="text-slate-400">
            {loading ? (
              <p>Loading repositories...</p>
            ) : repos.length === 0 ? (
              <p>No repositories found.</p>
            ) : (
              <ul className="space-y-3">
                {repos.map(repo => (
                  <li key={repo.id} className="flex items-center justify-between p-3 bg-slate-950 rounded-lg border border-slate-800">
                    <div>
                      <span className="font-semibold text-slate-200">{repo.name}</span>
                      <span className="block text-xs text-slate-500">Status: {repo.status}</span>
                    </div>
                    <div className="flex gap-2">
                      <button onClick={() => { setRenamingRepo(repo); setNewName(repo.name); }} className="p-2 text-blue-400 hover:bg-blue-400/10 rounded-lg transition-colors" title="Rename">
                        <Edit2 size={18} />
                      </button>
                      <button onClick={() => handleReindex(repo.id)} className="p-2 text-indigo-400 hover:bg-indigo-400/10 rounded-lg transition-colors" title="Re-index">
                        <RefreshCw size={18} />
                      </button>
                      <button onClick={() => handleDelete(repo.id)} className="p-2 text-red-400 hover:bg-red-400/10 rounded-lg transition-colors" title="Delete">
                        <Trash2 size={18} />
                      </button>
                    </div>
                  </li>
                ))}
              </ul>
            )}
          </div>
        </section>
        
        <section className="p-6 bg-slate-900 border border-slate-800 rounded-2xl">
          <h2 className="text-xl font-semibold mb-4 text-slate-50">Theme Preferences</h2>
          <div className="flex items-center justify-between p-4 bg-slate-950 rounded-lg border border-slate-800">
            <div>
              <span className="font-semibold text-slate-200 block">Light / Dark Mode</span>
              <span className="text-sm text-slate-500">Toggle between light and dark themes</span>
            </div>
            <button
              onClick={() => {
                const isLight = document.documentElement.classList.toggle('light');
                localStorage.setItem('theme', isLight ? 'light' : 'dark');
              }}
              className="px-4 py-2 bg-indigo-600 hover:bg-indigo-700 text-white rounded-lg transition-colors font-medium text-sm shadow-glass"
            >
              Toggle Theme
            </button>
          </div>
        </section>

        <section className="p-6 bg-slate-900 border border-slate-800 rounded-2xl">
          <h2 className="text-xl font-semibold mb-4 text-slate-50">About CodeSense</h2>
          <div className="text-slate-400">Version 1.0.0. Premium AI Developer Platform.</div>
        </section>
      </div>

      {/* Rename Modal */}
      {renamingRepo && (
        <div className="fixed inset-0 bg-black/60 flex items-center justify-center p-4 z-50">
          <div className="bg-slate-900 border border-slate-800 rounded-2xl w-full max-w-md overflow-hidden">
            <div className="flex justify-between items-center p-4 border-b border-slate-800">
              <h3 className="text-lg font-bold text-slate-50">Rename Repository</h3>
              <button onClick={() => setRenamingRepo(null)} className="text-slate-400 hover:text-slate-200 transition-colors">
                <X size={20} />
              </button>
            </div>
            <form onSubmit={handleRename} className="p-6">
              <div className="mb-6">
                <label className="block text-sm font-medium text-slate-300 mb-2">New Name</label>
                <input
                  type="text"
                  value={newName}
                  onChange={(e) => setNewName(e.target.value)}
                  className="w-full bg-slate-950 border border-slate-800 rounded-lg px-4 py-2 text-slate-50 focus:outline-none focus:border-indigo-500 transition-colors"
                  placeholder="e.g. My-Awesome-Repo"
                  autoFocus
                />
              </div>
              <div className="flex justify-end gap-3">
                <button
                  type="button"
                  onClick={() => setRenamingRepo(null)}
                  className="px-4 py-2 text-sm font-medium text-slate-300 hover:text-slate-50 transition-colors"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  className="px-4 py-2 bg-indigo-600 hover:bg-indigo-700 text-white rounded-lg text-sm font-medium transition-colors"
                >
                  Rename
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
}
