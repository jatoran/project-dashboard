"use client";

import { useState, useEffect, useMemo, useCallback, useRef } from "react";
import { Project, Platform, SortMode } from "@/types";
import { Plus, Search, RefreshCw, ExternalLink, Globe, Trash2, ArrowUpDown } from "lucide-react";
import DocViewer from "@/components/DocViewer";
import Navbar from "@/components/Navbar";
import ProjectCard from "@/components/ProjectCard";
import ProjectModal from "@/components/ProjectModal";
import {
  DndContext,
  closestCenter,
  KeyboardSensor,
  PointerSensor,
  useSensor,
  useSensors,
  DragEndEvent,
} from '@dnd-kit/core';
import {
  arrayMove,
  SortableContext,
  sortableKeyboardCoordinates,
  rectSortingStrategy,
} from '@dnd-kit/sortable';

export default function Home() {
  // --- State ---
  const [activeTab, setActiveTab] = useState("projects");
  const [projects, setProjects] = useState<Project[]>([]);
  const [searchQuery, setSearchQuery] = useState("");
  const [sortMode, setSortMode] = useState<SortMode>('custom');
  const searchInputRef = useRef<HTMLInputElement>(null);

  // Data States
  const [statuses, setStatuses] = useState<Record<string, boolean | null>>({});
  const [platforms, setPlatforms] = useState<Platform[]>([]);

  // UI States
  const [newPath, setNewPath] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  // Modals
  const [selectedProject, setSelectedProject] = useState<Project | null>(null);
  const [viewingDoc, setViewingDoc] = useState<{ path: string, name: string } | null>(null);
  const [isAddModalOpen, setIsAddModalOpen] = useState(false);

  // --- Helpers ---
  const formatUrl = (url: string, project?: Project) => {
    if (typeof window === 'undefined' || !url) return url;
    try {
      const urlObj = new URL(url, window.location.origin);
      const feOverride = project?.frontend_port_override || undefined;
      const beOverride = project?.backend_port_override || project?.backend_port || undefined;
      const isLocalHost = ['localhost', '127.0.0.1', window.location.hostname].includes(urlObj.hostname);
      const pathHint = urlObj.pathname.toLowerCase();
      const looksBackend = pathHint.includes("api") || pathHint.includes("swagger") || pathHint.includes("redoc") || pathHint.includes("openapi");

      if (isLocalHost) {
        urlObj.hostname = window.location.hostname;
        if (looksBackend && beOverride) {
          urlObj.port = beOverride;
        } else if (!looksBackend && feOverride) {
          urlObj.port = feOverride;
        }
        // If ports are defaults, swap to overrides
        if (urlObj.port === "37452" && feOverride) urlObj.port = feOverride;
        if (urlObj.port === "37453" && beOverride) urlObj.port = beOverride;
      }
      return urlObj.toString();
    } catch {
      return url;
    }
  };

  // --- Fetchers ---
  const fetchProjects = async () => {
    setLoading(true);
    try {
      const res = await fetch("/api/projects");
      if (res.ok) setProjects(await res.json());
    } catch (err) {
      const message = err instanceof Error ? err.message : "Failed to load projects";
      setError(message);
    }
    finally { setLoading(false); }
  };

  const fetchPlatforms = async () => {
    try {
      const res = await fetch("/api/platforms");
      if (res.ok) {
        const data = await res.json();
        setPlatforms(data || []);
      }
    } catch (e) { console.error(e); }
  };

  const addPlatform = async (name: string, url: string) => {
    try {
      const res = await fetch("/api/platforms", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ name, url }),
      });
      if (res.ok) {
        await fetchPlatforms();
        return true;
      }
    } catch (e) { console.error(e); }
    return false;
  };

  const deletePlatform = async (id: string) => {
    try {
      const res = await fetch(`/api/platforms/${id}`, { method: "DELETE" });
      if (res.ok) {
        await fetchPlatforms();
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
        setIsAddModalOpen(false);
        fetchProjects();
      } else {
        const err = await res.json();
        setError(err.detail || "Failed to add");
      }
    } catch (error) {
      const message = error instanceof Error ? error.message : "Failed to add project";
      setError(message);
    }
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
    } catch (error) {
      const message = error instanceof Error ? error.message : "Failed to delete project";
      setError(message);
    }
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
    fetchPlatforms();
  }, []);

  // Ctrl+F to focus search input
  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      if ((e.ctrlKey || e.metaKey) && e.key === 'f') {
        e.preventDefault();
        searchInputRef.current?.focus();
        searchInputRef.current?.select();
      }
    };
    window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, []);

  // Auto-clear search after 10 seconds of inactivity
  useEffect(() => {
    if (!searchQuery) return;
    const timer = setTimeout(() => setSearchQuery(''), 10000);
    return () => clearTimeout(timer);
  }, [searchQuery]);

  // Check project frontend statuses
  useEffect(() => {
    if (projects.length === 0) return;

    const checkStatuses = async () => {
      const newStatuses: Record<string, boolean | null> = {};
      const checks = projects.map(async (p) => {
        if (!p.frontend_url) return;
        try {
          const targetUrl = formatUrl(p.frontend_url, p);
          const res = await fetch(`/api/monitor/status?url=${encodeURIComponent(targetUrl)}`);
          newStatuses[p.id] = res.ok ? (await res.json()).is_up : false;
        } catch { newStatuses[p.id] = false; }
      });
      await Promise.all(checks);
      setStatuses(prev => ({ ...prev, ...newStatuses }));
    };

    checkStatuses();
    const interval = setInterval(checkStatuses, 60000);
    return () => clearInterval(interval);
  }, [projects]);

  // --- Filtering & Sorting ---
  const sortedProjects = useMemo(() => {
    let sorted = [...projects];
    switch (sortMode) {
      case 'name':
        sorted.sort((a, b) => a.name.localeCompare(b.name));
        break;
      case 'custom':
        sorted.sort((a, b) => (a.position ?? 999) - (b.position ?? 999));
        break;
      default:
        break;
    }
    return sorted;
  }, [projects, sortMode]);

  const filteredProjects = useMemo(() => {
    const q = searchQuery.toLowerCase();
    return sortedProjects.filter(p =>
      p.name.toLowerCase().includes(q) ||
      p.path.toLowerCase().includes(q) ||
      p.tags.some(t => t.toLowerCase().includes(q))
    );
  }, [sortedProjects, searchQuery]);

  // --- Drag and Drop ---
  const sensors = useSensors(
    useSensor(PointerSensor, { activationConstraint: { distance: 8 } }),
    useSensor(KeyboardSensor, { coordinateGetter: sortableKeyboardCoordinates })
  );

  const handleDragEnd = async (event: DragEndEvent) => {
    const { active, over } = event;
    if (!over || active.id === over.id) return;

    setSortMode('custom');

    const oldIndex = sortedProjects.findIndex(p => p.id === active.id);
    const newIndex = sortedProjects.findIndex(p => p.id === over.id);

    if (oldIndex !== -1 && newIndex !== -1) {
      const reordered = arrayMove(sortedProjects, oldIndex, newIndex);
      const newOrder = reordered.map(p => p.id);

      setProjects(reordered.map((p, i) => ({ ...p, position: i })));

      try {
        await fetch('/api/projects/reorder', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ order: newOrder }),
        });
      } catch (e) {
        console.error('Failed to persist order:', e);
      }
    }
  };

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
                  ref={searchInputRef}
                  type="text"
                  placeholder="Search projects... (Ctrl+F)"
                  value={searchQuery}
                  onChange={(e) => setSearchQuery(e.target.value)}
                  className="w-full bg-slate-950 border border-slate-800 rounded-lg pl-10 pr-4 py-2.5 focus:ring-2 focus:ring-indigo-500 focus:outline-none text-sm placeholder-slate-600"
                />
              </div>

              {/* Sort Dropdown */}
              <div className="flex items-center gap-2">
                <ArrowUpDown size={14} className="text-slate-500" />
                <select
                  value={sortMode}
                  onChange={(e) => setSortMode(e.target.value as SortMode)}
                  className="bg-slate-800 border border-slate-700 rounded-lg px-3 py-2 text-sm text-slate-300 focus:ring-2 focus:ring-indigo-500 focus:outline-none"
                >
                  <option value="custom">Custom</option>
                  <option value="name">Name</option>
                </select>
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

            {/* Project Grid with Drag & Drop */}
            <DndContext
              sensors={sensors}
              collisionDetection={closestCenter}
              onDragEnd={handleDragEnd}
            >
              <SortableContext
                items={filteredProjects.map(p => p.id)}
                strategy={rectSortingStrategy}
              >
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
              </SortableContext>
            </DndContext>
            {filteredProjects.length === 0 && (
              <div className="text-center py-20 text-slate-500">
                No projects found matching &quot;{searchQuery}&quot;
              </div>
            )}
          </div>
        )}

        {/* --- LINKS TAB --- */}
        {activeTab === 'links' && (
          <div className="space-y-6">
            {/* Add Link Form */}
            <div className="bg-slate-900/50 p-4 rounded-xl border border-slate-800">
              <form
                onSubmit={async (e) => {
                  e.preventDefault();
                  const form = e.target as HTMLFormElement;
                  const nameInput = form.elements.namedItem('linkName') as HTMLInputElement;
                  const urlInput = form.elements.namedItem('linkUrl') as HTMLInputElement;
                  if (nameInput.value && urlInput.value) {
                    const success = await addPlatform(nameInput.value, urlInput.value);
                    if (success) {
                      nameInput.value = '';
                      urlInput.value = '';
                    }
                  }
                }}
                className="flex flex-col sm:flex-row gap-3"
              >
                <input
                  name="linkName"
                  type="text"
                  placeholder="Link name"
                  className="flex-1 bg-slate-950 border border-slate-800 rounded-lg px-4 py-2.5 text-sm focus:ring-2 focus:ring-indigo-500 focus:outline-none placeholder-slate-600"
                />
                <input
                  name="linkUrl"
                  type="url"
                  placeholder="https://..."
                  className="flex-[2] bg-slate-950 border border-slate-800 rounded-lg px-4 py-2.5 text-sm focus:ring-2 focus:ring-indigo-500 focus:outline-none placeholder-slate-600"
                />
                <button
                  type="submit"
                  className="bg-indigo-600 hover:bg-indigo-500 text-white px-4 py-2.5 rounded-lg font-medium text-sm flex items-center gap-2 transition-colors"
                >
                  <Plus size={16} />
                  Add Link
                </button>
              </form>
            </div>

            {/* Links Grid */}
            <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-4">
              {platforms.map((platform) => (
                <div
                  key={platform.id}
                  className="group relative p-4 rounded-xl border border-slate-800 bg-slate-900 hover:bg-slate-800/50 hover:border-slate-700 transition-all"
                >
                  <a
                    href={platform.url}
                    target="_blank"
                    rel="noopener noreferrer"
                    className="block"
                  >
                    <div className="flex items-center gap-3">
                      <div className="w-10 h-10 rounded-lg bg-indigo-600/20 border border-indigo-500/30 flex items-center justify-center">
                        <Globe size={20} className="text-indigo-400" />
                      </div>
                      <div className="flex-1 min-w-0">
                        <h3 className="text-white font-semibold truncate group-hover:text-indigo-400 transition-colors">
                          {platform.name}
                        </h3>
                        <p className="text-xs text-slate-500 truncate">{platform.url}</p>
                      </div>
                      <ExternalLink size={16} className="text-slate-600 group-hover:text-slate-400 transition-colors shrink-0" />
                    </div>
                  </a>
                  <button
                    onClick={() => deletePlatform(platform.id)}
                    className="absolute top-2 right-2 p-1.5 rounded-lg bg-slate-800/80 text-slate-500 hover:bg-red-600/20 hover:text-red-400 opacity-0 group-hover:opacity-100 transition-all"
                    title="Delete link"
                  >
                    <Trash2 size={14} />
                  </button>
                </div>
              ))}
            </div>

            {platforms.length === 0 && (
              <div className="text-center py-20 text-slate-500">
                No saved links yet. Add one above!
              </div>
            )}
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
                <label className="block text-sm font-medium text-slate-400 mb-1">Project Path</label>
                <input
                  type="text"
                  value={newPath}
                  onChange={(e) => setNewPath(e.target.value)}
                  placeholder="D:\Projects\my-app"
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
