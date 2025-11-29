"use client";

import { useState, useEffect } from "react";
import { Project } from "@/types";
import { Folder, Terminal, Code2, FileText, Plus, RefreshCw, Trash2, Command, Link, ExternalLink } from "lucide-react";

export default function Home() {
  const [projects, setProjects] = useState<Project[]>([]);
  const [newPath, setNewPath] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const fetchProjects = async () => {
    setLoading(true);
    setError(null);
    try {
      const res = await fetch("/api/projects");
      if (!res.ok) {
        throw new Error(`HTTP error! status: ${res.status}`);
      }
      const data = await res.json();
      setProjects(data);
    } catch (error: any) {
      console.error("Failed to fetch projects:", error);
      setError(error.message || "Failed to fetch projects.");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchProjects();
  }, []);

  const handleAdd = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!newPath) return;
    setLoading(true);
    setError(null);
    try {
      const res = await fetch("/api/projects", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ path: newPath }),
      });
      if (res.ok) {
        setNewPath("");
        fetchProjects();
      } else {
        const err = await res.json();
        setError(err.detail || "Failed to add project.");
      }
    } catch (error: any) {
      console.error("Add failed", error);
      setError(error.message || "Failed to add project.");
    } finally {
      setLoading(false);
    }
  };

  const handleDelete = async (projectId: string) => {
    setLoading(true);
    setError(null);
    try {
      const res = await fetch(`/api/projects/${projectId}`, {
        method: "DELETE",
      });
      if (res.ok) {
        fetchProjects();
      } else {
        const err = await res.json();
        setError(err.detail || "Failed to delete project.");
      }
    } catch (error: any) {
      console.error("Delete failed", error);
      setError(error.message || "Failed to delete project.");
    } finally {
      setLoading(false);
    }
  };

  const launch = async (path: string, type: string) => {
    setError(null);
    try {
      const res = await fetch("/api/launch", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ project_path: path, launch_type: type }),
      });
      if (!res.ok) {
        const err = await res.json();
        setError(err.detail || "Failed to launch.");
      }
    } catch (error: any) {
      console.error("Launch failed", error);
      setError(error.message || "Failed to launch.");
    }
  };

  return (
    <main className="min-h-screen bg-slate-950 text-slate-200 p-8 font-sans">
      <div className="max-w-6xl mx-auto space-y-8">
        
        {/* Header */}
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 bg-indigo-500 rounded-lg flex items-center justify-center">
              <Terminal className="text-white" />
            </div>
            <h1 className="text-2xl font-bold text-white tracking-tight">Mission Control</h1>
          </div>
          <button onClick={fetchProjects} className="p-2 hover:bg-slate-800 rounded-full transition-colors">
            <RefreshCw size={20} className="text-slate-400" />
          </button>
        </div>

        {/* Add Project */}
        <form onSubmit={handleAdd} className="flex gap-4 bg-slate-900/50 p-4 rounded-xl border border-slate-800">
          <input
            type="text"
            value={newPath}
            onChange={(e) => setNewPath(e.target.value)}
            placeholder="/mnt/d/projects/..."
            className="flex-1 bg-slate-950 border border-slate-800 rounded-lg px-4 py-3 focus:outline-none focus:ring-2 focus:ring-indigo-500 text-slate-200 placeholder-slate-600 font-mono text-sm"
          />
          <button 
            disabled={loading}
            className="bg-indigo-600 hover:bg-indigo-500 text-white px-6 py-3 rounded-lg font-medium flex items-center gap-2 transition-all disabled:opacity-50"
          >
            <Plus size={18} />
            {loading ? "Scanning..." : "Add Project"}
          </button>
        </form>

        {error && (
          <div className="bg-red-900/30 text-red-400 border border-red-900 p-3 rounded-md text-sm">
            Error: {error}
          </div>
        )}

        {/* Grid */}
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
          {projects.map((project) => (
            <div key={project.id} className="bg-slate-900 border border-slate-800 rounded-xl p-6 hover:border-slate-700 transition-all group shadow-sm relative">
              {/* Delete Button */}
              <button 
                onClick={() => handleDelete(project.id)}
                className="absolute top-3 right-3 p-1 rounded-full text-slate-500 hover:text-red-500 hover:bg-slate-800 transition-colors"
                title="Remove Project"
              >
                <Trash2 size={16} />
              </button>

              {/* Card Header */}
              <div className="flex justify-between items-start mb-4">
                <div>
                  <h3 className="text-lg font-semibold text-white mb-1">{project.name}</h3>
                  <p className="text-xs text-slate-500 font-mono truncate max-w-[200px]" title={project.path}>
                    {project.path}
                  </p>
                </div>
                <span className={`px-2 py-1 rounded text-xs font-medium uppercase tracking-wider ${
                  project.type === 'node' ? 'bg-green-900/30 text-green-400 border border-green-900' :
                  project.type === 'python' ? 'bg-yellow-900/30 text-yellow-400 border border-yellow-900' :
                  'bg-slate-800 text-slate-400 border border-slate-700'
                }`}>
                  {project.type}
                </span>
              </div>

              {/* Docs / Metadata */}
              <div className="space-y-2 mb-6">
                {project.docs.map((doc) => (
                  <div key={doc.name} className="flex items-center gap-2 text-xs text-slate-400">
                    {doc.type === 'link' ? (
                       <a 
                         href={doc.path}
                         target="_blank"
                         rel="noopener noreferrer"
                         className="flex items-center gap-1 text-emerald-400 hover:text-emerald-300 hover:underline"
                       >
                         <Link size={12} />
                         <span className="font-mono">{doc.name}</span>
                       </a>
                    ) : doc.type === 'openapi' || doc.type === 'swagger' ? (
                       <button 
                         onClick={() => launch(doc.path, 'vscode')} 
                         className="flex items-center gap-1 text-indigo-400 hover:text-indigo-300 hover:underline"
                       >
                         <ExternalLink size={12} />
                         <span className="font-mono">{doc.name}</span>
                       </button>
                    ) : (
                      <>
                        <FileText size={12} />
                        <span>{doc.name}</span>
                      </>
                    )}
                  </div>
                ))}
                {project.git_status && (
                  <div className="flex items-center gap-2 text-xs text-slate-400">
                     <div className="w-2 h-2 rounded-full bg-green-500"></div>
                     <span>Git: {project.git_status}</span>
                  </div>
                )}
              </div>

              {/* Actions */}
              <div className="grid grid-cols-4 gap-2">
                <button 
                  onClick={() => launch(project.vscode_workspace_file || project.path, 'vscode')}
                  className="flex flex-col items-center justify-center gap-1 p-2 rounded-lg bg-slate-800/50 hover:bg-indigo-600/20 hover:text-indigo-400 text-slate-400 transition-all border border-transparent hover:border-indigo-500/30"
                >
                  <Code2 size={18} />
                  <span className="text-[10px] font-medium">Code</span>
                </button>
                <button 
                  onClick={() => launch(project.path, 'terminal')}
                  className="flex flex-col items-center justify-center gap-1 p-2 rounded-lg bg-slate-800/50 hover:bg-emerald-600/20 hover:text-emerald-400 text-slate-400 transition-all border border-transparent hover:border-emerald-500/30"
                >
                  <Terminal size={18} />
                  <span className="text-[10px] font-medium">Terminal</span>
                </button>
                <button 
                  onClick={() => launch(project.path, 'wsl')}
                  className="flex flex-col items-center justify-center gap-1 p-2 rounded-lg bg-slate-800/50 hover:bg-orange-600/20 hover:text-orange-400 text-slate-400 transition-all border border-transparent hover:border-orange-500/30"
                >
                  <Command size={18} />
                  <span className="text-[10px] font-medium">WSL</span>
                </button>
                <button 
                  onClick={() => launch(project.path, 'explorer')}
                  className="flex flex-col items-center justify-center gap-1 p-2 rounded-lg bg-slate-800/50 hover:bg-blue-600/20 hover:text-blue-400 text-slate-400 transition-all border border-transparent hover:border-blue-500/30"
                >
                  <Folder size={18} />
                  <span className="text-[10px] font-medium">Explorer</span>
                </button>
              </div>

            </div>
          ))}
        </div>
      </div>
    </main>
  );
}