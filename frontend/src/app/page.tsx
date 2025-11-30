"use client";

import { useState, useEffect, useMemo } from "react";
import { Project, HomepageService, ScrutinyDrive, HostServiceStatus } from "@/types";
import { Plus, Search, Globe, RefreshCw, ExternalLink } from "lucide-react";
import DocViewer from "@/components/DocViewer";
import Navbar from "@/components/Navbar";
import ProjectCard from "@/components/ProjectCard";
import ProjectModal from "@/components/ProjectModal";

export default function Home() {
  // --- State ---
  const [activeTab, setActiveTab] = useState("projects");
  const [projects, setProjects] = useState<Project[]>([]);
  const [searchQuery, setSearchQuery] = useState("");
  
  // Data States
  const [homepageServices, setHomepageServices] = useState<HomepageService[]>([]);
  const [drives, setDrives] = useState<ScrutinyDrive[]>([]);
  const [hostServices, setHostServices] = useState<HostServiceStatus[]>([]);
  const [statuses, setStatuses] = useState<Record<string, boolean | null>>({});
  
  // UI States
  const [newPath, setNewPath] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  
  // Modals
  const [selectedProject, setSelectedProject] = useState<Project | null>(null);
  const [viewingDoc, setViewingDoc] = useState<{path: string, name: string} | null>(null);
  const [isAddModalOpen, setIsAddModalOpen] = useState(false);

  // --- Helpers ---
  const formatUrl = (url: string) => {
    if (typeof window === 'undefined' || !url) return url;
    try {
        const urlObj = new URL(url);
        if (urlObj.hostname === 'localhost' || urlObj.hostname === '127.0.0.1') {
            urlObj.hostname = window.location.hostname;
            return urlObj.toString();
        }
        return url;
    } catch {
        return url;
    }
  };

  const copyToClipboard = async (text: string) => {
    if (!navigator.clipboard) {
       const textArea = document.createElement("textarea");
       textArea.value = text;
       textArea.style.position = "fixed"; 
       document.body.appendChild(textArea);
       textArea.focus();
       textArea.select();
       try {
         document.execCommand('copy');
         document.body.removeChild(textArea);
         return Promise.resolve();
       } catch (err) {
         document.body.removeChild(textArea);
         return Promise.reject(err);
       }
    }
    return navigator.clipboard.writeText(text);
  };

  // --- Fetchers ---
  const fetchProjects = async () => {
    setLoading(true);
    try {
      const res = await fetch("/api/projects");
      if (res.ok) setProjects(await res.json());
    } catch (err: any) { setError(err.message); } 
    finally { setLoading(false); }
  };

  const fetchHomepage = async () => {
    try {
      const res = await fetch("/api/homepage");
      if (res.ok) {
        const data = await res.json();
        setHomepageServices(data.services || []);
      }
    } catch (e) { console.error(e); }
  };

  const fetchDrives = async () => {
    try {
      const res = await fetch("/api/scrutiny");
      if (res.ok) {
        const data = await res.json();
        setDrives(data.drives || []);
      }
    } catch (e) { console.error(e); }
  };

  const fetchHostStatus = async () => {
    try {
      const res = await fetch("/api/host-status");
      if (res.ok) {
        const data = await res.json();
        setHostServices(data.services || []);
      }
    } catch (e) { console.error(e); }
  };

  // --- Actions ---
  const handleAdd = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!newPath) return;
    setLoading(true);
    try {
      const res = await fetch("/api/projects", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ path: newPath }),
      });
      if (res.ok) {
        setNewPath("");
        setIsAddModalOpen(false); // Close modal on success
        fetchProjects();
      } else {
        const err = await res.json();
        setError(err.detail || "Failed to add");
      }
    } catch (error: any) { setError(error.message); } 
    finally { setLoading(false); }
  };

  const handleDelete = async (projectId: string) => {
    setLoading(true);
    try {
      const res = await fetch(`/api/projects/${projectId}`, { method: "DELETE" });
      if (res.ok) {
        fetchProjects();
      } else {
        const err = await res.json();
        setError(err.detail || "Failed to delete");
      }
    } catch (error: any) { setError(error.message); } 
    finally { setLoading(false); }
  };

  const launch = async (path: string, type: string) => {
    try {
      await fetch("/api/launch", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ project_path: path, launch_type: type }),
      });
    } catch (e) { console.error(e); }
  };

  // --- Effects ---
  useEffect(() => {
    fetchProjects();
    fetchHomepage();
    fetchDrives();
    fetchHostStatus();
  }, []);

  useEffect(() => {
    if (projects.length === 0) return;
    
    const checkStatuses = async () => {
      const newStatuses: Record<string, boolean | null> = {};
      const checks = projects.map(async (p) => {
        if (!p.frontend_url) return;
        try {
            // Use local relative URL to hit backend proxy
            const res = await fetch(`/api/monitor/status?url=${encodeURIComponent(p.frontend_url)}`);
            newStatuses[p.id] = res.ok ? (await res.json()).is_up : false;
        } catch { newStatuses[p.id] = false; }
      });
      await Promise.all(checks);
      setStatuses(prev => ({ ...prev, ...newStatuses }));
    };

    checkStatuses();
    const interval = setInterval(checkStatuses, 30000);
    return () => clearInterval(interval);
  }, [projects]);

  // --- Filtering ---
  const filteredProjects = useMemo(() => {
    const q = searchQuery.toLowerCase();
    return projects.filter(p => 
        p.name.toLowerCase().includes(q) || 
        p.path.toLowerCase().includes(q) || 
        p.tags.some(t => t.toLowerCase().includes(q))
    );
  }, [projects, searchQuery]);


  return (
    <div className="min-h-screen bg-slate-950 text-slate-200 font-sans">
      <Navbar activeTab={activeTab} onTabChange={setActiveTab} />

      <main className="max-w-7xl mx-auto p-4 md:p-8">
        
        {error && (
          <div className="mb-6 bg-red-900/30 text-red-400 border border-red-900 p-3 rounded-md text-sm flex justify-between items-center">
            <span>{error}</span>
            <button onClick={() => setError(null)} className="hover:text-white">Dismiss</button>
          </div>
        )}

        {/* --- PROJECTS TAB --- */}
        {activeTab === 'projects' && (
            <div className="space-y-6">
                {/* Controls Bar */}
                <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 bg-slate-900/50 p-4 rounded-xl border border-slate-800 sticky top-20 z-30 backdrop-blur-md">
                    
                    {/* Search */}
                    <div className="relative flex-1 max-w-md">
                        <Search className="absolute left-3 top-1/2 -translate-y-1/2 text-slate-500" size={18} />
                        <input 
                            type="text" 
                            placeholder="Search projects..."
                            value={searchQuery}
                            onChange={(e) => setSearchQuery(e.target.value)}
                            className="w-full bg-slate-950 border border-slate-800 rounded-lg pl-10 pr-4 py-2.5 focus:ring-2 focus:ring-indigo-500 focus:outline-none text-sm placeholder-slate-600"
                        />
                    </div>

                    {/* Actions */}
                    <div className="flex items-center gap-2 w-full md:w-auto justify-end">
                         <button 
                            onClick={() => setIsAddModalOpen(true)}
                            className="bg-indigo-600 hover:bg-indigo-500 text-white p-2.5 rounded-lg transition-all shadow-lg shadow-indigo-900/20 flex items-center gap-2"
                         >
                            <Plus size={18} />
                            <span className="font-medium text-sm hidden sm:block">Add Project</span>
                         </button>
                         <button onClick={fetchProjects} className="p-2.5 bg-slate-800 hover:bg-slate-700 rounded-lg text-slate-400 transition-colors" title="Refresh">
                            <RefreshCw size={18} />
                         </button>
                    </div>
                </div>

                {/* Project Grid */}
                <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-4">
                    {filteredProjects.map(project => (
                        <ProjectCard 
                            key={project.id}
                            project={project}
                            status={statuses[project.id] ?? null}
                            onClick={() => setSelectedProject(project)}
                            onLaunch={launch}
                            formatUrl={formatUrl}
                        />
                    ))}
                </div>
                {filteredProjects.length === 0 && (
                    <div className="text-center py-20 text-slate-500">
                        No projects found matching &quot;{searchQuery}&quot;
                    </div>
                )}
            </div>
        )}

        {/* --- DASHBOARD TAB --- */}
        {activeTab === 'dashboard' && (
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
                {homepageServices.map((svc) => (
                  <div key={svc.name} className="p-5 rounded-xl border border-slate-800 bg-slate-900 shadow-sm hover:border-slate-700 transition-all">
                    <div className="flex items-start gap-3 mb-4">
                      {svc.icons[0] && <img src={svc.icons[0]} className="w-10 h-10 object-contain bg-slate-800 p-1.5 rounded-lg" />}
                      <div>
                        <div className="text-white font-semibold text-lg">{svc.name}</div>
                        <div className="text-xs text-slate-500 mt-1 line-clamp-2">{svc.snippet}</div>
                      </div>
                    </div>
                    <div className="flex flex-wrap gap-2 mb-4">
                      {svc.metrics.map((m, i) => (
                        <span key={i} className="px-2 py-1 rounded bg-slate-800 text-slate-300 text-xs">
                          <span className="font-bold text-white">{m.value}</span> {m.label}
                        </span>
                      ))}
                    </div>
                    <div className="flex flex-wrap gap-2 mt-auto">
                      {svc.links.slice(0, 3).map((href, idx) => (
                        <a
                          key={idx}
                          href={formatUrl(href)}
                          target="_blank"
                          className="flex items-center gap-1 text-xs px-3 py-1.5 rounded bg-indigo-900/20 text-indigo-400 hover:bg-indigo-600 hover:text-white transition-colors border border-indigo-500/20"
                        >
                          {idx === 0 ? "Launch" : `Link ${idx + 1}`}
                          <ExternalLink size={12} />
                        </a>
                      ))}
                    </div>
                  </div>
                ))}
            </div>
        )}

        {/* --- SCRUTINY TAB --- */}
        {activeTab === 'scrutiny' && (
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
                 {drives.map((d) => (
                  <div key={d.device} className="p-5 rounded-xl border border-slate-800 bg-slate-900 shadow-sm">
                    <div className="flex justify-between items-start mb-4">
                        <div>
                            <div className="text-white font-semibold text-lg">{d.device}</div>
                            <div className="text-xs text-slate-500 font-mono">{d.bus_model}</div>
                        </div>
                        <span className={`text-xs px-2 py-1 rounded font-medium ${
                            d.status.toLowerCase() === "passed" ? "bg-emerald-900/30 text-emerald-400 border border-emerald-900/50" : "bg-red-900/30 text-red-400 border border-red-900/50"
                        }`}>
                            {d.status}
                        </span>
                    </div>
                    <div className="grid grid-cols-2 gap-2 text-sm">
                        <div className="p-2 rounded bg-slate-800/50">
                            <span className="text-slate-500 text-xs block">Temperature</span>
                            <span className="text-slate-200">{d.temp}</span>
                        </div>
                        <div className="p-2 rounded bg-slate-800/50">
                            <span className="text-slate-500 text-xs block">Capacity</span>
                            <span className="text-slate-200">{d.capacity}</span>
                        </div>
                        <div className="col-span-2 p-2 rounded bg-slate-800/50">
                            <span className="text-slate-500 text-xs block">Power On Hours</span>
                            <span className="text-slate-200">{d.powered_on}</span>
                        </div>
                    </div>
                    <div className="mt-4 text-[10px] text-slate-600 text-right">Updated: {d.last_updated}</div>
                  </div>
                 ))}
            </div>
        )}

        {/* --- HOST TAB --- */}
        {activeTab === 'host' && (
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
                 {hostServices.map((svc) => (
                  <div key={svc.name} className="flex items-center justify-between p-4 rounded-xl border border-slate-800 bg-slate-900 shadow-sm">
                     <div>
                        <div className="text-white font-semibold">{svc.name}</div>
                        <div className="text-xs text-slate-500 mt-1">
                            {svc.details && JSON.stringify(svc.details).replace(/[{}"\\]/g, ' ')}
                        </div>
                     </div>
                     <div className={`w-3 h-3 rounded-full shadow-sm ${
                        svc.state === 'running' ? 'bg-emerald-500 shadow-emerald-900/50' : 'bg-red-500 shadow-red-900/50'
                     }`} title={svc.state} />
                  </div>
                 ))}
            </div>
        )}

      </main>
      
      {/* --- GLOBAL MODALS --- */}
      
      {/* Add Project Modal */}
      {isAddModalOpen && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/60 backdrop-blur-sm animate-in fade-in" onClick={() => setIsAddModalOpen(false)}>
            <div className="w-full max-w-lg bg-slate-900 border border-slate-800 rounded-xl p-6 shadow-2xl animate-in zoom-in-95" onClick={e => e.stopPropagation()}>
                <h2 className="text-xl font-bold text-white mb-4">Add New Project</h2>
                <form onSubmit={handleAdd} className="space-y-4">
                    <div>
                        <label className="block text-sm font-medium text-slate-400 mb-1">Project Path (Linux/WSL)</label>
                        <input
                            type="text"
                            value={newPath}
                            onChange={(e) => setNewPath(e.target.value)}
                            placeholder="/mnt/d/projects/my-app"
                            className="w-full bg-slate-950 border border-slate-800 rounded-lg px-4 py-3 focus:outline-none focus:ring-2 focus:ring-indigo-500 text-slate-200 placeholder-slate-600 font-mono text-sm"
                            autoFocus
                        />
                    </div>
                    <div className="flex justify-end gap-3">
                        <button 
                            type="button" 
                            onClick={() => setIsAddModalOpen(false)}
                            className="px-4 py-2 text-slate-400 hover:text-white transition-colors"
                        >
                            Cancel
                        </button>
                        <button 
                            type="submit" 
                            disabled={loading}
                            className="bg-indigo-600 hover:bg-indigo-500 text-white px-6 py-2 rounded-lg font-medium transition-colors disabled:opacity-50 flex items-center gap-2"
                        >
                            {loading ? "Scanning..." : "Add Project"}
                        </button>
                    </div>
                </form>
            </div>
        </div>
      )}

      {selectedProject && (
        <ProjectModal 
            project={selectedProject} 
            isOpen={!!selectedProject} 
            onClose={() => setSelectedProject(null)}
            onLaunch={launch}
            onViewDoc={setViewingDoc}
            onUpdate={(updated) => {
                setSelectedProject(updated);
                setProjects(prev => prev.map(p => p.id === updated.id ? updated : p));
            }}
            onDelete={() => {
                handleDelete(selectedProject.id);
                setSelectedProject(null);
            }}
            formatUrl={formatUrl}
            status={statuses[selectedProject.id] ?? null}
        />
      )}

      <DocViewer 
        isOpen={!!viewingDoc} 
        onClose={() => setViewingDoc(null)} 
        filePath={viewingDoc?.path ?? null}
        fileName={viewingDoc?.name ?? null}
      />
    </div>
  );
}
