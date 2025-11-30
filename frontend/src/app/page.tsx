"use client";

import { useState, useEffect, useMemo, useCallback } from "react";
import { Project, HomepageService, ScrutinyDrive, HostServiceStatus, HardwareHistoryResponse } from "@/types";
import { Plus, Search, RefreshCw, ExternalLink, Cpu, Thermometer, HardDrive as HardDriveIcon, ScrollText, Activity } from "lucide-react";
import DocViewer from "@/components/DocViewer";
import Navbar from "@/components/Navbar";
import ProjectCard from "@/components/ProjectCard";
import ProjectModal from "@/components/ProjectModal";

const DEFAULT_LOG_SERVICES = ["google_drive", "syncthing", "docker_desktop", "veeam", "tailscale", "activitywatch"];

export default function Home() {
  // --- State ---
  const [activeTab, setActiveTab] = useState("projects");
  const [projects, setProjects] = useState<Project[]>([]);
  const [searchQuery, setSearchQuery] = useState("");
  
  // Data States
  const [homepageServices, setHomepageServices] = useState<HomepageService[]>([]);
  const [drives, setDrives] = useState<ScrutinyDrive[]>([]);
  const [hostServices, setHostServices] = useState<HostServiceStatus[]>([]);
  const [hardware, setHardware] = useState<HardwareHistoryResponse | null>(null);
  const [hostLogs, setHostLogs] = useState<Record<string, string[]>>({});
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

  const fetchHostStatus = useCallback(async () => {
    try {
      const res = await fetch("/api/host-status");
      if (res.ok) {
        const data = await res.json();
        setHostServices(data.services || []);
      }
    } catch (e) { console.error(e); }
  }, []);

  const fetchHardware = useCallback(async () => {
    try {
      const res = await fetch("/api/host-hardware?limit=300");
      if (res.ok) {
        const data = await res.json();
        setHardware(data);
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
    fetchHomepage();
    fetchDrives();
  }, []);

  useEffect(() => {
    fetchHostStatus();
    const interval = setInterval(fetchHostStatus, 30000);
    return () => clearInterval(interval);
  }, [fetchHostStatus]);

  useEffect(() => {
    fetchHardware();
    const interval = setInterval(fetchHardware, 30000);
    return () => clearInterval(interval);
  }, [fetchHardware]);

  useEffect(() => {
    fetchHostLogs();
    const interval = setInterval(fetchHostLogs, 5 * 60 * 1000);
    return () => clearInterval(interval);
  }, [fetchHostLogs]);

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
                      {svc.icons[0] && (
                        <>
                          {/* eslint-disable-next-line @next/next/no-img-element */}
                          <img 
                            src={svc.icons[0]} 
                            alt={`${svc.name} icon`} 
                            className="w-10 h-10 object-contain bg-slate-800 p-1.5 rounded-lg" 
                          />
                        </>
                      )}
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

        {/* --- PC MONITORING TAB --- */}
        {activeTab === 'host' && (
            <div className="space-y-6">
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

              <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
                <div className="p-5 rounded-xl border border-slate-800 bg-slate-900 shadow-sm">
                  <div className="flex items-center justify-between mb-3">
                    <div>
                      <div className="text-sm text-slate-400">CPU Load (history)</div>
                      <div className="text-lg text-white font-semibold">{formatMetric(readMetric(latestSnapshot, ["cpu", "load_pct"]), "%")}</div>
                      {historyWindowLabel && <div className="text-xs text-slate-500">{historyWindowLabel}</div>}
                    </div>
                    <span className="text-xs text-slate-500">{latestSnapshot?.timestamp ? new Date(latestSnapshot.timestamp).toLocaleTimeString() : ""}</span>
                  </div>
                  <Sparkline data={cpuLoadSeries} color="#22d3ee" />
                </div>

                <div className="p-5 rounded-xl border border-slate-800 bg-slate-900 shadow-sm">
                  <div className="flex items-center justify-between mb-3">
                    <div>
                      <div className="text-sm text-slate-400">CPU Temp (history)</div>
                      <div className="text-lg text-white font-semibold">{formatMetric(readMetric(latestSnapshot, ["cpu", "temp_c"]), "°C")}</div>
                      {historyWindowLabel && <div className="text-xs text-slate-500">{historyWindowLabel}</div>}
                    </div>
                    <span className="text-xs text-slate-500">{latestSnapshot?.timestamp ? new Date(latestSnapshot.timestamp).toLocaleTimeString() : ""}</span>
                  </div>
                  <Sparkline data={cpuTempSeries} color="#f59e0b" />
                </div>

                <div className="p-5 rounded-xl border border-slate-800 bg-slate-900 shadow-sm">
                  <div className="flex items-center justify-between mb-3">
                    <div>
                      <div className="text-sm text-slate-400">GPU Temp (history)</div>
                      <div className="text-lg text-white font-semibold">{formatMetric(readMetric(latestSnapshot, ["gpu", "temp_c"]), "°C")}</div>
                      {historyWindowLabel && <div className="text-xs text-slate-500">{historyWindowLabel}</div>}
                    </div>
                    <span className="text-xs text-slate-500">{latestSnapshot?.timestamp ? new Date(latestSnapshot.timestamp).toLocaleTimeString() : ""}</span>
                  </div>
                  <Sparkline data={gpuTempSeries} color="#38bdf8" />
                </div>

                <div className="p-5 rounded-xl border border-slate-800 bg-slate-900 shadow-sm">
                  <div className="flex items-center justify-between mb-3">
                    <div>
                      <div className="text-sm text-slate-400">RAM Usage (history)</div>
                      <div className="text-lg text-white font-semibold">{formatMetric(readMetric(latestSnapshot, ["ram", "load_pct"]), "%")}</div>
                      {historyWindowLabel && <div className="text-xs text-slate-500">{historyWindowLabel}</div>}
                    </div>
                    <span className="text-xs text-slate-500">{latestSnapshot?.timestamp ? new Date(latestSnapshot.timestamp).toLocaleTimeString() : ""}</span>
                  </div>
                  <Sparkline data={ramLoadSeries} color="#34d399" />
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
