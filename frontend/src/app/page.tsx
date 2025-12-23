"use client";

import { useState, useEffect, useMemo, useCallback, useRef } from "react";
import { Project, HostServiceStatus, HardwareHistoryResponse, Platform, SortMode } from "@/types";
import { Plus, Search, RefreshCw, ExternalLink, Cpu, Thermometer, HardDrive as HardDriveIcon, ScrollText, Activity, Globe, Trash2, ArrowUpDown, GripVertical } from "lucide-react";
import DocViewer from "@/components/DocViewer";
import Navbar from "@/components/Navbar";
import ProjectCard from "@/components/ProjectCard";
import ProjectModal from "@/components/ProjectModal";
import MetricChart from "@/components/MetricChart";
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

const DEFAULT_LOG_SERVICES = ["google_drive", "syncthing", "docker_desktop", "veeam", "tailscale", "activitywatch"];

export default function Home() {
  // --- State ---
  const [activeTab, setActiveTab] = useState("projects");
  const [projects, setProjects] = useState<Project[]>([]);
  const [searchQuery, setSearchQuery] = useState("");
  const [sortMode, setSortMode] = useState<SortMode>('custom');
  const searchInputRef = useRef<HTMLInputElement>(null);

  // Data States
  const [hostServices, setHostServices] = useState<HostServiceStatus[]>([]);
  const [hardware, setHardware] = useState<HardwareHistoryResponse | null>(null);
  const [hostLogs, setHostLogs] = useState<Record<string, string[]>>({});
  const [statuses, setStatuses] = useState<Record<string, boolean | null>>({});
  const [platforms, setPlatforms] = useState<Platform[]>([]);

  // Cache timestamps
  const [lastUpdated, setLastUpdated] = useState<Record<string, string>>({});
  const [refreshing, setRefreshing] = useState<Record<string, boolean>>({});

  // History state for charts
  type TimeRange = '1h' | '6h' | '24h' | '7d';
  const [historyRange, setHistoryRange] = useState<TimeRange>('1h');
  const [historyData, setHistoryData] = useState<Array<Record<string, unknown>>>([]);

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

  const formatRelativeTime = (isoTimestamp: string | undefined) => {
    if (!isoTimestamp) return null;
    try {
      const date = new Date(isoTimestamp);
      const now = new Date();
      const diffSec = Math.floor((now.getTime() - date.getTime()) / 1000);
      if (diffSec < 60) return "just now";
      if (diffSec < 3600) return `${Math.floor(diffSec / 60)} min ago`;
      if (diffSec < 86400) return `${Math.floor(diffSec / 3600)} hr ago`;
      return date.toLocaleDateString();
    } catch {
      return null;
    }
  };

  const readMetric = (snapshot: HardwareHistoryResponse["latest"], path: string[]) => {
    if (!snapshot) return undefined;
    const source = snapshot.metrics && typeof snapshot.metrics === "object" ? snapshot.metrics as Record<string, unknown> : snapshot as Record<string, unknown>;
    let current: unknown = source;
    for (const key of path) {
      if (current && typeof current === "object" && key in current) {
        current = (current as Record<string, unknown>)[key];
      } else {
        return undefined;
      }
    }
    return typeof current === "number" ? current : undefined;
  };

  const buildSeries = useCallback((history: HardwareHistoryResponse["history"], path: string[]) => {
    if (!history) return [];
    return history
      .map((row) => readMetric(row, path))
      .filter((v): v is number => typeof v === "number" && !Number.isNaN(v))
      .slice(-120);
  }, []);

  const formatMetric = (value?: number, suffix = "", digits = 1) =>
    typeof value === "number" ? `${value.toFixed(digits)}${suffix}` : "—";

  const parseLogText = (text: string) => {
    try {
      const parsed = JSON.parse(text);
      if (Array.isArray(parsed)) return parsed.map(line => String(line));
      if (parsed && typeof parsed === "object" && Array.isArray((parsed as Record<string, unknown>).lines)) {
        const lines = (parsed as { lines: unknown[] }).lines;
        return lines.map(line => String(line));
      }
    } catch {
      // If not JSON, fall back to splitting text
    }
    return text.split(/\r?\n/).filter(Boolean);
  };

  const formatDetails = (details?: Record<string, unknown>) => {
    if (!details) return "";
    return Object.entries(details)
      .map(([key, val]) => `${key}: ${Array.isArray(val) ? val.join(", ") : String(val)}`)
      .join(" • ");
  };

  const extractNetwork = (snapshot: HardwareHistoryResponse["latest"]) => {
    if (!snapshot) return undefined;
    if ("network" in snapshot && snapshot.network && typeof snapshot.network === "object") {
      return snapshot.network as Record<string, unknown>;
    }
    if ("metrics" in (snapshot as Record<string, unknown>)) {
      const metrics = (snapshot as { metrics?: Record<string, unknown> }).metrics;
      if (metrics && typeof metrics === "object" && "network" in metrics) {
        return (metrics as { network?: Record<string, unknown> }).network;
      }
    }
    return undefined;
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

  const fetchHostStatus = useCallback(async (forceRefresh = false) => {
    if (forceRefresh) setRefreshing(r => ({ ...r, hostStatus: true }));
    try {
      const url = forceRefresh ? "/api/host-status/refresh" : "/api/host-status";
      const res = await fetch(url, { method: forceRefresh ? "POST" : "GET" });
      if (res.ok) {
        const data = await res.json();
        setHostServices(data.services || []);
        if (data.last_updated) setLastUpdated(u => ({ ...u, hostStatus: data.last_updated }));
      }
    } catch (e) { console.error(e); }
    if (forceRefresh) setRefreshing(r => ({ ...r, hostStatus: false }));
  }, []);

  const fetchHardware = useCallback(async (forceRefresh = false) => {
    if (forceRefresh) setRefreshing(r => ({ ...r, hardware: true }));
    try {
      const url = forceRefresh ? "/api/host-hardware/refresh" : "/api/host-hardware?limit=300";
      const res = await fetch(url, { method: forceRefresh ? "POST" : "GET" });
      if (res.ok) {
        const data = await res.json();
        setHardware(data);
        if (data.last_updated) setLastUpdated(u => ({ ...u, hardware: data.last_updated }));
      }
    } catch (e) { console.error(e); }
    if (forceRefresh) setRefreshing(r => ({ ...r, hardware: false }));
  }, []);

  const fetchHistory = useCallback(async (range: TimeRange) => {
    try {
      const rangeMinutes = { '1h': 60, '6h': 360, '24h': 1440, '7d': 10080 };
      const minutes = rangeMinutes[range];
      const res = await fetch(`/api/history?minutes=${minutes}`);
      if (res.ok) {
        const data = await res.json();
        setHistoryData(data.history || []);
      }
    } catch (e) { console.error(e); }
  }, []);

  const fetchHostLogs = useCallback(async () => {
    const servicesToPoll = hostServices.length ? hostServices.map((svc) => svc.name) : DEFAULT_LOG_SERVICES;
    const logEntries: Record<string, string[]> = {};

    const requests = servicesToPoll.map(async (service) => {
      try {
        const res = await fetch(`/api/host-logs?service=${encodeURIComponent(service)}&lines=80`);
        if (!res.ok) return;
        const text = await res.text();
        logEntries[service] = parseLogText(text).slice(-10);
      } catch (e) { console.error(e); }
    });

    await Promise.all(requests);
    setHostLogs(logEntries);
  }, [hostServices]);

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

  useEffect(() => {
    fetchHostStatus();
    const interval = setInterval(fetchHostStatus, 60000); // Reduced from 30s to 60s
    return () => clearInterval(interval);
  }, [fetchHostStatus]);

  useEffect(() => {
    fetchHardware();
    const interval = setInterval(fetchHardware, 60000); // Reduced from 30s to 60s
    return () => clearInterval(interval);
  }, [fetchHardware]);

  useEffect(() => {
    fetchHostLogs();
    const interval = setInterval(fetchHostLogs, 5 * 60 * 1000);
    return () => clearInterval(interval);
  }, [fetchHostLogs]);

  // Fetch history data when range changes
  useEffect(() => {
    fetchHistory(historyRange);
    // Also refresh every 60 seconds
    const interval = setInterval(() => fetchHistory(historyRange), 60000);
    return () => clearInterval(interval);
  }, [fetchHistory, historyRange]);

  useEffect(() => {
    if (projects.length === 0) return;

    const checkStatuses = async () => {
      const newStatuses: Record<string, boolean | null> = {};
      const checks = projects.map(async (p) => {
        if (!p.frontend_url) return;
        try {
          // Use formatted URL (with overrides) to hit backend proxy
          const targetUrl = formatUrl(p.frontend_url, p);
          const res = await fetch(`/api/monitor/status?url=${encodeURIComponent(targetUrl)}`);
          newStatuses[p.id] = res.ok ? (await res.json()).is_up : false;
        } catch { newStatuses[p.id] = false; }
      });
      await Promise.all(checks);
      setStatuses(prev => ({ ...prev, ...newStatuses }));
    };

    checkStatuses();
    const interval = setInterval(checkStatuses, 60000); // Reduced from 30s to 60s
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
      // 'created' and 'modified' would need timestamps in the Project model
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

    // Switch to custom sort when dragging
    setSortMode('custom');

    const oldIndex = sortedProjects.findIndex(p => p.id === active.id);
    const newIndex = sortedProjects.findIndex(p => p.id === over.id);

    if (oldIndex !== -1 && newIndex !== -1) {
      const reordered = arrayMove(sortedProjects, oldIndex, newIndex);
      const newOrder = reordered.map(p => p.id);

      // Optimistically update UI
      setProjects(reordered.map((p, i) => ({ ...p, position: i })));

      // Persist to backend
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

  const latestSnapshot = hardware?.latest;
  const cpuLoadSeries = useMemo(() => buildSeries(hardware?.history, ["cpu", "load_pct"]), [buildSeries, hardware]);
  const cpuTempSeries = useMemo(() => buildSeries(hardware?.history, ["cpu", "temp_c"]), [buildSeries, hardware]);
  const gpuTempSeries = useMemo(() => buildSeries(hardware?.history, ["gpu", "temp_c"]), [buildSeries, hardware]);
  const ramLoadSeries = useMemo(() => buildSeries(hardware?.history, ["ram", "load_pct"]), [buildSeries, hardware]);
  const servicesToShowLogs = hostServices.length ? hostServices.map((svc) => svc.name) : DEFAULT_LOG_SERVICES;

  const drivesList = useMemo(() => {
    const fromRoot = Array.isArray((latestSnapshot as { drives?: unknown[] } | undefined)?.drives)
      ? (latestSnapshot as { drives: unknown[] }).drives
      : [];
    const fromMetrics = latestSnapshot && typeof latestSnapshot === "object" && "metrics" in latestSnapshot
      ? (latestSnapshot as { metrics?: { drives?: unknown[] } }).metrics?.drives ?? []
      : [];
    return (fromRoot.length ? fromRoot : fromMetrics).filter(Boolean) as {
      id?: string;
      name?: string;
      temp_c?: number;
      used_pct?: number;
      read_rate_mbps?: number;
      write_rate_mbps?: number;
      data_read_gb?: number;
      data_written_gb?: number;
    }[];
  }, [latestSnapshot]);

  const primaryDrive = drivesList[0];
  const historyWindowLabel = useMemo(() => {
    const historyList = hardware?.history;
    if (!historyList || historyList.length < 2) return null;
    const newestTs = historyList[0]?.timestamp;
    const oldestTs = historyList[historyList.length - 1]?.timestamp;
    if (!newestTs || !oldestTs) return null;
    const diffMs = new Date(newestTs).getTime() - new Date(oldestTs).getTime();
    if (Number.isNaN(diffMs) || diffMs <= 0) return null;
    const minutes = diffMs / 60000;
    if (minutes < 1) return `${Math.round(minutes * 60)} sec window`;
    if (minutes < 10) return `${minutes.toFixed(1)} min window`;
    return `${Math.round(minutes)} min window`;
  }, [hardware]);

  const networkAdapters = useMemo(() => {
    const network = extractNetwork(latestSnapshot);
    if (!network || typeof network !== "object") return [];
    return Object.entries(network as Record<string, unknown>).map(([key, value]) => {
      const val = value as Record<string, unknown>;
      return {
        key,
        name: key,
        uploadRate: typeof val?.upload_rate_mbps === "number" ? val.upload_rate_mbps : undefined,
        downloadRate: typeof val?.download_rate_mbps === "number" ? val.download_rate_mbps : undefined,
        uploadedGb: typeof val?.data_uploaded_gb === "number" ? val.data_uploaded_gb : undefined,
        downloadedGb: typeof val?.data_downloaded_gb === "number" ? val.data_downloaded_gb : undefined,
      };
    });
  }, [latestSnapshot]);

  const networkSeries = useMemo(() => {
    const series: Record<string, { upload: number[]; download: number[] }> = {};
    (hardware?.history || []).forEach((row) => {
      const network = extractNetwork(row);
      if (!network || typeof network !== "object") return;
      Object.entries(network as Record<string, unknown>).forEach(([key, value]) => {
        const val = value as Record<string, unknown>;
        const upload = typeof val?.upload_rate_mbps === "number" ? val.upload_rate_mbps : undefined;
        const download = typeof val?.download_rate_mbps === "number" ? val.download_rate_mbps : undefined;
        if (!series[key]) series[key] = { upload: [], download: [] };
        if (typeof upload === "number" && !Number.isNaN(upload)) series[key].upload.push(upload);
        if (typeof download === "number" && !Number.isNaN(download)) series[key].download.push(download);
      });
    });
    Object.keys(series).forEach((key) => {
      series[key].upload = series[key].upload.slice(-120);
      series[key].download = series[key].download.slice(-120);
    });
    return series;
  }, [hardware]);

  const driveSeries = useMemo(() => {
    const series: Record<string, { name: string; read: number[]; write: number[] }> = {};
    (hardware?.history || []).forEach((row) => {
      const drives = (row as { drives?: unknown[]; metrics?: { drives?: unknown[] } }).drives
        ?? (row as { metrics?: { drives?: unknown[] } }).metrics?.drives
        ?? [];
      if (!Array.isArray(drives)) return;
      drives.forEach((drive, idx) => {
        const d = drive as Record<string, unknown>;
        const key = (typeof d.id === "string" && d.id) || (typeof d.name === "string" && d.name) || `drive-${idx}`;
        if (!series[key]) series[key] = { name: (d.name as string) || key, read: [], write: [] };
        const read = typeof d.read_rate_mbps === "number" ? d.read_rate_mbps : undefined;
        const write = typeof d.write_rate_mbps === "number" ? d.write_rate_mbps : undefined;
        if (typeof read === "number" && !Number.isNaN(read)) series[key].read.push(read);
        if (typeof write === "number" && !Number.isNaN(write)) series[key].write.push(write);
      });
    });
    Object.keys(series).forEach((key) => {
      series[key].read = series[key].read.slice(-120);
      series[key].write = series[key].write.slice(-120);
    });
    return series;
  }, [hardware]);

  const Sparkline = ({ data, color = "#818cf8" }: { data: number[]; color?: string }) => {
    if (!data.length) {
      return <div className="text-xs text-slate-500">No history yet</div>;
    }
    const max = Math.max(...data);
    const min = Math.min(...data);
    const range = max - min || 1;
    const points = data.map((val, idx) => {
      const x = data.length === 1 ? 0 : (idx / (data.length - 1)) * 100;
      const y = 100 - ((val - min) / range) * 100;
      return `${x},${y}`;
    }).join(" ");

    return (
      <svg viewBox="0 0 100 100" preserveAspectRatio="none" className="w-full h-20">
        <polyline
          fill="none"
          stroke={color}
          strokeWidth="2"
          strokeLinecap="round"
          strokeLinejoin="round"
          points={points}
        />
      </svg>
    );
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

        {/* --- PC MONITORING TAB --- */}
        {activeTab === 'host' && (
          <div className="space-y-6">
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-3">
                <h2 className="text-lg font-semibold text-white">PC Monitoring</h2>
                {lastUpdated.hardware && (
                  <span className="text-xs text-slate-500">Updated {formatRelativeTime(lastUpdated.hardware)}</span>
                )}
              </div>
              <button
                onClick={() => { fetchHardware(true); fetchHostStatus(true); }}
                disabled={refreshing.hardware || refreshing.hostStatus}
                className="flex items-center gap-1.5 px-3 py-1.5 text-xs bg-slate-800 hover:bg-slate-700 disabled:opacity-50 rounded-lg text-slate-300 transition-colors"
              >
                <RefreshCw size={14} className={(refreshing.hardware || refreshing.hostStatus) ? "animate-spin" : ""} />
                Refresh
              </button>
            </div>
            <div className="grid grid-cols-1 sm:grid-cols-2 xl:grid-cols-4 gap-4">
              <div className="p-4 rounded-xl border border-slate-800 bg-slate-900 shadow-sm">
                <div className="flex items-center justify-between text-sm text-slate-400 mb-2">
                  <span>CPU Load</span>
                  <Cpu size={16} className="text-indigo-400" />
                </div>
                <div className="text-2xl font-semibold text-white">{formatMetric(readMetric(latestSnapshot, ["cpu", "load_pct"]), "%")}</div>
                <div className="text-xs text-slate-500 mt-1">Clock {formatMetric(readMetric(latestSnapshot, ["cpu", "clock_mhz"]), " MHz", 0)}</div>
              </div>

              <div className="p-4 rounded-xl border border-slate-800 bg-slate-900 shadow-sm">
                <div className="flex items-center justify-between text-sm text-slate-400 mb-2">
                  <span>CPU Temp</span>
                  <Thermometer size={16} className="text-amber-300" />
                </div>
                <div className="text-2xl font-semibold text-white">{formatMetric(readMetric(latestSnapshot, ["cpu", "temp_c"]), "°C")}</div>
                <div className="text-xs text-slate-500 mt-1">GPU Temp {formatMetric(readMetric(latestSnapshot, ["gpu", "temp_c"]), "°C")}</div>
              </div>

              <div className="p-4 rounded-xl border border-slate-800 bg-slate-900 shadow-sm">
                <div className="flex items-center justify-between text-sm text-slate-400 mb-2">
                  <span>RAM Usage</span>
                  <Activity size={16} className="text-emerald-300" />
                </div>
                <div className="text-2xl font-semibold text-white">{formatMetric(readMetric(latestSnapshot, ["ram", "load_pct"]), "%")}</div>
                <div className="text-xs text-slate-500 mt-1">Used {formatMetric(readMetric(latestSnapshot, ["ram", "used_gb"]), " GB")}</div>
              </div>

              <div className="p-4 rounded-xl border border-slate-800 bg-slate-900 shadow-sm">
                <div className="flex items-center justify-between text-sm text-slate-400 mb-2">
                  <span>Primary Drive</span>
                  <HardDriveIcon size={16} className="text-sky-300" />
                </div>
                <div className="text-2xl font-semibold text-white">{formatMetric(typeof primaryDrive?.used_pct === "number" ? primaryDrive.used_pct : undefined, "%")}</div>
                <div className="text-xs text-slate-500 mt-1">Temp {formatMetric(typeof primaryDrive?.temp_c === "number" ? primaryDrive.temp_c : undefined, "°C")}</div>
              </div>
            </div>
            {/* History Charts (DuckDB data) */}
            <div>
              <div className="flex items-center justify-between mb-3">
                <div className="flex items-center gap-2 text-sm font-semibold text-slate-300">
                  <Activity size={16} />
                  <span>Historical Metrics</span>
                </div>
                <div className="flex gap-1">
                  {(['1h', '6h', '24h', '7d'] as const).map((range) => (
                    <button
                      key={range}
                      onClick={() => setHistoryRange(range)}
                      className={`px-2.5 py-1 text-xs rounded-lg transition-colors ${historyRange === range
                        ? 'bg-indigo-600 text-white'
                        : 'bg-slate-800 text-slate-400 hover:bg-slate-700'
                        }`}
                    >
                      {range}
                    </button>
                  ))}
                </div>
              </div>
              <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
                <MetricChart
                  data={historyData as Array<{ timestamp: string;[key: string]: number | string | null | undefined }>}
                  dataKey="cpu_load"
                  title="CPU Load"
                  color="indigo"
                  unit="%"
                  maxY={100}
                  timeRange={historyRange}
                />
                <MetricChart
                  data={historyData as Array<{ timestamp: string;[key: string]: number | string | null | undefined }>}
                  dataKey="cpu_temp"
                  title="CPU Temperature"
                  color="amber"
                  unit="°C"
                  timeRange={historyRange}
                />
                <MetricChart
                  data={historyData as Array<{ timestamp: string;[key: string]: number | string | null | undefined }>}
                  dataKey="gpu_temp"
                  title="GPU Temperature"
                  color="cyan"
                  unit="°C"
                  timeRange={historyRange}
                />
                <MetricChart
                  data={historyData as Array<{ timestamp: string;[key: string]: number | string | null | undefined }>}
                  dataKey="ram_load"
                  title="RAM Usage"
                  color="green"
                  unit="%"
                  maxY={100}
                  timeRange={historyRange}
                />
              </div>
            </div>

            <div>
              <div className="flex items-center gap-2 mb-3 text-sm font-semibold text-slate-300">
                <Activity size={16} />
                <span>Network</span>
              </div>
              <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
                {networkAdapters.map((net) => {
                  const series = networkSeries[net.key] || { upload: [], download: [] };
                  return (
                    <div key={net.key} className="p-4 rounded-xl border border-slate-800 bg-slate-900 shadow-sm flex flex-col gap-3">
                      <div className="flex items-center justify-between">
                        <div className="text-white font-semibold">{net.name}</div>
                        {historyWindowLabel && <span className="text-[11px] text-slate-500">{historyWindowLabel}</span>}
                      </div>
                      <div className="grid grid-cols-2 gap-2 text-sm">
                        <div className="p-2 rounded-lg bg-slate-950 border border-slate-800">
                          <div className="text-[11px] uppercase tracking-wide text-slate-500">Up</div>
                          <div className="text-lg text-white">{formatMetric(net.uploadRate, " Mbps")}</div>
                          <div className="text-[11px] text-slate-500">Total {formatMetric(net.uploadedGb, " GB", 0)}</div>
                        </div>
                        <div className="p-2 rounded-lg bg-slate-950 border border-slate-800">
                          <div className="text-[11px] uppercase tracking-wide text-slate-500">Down</div>
                          <div className="text-lg text-white">{formatMetric(net.downloadRate, " Mbps")}</div>
                          <div className="text-[11px] text-slate-500">Total {formatMetric(net.downloadedGb, " GB", 0)}</div>
                        </div>
                      </div>
                      <div className="grid grid-cols-2 gap-2 text-xs">
                        <div>
                          <div className="text-[11px] uppercase text-slate-500 mb-1">Up history</div>
                          <Sparkline data={series.upload} color="#f472b6" />
                        </div>
                        <div>
                          <div className="text-[11px] uppercase text-slate-500 mb-1">Down history</div>
                          <Sparkline data={series.download} color="#60a5fa" />
                        </div>
                      </div>
                    </div>
                  );
                })}
                {networkAdapters.length === 0 && (
                  <div className="text-sm text-slate-500">No network telemetry yet.</div>
                )}
              </div>
            </div>

            <div>
              <div className="flex items-center gap-2 mb-3 text-sm font-semibold text-slate-300">
                <HardDriveIcon size={16} />
                <span>Drives</span>
              </div>
              <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
                {drivesList.map((drive, idx) => (
                  <div key={drive.id || `${drive.name}-${idx}`} className="p-4 rounded-xl border border-slate-800 bg-slate-900 shadow-sm flex flex-col gap-2">
                    <div className="flex items-center justify-between">
                      <div>
                        <div className="text-white font-semibold">{drive.name || drive.id || `Drive ${idx + 1}`}</div>
                        <div className="text-xs text-slate-500">{typeof drive.used_pct === "number" ? `${drive.used_pct.toFixed(1)}% used` : "Usage n/a"}</div>
                      </div>
                      <div className="text-xs text-slate-500">{typeof drive.temp_c === "number" ? `${drive.temp_c.toFixed(1)}°C` : "Temp n/a"}</div>
                    </div>
                    <div className="grid grid-cols-2 gap-2 text-xs text-slate-400">
                      <div className="p-2 rounded-lg bg-slate-950 border border-slate-800">
                        <div className="text-[11px] uppercase tracking-wide">Read</div>
                        <div className="text-sm text-white">{typeof drive.read_rate_mbps === "number" ? `${drive.read_rate_mbps.toFixed(1)} MB/s` : "—"}</div>
                      </div>
                      <div className="p-2 rounded-lg bg-slate-950 border border-slate-800">
                        <div className="text-[11px] uppercase tracking-wide">Write</div>
                        <div className="text-sm text-white">{typeof drive.write_rate_mbps === "number" ? `${drive.write_rate_mbps.toFixed(1)} MB/s` : "—"}</div>
                      </div>
                      <div className="p-2 rounded-lg bg-slate-950 border border-slate-800 col-span-2">
                        <div className="text-[11px] uppercase tracking-wide flex items-center justify-between">
                          <span>Totals</span>
                          <span className="text-[10px] text-slate-500">read / written</span>
                        </div>
                        <div className="text-sm text-white flex items-center justify-between gap-2 mt-1">
                          <span>{typeof drive.data_read_gb === "number" ? `${drive.data_read_gb.toFixed(0)} GB` : "—"}</span>
                          <span className="text-slate-400">/</span>
                          <span>{typeof drive.data_written_gb === "number" ? `${drive.data_written_gb.toFixed(0)} GB` : "—"}</span>
                        </div>
                      </div>
                      <div className="col-span-2 grid grid-cols-2 gap-2 text-[11px]">
                        <div className="bg-slate-950 border border-slate-800 rounded-lg p-2">
                          <div className="uppercase tracking-wide text-slate-500 mb-1">Read history</div>
                          <Sparkline data={(driveSeries[drive.id || drive.name || `drive-${idx}`]?.read) || []} color="#a855f7" />
                        </div>
                        <div className="bg-slate-950 border border-slate-800 rounded-lg p-2">
                          <div className="uppercase tracking-wide text-slate-500 mb-1">Write history</div>
                          <Sparkline data={(driveSeries[drive.id || drive.name || `drive-${idx}`]?.write) || []} color="#22c55e" />
                        </div>
                      </div>
                    </div>
                  </div>
                ))}
                {drivesList.length === 0 && (
                  <div className="text-sm text-slate-500">No drive telemetry yet.</div>
                )}
              </div>
            </div>
          </div>
        )}

        {/* --- PC SERVICES TAB --- */}
        {activeTab === 'services' && (
          <div className="space-y-6">
            <div>
              <div className="flex items-center gap-2 mb-3 text-sm font-semibold text-slate-300">
                <Activity size={16} />
                <span>Service Status</span>
              </div>
              <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
                {hostServices.map((svc) => (
                  <div key={svc.name} className="p-4 rounded-xl border border-slate-800 bg-slate-900 shadow-sm flex flex-col gap-2">
                    <div className="flex items-center justify-between">
                      <div className="flex items-center gap-2">
                        <div className={`w-2.5 h-2.5 rounded-full ${svc.state === 'running' ? 'bg-emerald-400' : 'bg-red-400'}`} />
                        <div className="text-white font-semibold">{svc.name}</div>
                      </div>
                      <span className="text-xs uppercase tracking-wide text-slate-500">{svc.state}</span>
                    </div>
                    {formatDetails(svc.details) && (
                      <div className="text-xs text-slate-500 leading-snug">
                        {formatDetails(svc.details)}
                      </div>
                    )}
                  </div>
                ))}
                {hostServices.length === 0 && (
                  <div className="text-sm text-slate-500">No host services reported yet.</div>
                )}
              </div>
            </div>

            <div>
              <div className="flex items-center gap-2 mb-3 text-sm font-semibold text-slate-300">
                <ScrollText size={16} />
                <span>Recent Logs (polled every 5 min)</span>
              </div>
              <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
                {servicesToShowLogs.map((svc) => {
                  const lines = hostLogs[svc] || [];
                  return (
                    <div key={svc} className="p-4 rounded-xl border border-slate-800 bg-slate-900 shadow-sm flex flex-col gap-2">
                      <div className="flex items-center justify-between text-sm text-slate-300">
                        <span className="font-semibold">{svc}</span>
                        <span className="text-[11px] text-slate-500">last 10 lines</span>
                      </div>
                      <pre className="bg-slate-950 border border-slate-800 rounded-lg p-3 text-xs text-slate-300 overflow-auto max-h-48 whitespace-pre-wrap">
                        {lines.length ? lines.join("\n") : "No log lines yet."}
                      </pre>
                    </div>
                  );
                })}
              </div>
            </div>
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
