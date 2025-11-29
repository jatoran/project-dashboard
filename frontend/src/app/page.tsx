"use client";

import { useState, useEffect } from "react";
import { Project } from "@/types";
import { Folder, Terminal, Code2, FileText, Plus, RefreshCw, Trash2, Command, Link, ExternalLink, Copy, Check, Globe } from "lucide-react";
import DocViewer from "@/components/DocViewer";

export default function Home() {
  const [projects, setProjects] = useState<Project[]>([]);
  const [newPath, setNewPath] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [viewingDoc, setViewingDoc] = useState<{path: string, name: string} | null>(null);
  const [copiedDocContentPath, setCopiedDocContentPath] = useState<string | null>(null); // To track which doc's content was copied
  const [statuses, setStatuses] = useState<Record<string, boolean | null>>({});

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

  const handleCopyDocContent = async (filePath: string) => {
    try {
        const res = await fetch(`/api/files/content?path=${encodeURIComponent(filePath)}`);
        if (!res.ok) throw new Error("Failed to load file content for copying.");
        const data = await res.json();
        await navigator.clipboard.writeText(data.content);
        setCopiedDocContentPath(filePath);
        setTimeout(() => setCopiedDocContentPath(null), 2000);
    } catch (err: any) {
        console.error("Error copying doc content:", err);
        setError("Failed to copy document content.");
    }
  };

  const handleCopyProjectPath = async (path: string) => {
    try {
        await navigator.clipboard.writeText(path);
    } catch (err) {
        console.error("Error copying project path:", err);
        setError("Failed to copy project path.");
    }
  };

  useEffect(() => {
    fetchProjects();
  }, []);

  // Polling Logic
  useEffect(() => {
    if (projects.length === 0) return;

    const checkStatuses = async () => {
      const newStatuses: Record<string, boolean | null> = {};
      
      // Create a list of promises to check all projects in parallel
      const checks = projects.map(async (project) => {
        if (!project.frontend_url) return;
        
        try {
            const res = await fetch(`/api/monitor/status?url=${encodeURIComponent(project.frontend_url)}`);
            if (res.ok) {
                const data = await res.json();
                newStatuses[project.id] = data.is_up;
            } else {
                newStatuses[project.id] = false;
            }
        } catch {
            newStatuses[project.id] = false;
        }
      });

      await Promise.all(checks);
      setStatuses(prev => ({ ...prev, ...newStatuses }));
    };

    // Check immediately
    checkStatuses();

    // Then poll every 30s
    const interval = setInterval(checkStatuses, 30000);
    return () => clearInterval(interval);
  }, [projects]);

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
            <h1 className="text-2xl font-bold text-white tracking-tight">Project Dashboard</h1>
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
                <div 
                  className="cursor-pointer group relative" 
                  onClick={() => handleCopyProjectPath(project.path)}
                  title="Click to copy path"
                >
                  <h3 className="text-lg font-semibold text-white mb-1">{project.name}</h3>
                  <p className="text-xs text-slate-500 font-mono truncate max-w-[200px] group-hover:text-slate-400 transition-colors">
                    {project.path}
                  </p>
                </div>
                {/* Tags */}
                <div className="flex flex-wrap gap-1 justify-end max-w-[50%]">
                   {project.tags.slice(0, 3).map(tag => (
                      <span key={tag} className={`px-2 py-0.5 rounded text-[10px] font-medium uppercase tracking-wider border ${
                        tag === 'node' || tag === 'javascript' || tag === 'typescript' ? 'bg-yellow-900/20 text-yellow-400 border-yellow-900/50' :
                        tag === 'python' || tag === 'django' || tag === 'flask' ? 'bg-blue-900/20 text-blue-400 border-blue-900/50' :
                        tag === 'react' || tag === 'next.js' || tag === 'vue' ? 'bg-cyan-900/20 text-cyan-400 border-cyan-900/50' :
                        tag === 'docker' ? 'bg-sky-900/20 text-sky-400 border-sky-900/50' :
                        tag === 'rust' ? 'bg-orange-900/20 text-orange-400 border-orange-900/50' :
                        tag === 'fastapi' ? 'bg-teal-900/20 text-teal-400 border-teal-900/50' :
                        'bg-slate-800 text-slate-400 border-slate-700'
                      }`}>
                        {tag}
                      </span>
                   ))}
                   {project.tags.length > 3 && (
                     <span className="px-1.5 py-0.5 rounded text-[10px] font-medium bg-slate-800 text-slate-500 border border-slate-700">
                       +{project.tags.length - 3}
                     </span>
                   )}
                </div>
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
                    ) : doc.type === 'markdown' ? (
                        <div className="flex items-center justify-between w-full gap-2">
                           <button 
                             onClick={() => setViewingDoc({path: doc.path, name: doc.name})}
                             className="flex items-center gap-1 text-blue-400 hover:text-blue-300 hover:underline truncate flex-1 min-w-0 text-left"
                           >
                             <FileText size={12} className="shrink-0" />
                             <span className="font-mono truncate">{doc.name}</span>
                           </button>
                           <button
                             onClick={(e) => {
                               e.stopPropagation();
                               handleCopyDocContent(doc.path);
                             }}
                             className="text-slate-500 hover:text-white hover:bg-slate-800 rounded p-1.5 transition-all z-10 shrink-0"
                             title="Copy content"
                           >
                             {copiedDocContentPath === doc.path ? (
                               <Check size={14} className="text-green-400 pointer-events-none" />
                             ) : (
                               <Copy size={14} className="pointer-events-none" />
                             )}
                           </button>
                        </div>
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
              <div className="grid grid-cols-5 gap-2">
                <button 
                  onClick={() => launch(project.vscode_workspace_file || project.path, 'vscode')}
                  className="flex flex-col items-center justify-center gap-1 p-2 rounded-lg bg-slate-800/50 hover:bg-indigo-600/20 hover:text-indigo-400 text-slate-400 transition-all border border-transparent hover:border-indigo-500/30"
                  title="Open in VS Code"
                >
                  <Code2 size={18} />
                  <span className="text-[10px] font-medium">Code</span>
                </button>
                <button 
                  onClick={() => launch(project.path, 'terminal')}
                  className="flex flex-col items-center justify-center gap-1 p-2 rounded-lg bg-slate-800/50 hover:bg-emerald-600/20 hover:text-emerald-400 text-slate-400 transition-all border border-transparent hover:border-emerald-500/30"
                  title="Open Terminal"
                >
                  <Terminal size={18} />
                  <span className="text-[10px] font-medium">Term</span>
                </button>
                <button 
                  onClick={() => launch(project.path, 'wsl')}
                  className="flex flex-col items-center justify-center gap-1 p-2 rounded-lg bg-slate-800/50 hover:bg-orange-600/20 hover:text-orange-400 text-slate-400 transition-all border border-transparent hover:border-orange-500/30"
                  title="Open WSL Terminal"
                >
                  <Command size={18} />
                  <span className="text-[10px] font-medium">WSL</span>
                </button>
                <button 
                  onClick={() => launch(project.path, 'explorer')}
                  className="flex flex-col items-center justify-center gap-1 p-2 rounded-lg bg-slate-800/50 hover:bg-blue-600/20 hover:text-blue-400 text-slate-400 transition-all border border-transparent hover:border-blue-500/30"
                  title="Open File Explorer"
                >
                  <Folder size={18} />
                  <span className="text-[10px] font-medium">Files</span>
                </button>

                 {/* App Button - Only renders if URL exists, but takes up 5th slot */}
                 {project.frontend_url ? (
                     <a 
                       href={project.frontend_url}
                       target="_blank"
                       rel="noopener noreferrer"
                       className="flex flex-col items-center justify-center gap-1 p-2 rounded-lg bg-slate-800/50 hover:bg-cyan-600/20 hover:text-cyan-400 text-slate-400 transition-all border border-transparent hover:border-cyan-500/30 relative"
                       title="Open Web App"
                     >
                        <div className={`absolute top-1 right-1 w-1.5 h-1.5 rounded-full ${
                            statuses[project.id] === true ? "bg-green-500 shadow-[0_0_6px_rgba(34,197,94,0.6)]" : 
                            statuses[project.id] === false ? "bg-red-500" : 
                            "bg-slate-600"
                        }`} />
                        <Globe size={18} />
                        <span className="text-[10px] font-medium">App</span>
                     </a>
                ) : (
                    <div className="bg-slate-900/20 rounded-lg border border-transparent border-slate-800/20"></div>
                )}
              </div>

            </div>
          ))}
        </div>
      </div>
      
      <DocViewer 
        isOpen={!!viewingDoc} 
        onClose={() => setViewingDoc(null)} 
        filePath={viewingDoc?.path ?? null}
        fileName={viewingDoc?.name ?? null}
      />
    </main>
  );
}