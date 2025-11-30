import { Project } from "@/types";
import { X, Terminal, Code2, Command, Folder, Globe, Link, ExternalLink, FileText, Copy, Check, Plus, Trash2 } from "lucide-react";
import { useState, useEffect, useMemo } from "react";

interface ProjectModalProps {
  project: Project;
  isOpen: boolean;
  onClose: () => void;
  onLaunch: (path: string, type: string) => void;
  onViewDoc: (doc: {path: string, name: string}) => void;
  onUpdate: (updatedProject: Project) => void;
  onDelete: () => void;
  formatUrl: (url: string, project?: Project) => string;
  status: boolean | null;
}

export default function ProjectModal({ project, isOpen, onClose, onLaunch, onViewDoc, onUpdate, onDelete, formatUrl, status }: ProjectModalProps) {
  const [copiedPath, setCopiedPath] = useState(false);
  const [loading, setLoading] = useState(false);
  const [deleteConfirm, setDeleteConfirm] = useState(false);
  const [frontendPort, setFrontendPort] = useState("");
  const [backendPort, setBackendPort] = useState("");
  const detectedFrontendPort = useMemo(() => {
    try {
      return project.frontend_url ? new URL(project.frontend_url).port || "" : "";
    } catch {
      return "";
    }
  }, [project.frontend_url]);

  // Custom Link State
  const [isAddingLink, setIsAddingLink] = useState(false);
  const [newLinkName, setNewLinkName] = useState("");
  const [newLinkUrl, setNewLinkUrl] = useState("");

  // Custom Doc State
  const [isAddingDoc, setIsAddingDoc] = useState(false);
  const [newDocName, setNewDocName] = useState("");
  const [newDocPath, setNewDocPath] = useState("");

  // Handle Escape Key
  useEffect(() => {
    const handleEsc = (e: KeyboardEvent) => {
        if (e.key === 'Escape') onClose();
    };
    if (isOpen) window.addEventListener('keydown', handleEsc);
    return () => window.removeEventListener('keydown', handleEsc);
  }, [isOpen, onClose]);

  useEffect(() => {
    setFrontendPort(project.frontend_port_override || detectedFrontendPort || "");
    setBackendPort(project.backend_port_override || project.backend_port || "");
  }, [project, detectedFrontendPort]);

  if (!isOpen) return null;

  const handleCopyPath = async () => {
    try {
        await navigator.clipboard.writeText(project.path);
        setCopiedPath(true);
        setTimeout(() => setCopiedPath(false), 2000);
    } catch (err) { /* Fallback ignored */ }
  };

  // --- API Actions ---

  const savePorts = async () => {
    setLoading(true);
    try {
      const res = await fetch(`/api/projects/${project.id}/ports`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          frontend_port: frontendPort || null,
          backend_port: backendPort || null,
        }),
      });
      if (res.ok) {
        onUpdate(await res.json());
      }
    } catch (e) { console.error(e); }
    finally { setLoading(false); }
  };

  const addLink = async () => {
    if (!newLinkName || !newLinkUrl) return;
    setLoading(true);
    try {
        const res = await fetch(`/api/projects/${project.id}/links`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ name: newLinkName, url: newLinkUrl })
        });
        if (res.ok) {
            onUpdate(await res.json());
            setNewLinkName("");
            setNewLinkUrl("");
            setIsAddingLink(false);
        }
    } catch (e) { console.error(e); }
    finally { setLoading(false); }
  };

  const removeLink = async (name: string) => {
    if (!confirm("Remove this link?")) return;
    setLoading(true);
    try {
        const res = await fetch(`/api/projects/${project.id}/links/${encodeURIComponent(name)}`, { method: 'DELETE' });
        if (res.ok) onUpdate(await res.json());
    } catch (e) { console.error(e); }
    finally { setLoading(false); }
  };

  const addDoc = async () => {
    if (!newDocName || !newDocPath) return;
    setLoading(true);
    try {
        const res = await fetch(`/api/projects/${project.id}/custom-docs`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ name: newDocName, path: newDocPath })
        });
        if (res.ok) {
            onUpdate(await res.json());
            setNewDocName("");
            setNewDocPath("");
            setIsAddingDoc(false);
        }
    } catch (e) { console.error(e); }
    finally { setLoading(false); }
  };

  const removeDoc = async (name: string) => {
    if (!confirm("Remove this document reference?")) return;
    setLoading(true);
    try {
        const res = await fetch(`/api/projects/${project.id}/custom-docs/${encodeURIComponent(name)}`, { method: 'DELETE' });
        if (res.ok) onUpdate(await res.json());
    } catch (e) { console.error(e); }
    finally { setLoading(false); }
  };

  return (
    <div 
      className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/60 backdrop-blur-sm animate-in fade-in duration-200"
      onClick={onClose}
    >
      <div 
        className="relative w-full max-w-2xl bg-slate-900 border border-slate-800 rounded-xl shadow-2xl overflow-hidden flex flex-col max-h-[90vh] animate-in zoom-in-95 duration-200"
        onClick={(e) => e.stopPropagation()}
      >
        {/* Header */}
        <div className="p-6 border-b border-slate-800 bg-slate-900/50 flex justify-between items-start">
           <div>
               <h2 className="text-2xl font-bold text-white mb-1">{project.name}</h2>
               <div 
                 className="flex items-center gap-2 text-slate-400 text-sm font-mono cursor-pointer hover:text-slate-300 transition-colors"
                 onClick={handleCopyPath}
                 title="Click to copy path"
               >
                  <span className="truncate max-w-[300px] md:max-w-md">{project.path}</span>
                  {copiedPath ? <Check size={14} className="text-green-500"/> : <Copy size={14}/>}
               </div>
           </div>
           <button onClick={onClose} className="p-2 hover:bg-slate-800 rounded-lg text-slate-400 hover:text-white transition-colors">
             <X size={24} />
           </button>
        </div>

        {/* Content Scrollable */}
        <div className="overflow-y-auto p-6 space-y-6 bg-slate-950/50 flex-1">
            
            {/* Status & App Link */}
            {project.frontend_url && (
                <div className="flex items-center justify-between p-4 bg-slate-900 rounded-lg border border-slate-800">
                    <div className="flex items-center gap-3">
                         <div className={`w-3 h-3 rounded-full ${
                            status === true ? "bg-green-500 shadow-[0_0_8px_rgba(34,197,94,0.6)]" : 
                            status === false ? "bg-red-500" : "bg-slate-600"
                         }`} />
                         <div>
                            <div className="text-sm text-slate-400 font-medium uppercase tracking-wider">Application Status</div>
                            <div className="text-white font-semibold">{status === true ? "Online" : status === false ? "Offline" : "Unknown"}</div>
                         </div>
                    </div>
                    <a 
                       href={formatUrl(project.frontend_url, project)}
                       target="_blank"
                       rel="noopener noreferrer"
                       className="flex items-center gap-2 bg-indigo-600 hover:bg-indigo-500 text-white px-4 py-2 rounded-lg font-medium transition-colors"
                    >
                        <Globe size={18} />
                        Open App
                    </a>
                </div>
            )}

            <div className="p-4 bg-slate-900 rounded-lg border border-slate-800 space-y-3">
              <div className="flex items-center justify-between">
                <div>
                  <div className="text-sm text-slate-400 font-medium uppercase tracking-wider">Port Overrides</div>
                  <div className="text-xs text-slate-500">Leave blank to use detected ports.</div>
                </div>
                <button
                  onClick={savePorts}
                  disabled={loading}
                  className="text-xs bg-indigo-600 hover:bg-indigo-500 disabled:opacity-60 text-white px-3 py-1.5 rounded-md font-medium"
                >
                  Save
                </button>
              </div>
              <div className="grid grid-cols-2 gap-3">
                <label className="space-y-1 text-sm text-slate-300">
                  <span className="text-xs text-slate-500">Frontend Port</span>
                  <input
                    type="number"
                    value={frontendPort}
                    onChange={(e) => setFrontendPort(e.target.value)}
                    placeholder={project.frontend_port_override ? "" : (detectedFrontendPort || "")}
                    className="w-full bg-slate-950 border border-slate-800 rounded px-3 py-2 focus:outline-none focus:ring-2 focus:ring-indigo-500 text-slate-200"
                  />
                  <span className="text-[11px] text-slate-500">Detected: {detectedFrontendPort || "none"}</span>
                </label>
                <label className="space-y-1 text-sm text-slate-300">
                  <span className="text-xs text-slate-500">Backend Port</span>
                  <input
                    type="number"
                    value={backendPort}
                    onChange={(e) => setBackendPort(e.target.value)}
                    placeholder={project.backend_port || ""}
                    className="w-full bg-slate-950 border border-slate-800 rounded px-3 py-2 focus:outline-none focus:ring-2 focus:ring-indigo-500 text-slate-200"
                  />
                  <span className="text-[11px] text-slate-500">Detected: {project.backend_port || "none"}</span>
                </label>
              </div>
            </div>

            {/* Tags */}
            <div>
                <h3 className="text-sm font-medium text-slate-500 uppercase tracking-wider mb-3">Tech Stack</h3>
                <div className="flex flex-wrap gap-2">
                    {project.tags.map(tag => (
                        <span key={tag} className="px-3 py-1 rounded bg-slate-800 text-slate-300 border border-slate-700 text-sm font-mono">
                            {tag}
                        </span>
                    ))}
                </div>
            </div>

            {/* Actions Grid - Desktop Only */}
            <div className="hidden md:block">
                <h3 className="text-sm font-medium text-slate-500 uppercase tracking-wider mb-3">Developer Actions</h3>
                <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
                    <button onClick={() => onLaunch(project.vscode_workspace_file || project.path, 'vscode')} className="flex flex-col items-center justify-center gap-2 p-4 rounded-lg bg-slate-900 border border-slate-800 hover:bg-slate-800 hover:border-slate-600 transition-all text-slate-300 font-medium text-sm">
                        <Code2 size={20} className="text-blue-400"/>
                        <span>VS Code</span>
                    </button>
                    <button onClick={() => onLaunch(project.path, 'terminal')} className="flex flex-col items-center justify-center gap-2 p-4 rounded-lg bg-slate-900 border border-slate-800 hover:bg-slate-800 hover:border-slate-600 transition-all text-slate-300 font-medium text-sm">
                        <Terminal size={20} className="text-emerald-400"/>
                        <span>Terminal</span>
                    </button>
                    <button onClick={() => onLaunch(project.path, 'wsl')} className="flex flex-col items-center justify-center gap-2 p-4 rounded-lg bg-slate-900 border border-slate-800 hover:bg-slate-800 hover:border-slate-600 transition-all text-slate-300 font-medium text-sm">
                        <Command size={20} className="text-orange-400"/>
                        <span>WSL</span>
                    </button>
                    <button onClick={() => onLaunch(project.path, 'explorer')} className="flex flex-col items-center justify-center gap-2 p-4 rounded-lg bg-slate-900 border border-slate-800 hover:bg-slate-800 hover:border-slate-600 transition-all text-slate-300 font-medium text-sm">
                        <Folder size={20} className="text-yellow-400"/>
                        <span>Explorer</span>
                    </button>
                </div>
            </div>

            {/* Custom Links Section */}
            <div>
                 <div className="flex items-center justify-between mb-3">
                    <h3 className="text-sm font-medium text-slate-500 uppercase tracking-wider">Project Links</h3>
                    <button onClick={() => setIsAddingLink(!isAddingLink)} className="text-indigo-400 hover:text-indigo-300 text-xs flex items-center gap-1">
                        <Plus size={14} /> Add Link
                    </button>
                 </div>
                 
                 {isAddingLink && (
                    <div className="mb-4 p-3 bg-slate-900 rounded border border-slate-800 flex flex-col gap-2">
                        <input 
                            value={newLinkName} onChange={e => setNewLinkName(e.target.value)}
                            placeholder="Link Name (e.g. Jira, Figma)"
                            className="bg-slate-950 border border-slate-800 rounded px-2 py-1 text-sm text-white focus:border-indigo-500 outline-none"
                        />
                        <input 
                            value={newLinkUrl} onChange={e => setNewLinkUrl(e.target.value)}
                            placeholder="https://..."
                            className="bg-slate-950 border border-slate-800 rounded px-2 py-1 text-sm text-white focus:border-indigo-500 outline-none"
                        />
                        <div className="flex justify-end gap-2">
                            <button onClick={() => setIsAddingLink(false)} className="text-xs text-slate-500">Cancel</button>
                            <button onClick={addLink} disabled={loading} className="text-xs bg-indigo-600 text-white px-2 py-1 rounded">Save</button>
                        </div>
                    </div>
                 )}

                 <div className="space-y-2">
                    {project.custom_links?.map((link) => (
                        <div key={link.name} className="flex items-center justify-between p-3 bg-slate-900 rounded border border-slate-800 hover:border-slate-700 transition-colors">
                             <div className="flex items-center gap-3">
                                 <Link size={16} className="text-indigo-400 shrink-0"/>
                                 <a href={formatUrl(link.url, project)} target="_blank" rel="noreferrer" className="text-sm text-indigo-300 hover:text-white hover:underline font-medium">{link.name}</a>
                             </div>
                             <button onClick={() => removeLink(link.name)} className="text-slate-600 hover:text-red-400 p-1">
                                 <Trash2 size={14} />
                             </button>
                        </div>
                    ))}
                    {(!project.custom_links || project.custom_links.length === 0) && !isAddingLink && (
                        <div className="text-xs text-slate-600 italic">No custom links added.</div>
                    )}
                 </div>
            </div>

            {/* Custom Docs Section */}
            <div>
                 <div className="flex items-center justify-between mb-3">
                    <h3 className="text-sm font-medium text-slate-500 uppercase tracking-wider">Custom Documentation</h3>
                    <button onClick={() => setIsAddingDoc(!isAddingDoc)} className="text-emerald-400 hover:text-emerald-300 text-xs flex items-center gap-1">
                        <Plus size={14} /> Add Doc
                    </button>
                 </div>

                 {isAddingDoc && (
                    <div className="mb-4 p-3 bg-slate-900 rounded border border-slate-800 flex flex-col gap-2">
                        <input 
                            value={newDocName} onChange={e => setNewDocName(e.target.value)}
                            placeholder="Doc Name (e.g. Deployment Guide)"
                            className="bg-slate-950 border border-slate-800 rounded px-2 py-1 text-sm text-white focus:border-emerald-500 outline-none"
                        />
                        <input 
                            value={newDocPath} onChange={e => setNewDocPath(e.target.value)}
                            placeholder="/absolute/path/to/file.md"
                            className="bg-slate-950 border border-slate-800 rounded px-2 py-1 text-sm text-white focus:border-emerald-500 outline-none"
                        />
                        <div className="flex justify-end gap-2">
                            <button onClick={() => setIsAddingDoc(false)} className="text-xs text-slate-500">Cancel</button>
                            <button onClick={addDoc} disabled={loading} className="text-xs bg-emerald-600 text-white px-2 py-1 rounded">Save</button>
                        </div>
                    </div>
                 )}

                 <div className="space-y-2">
                    {project.custom_docs?.map((doc) => (
                        <div key={doc.name} className="flex items-center justify-between p-3 bg-slate-900 rounded border border-slate-800 hover:border-slate-700 transition-colors">
                             <div className="flex items-center gap-3 overflow-hidden">
                                 <FileText size={16} className="text-emerald-400 shrink-0"/>
                                 <button onClick={() => onViewDoc(doc)} className="text-sm text-slate-300 hover:text-white hover:underline font-mono truncate text-left">
                                    {doc.name}
                                 </button>
                             </div>
                             <button onClick={() => removeDoc(doc.name)} className="text-slate-600 hover:text-red-400 p-1">
                                 <Trash2 size={14} />
                             </button>
                        </div>
                    ))}
                    {(!project.custom_docs || project.custom_docs.length === 0) && !isAddingDoc && (
                        <div className="text-xs text-slate-600 italic">No custom documents added.</div>
                    )}
                 </div>
            </div>

            {/* Auto-Detected Documentation */}
            {project.docs.length > 0 && (
                <div>
                    <h3 className="text-sm font-medium text-slate-500 uppercase tracking-wider mb-3">Auto-Detected Docs ({project.docs.length})</h3>
                    <div className="space-y-2">
                        {project.docs.map((doc) => (
                            <div key={doc.name} className="flex items-center justify-between p-3 bg-slate-900 rounded border border-slate-800 hover:border-slate-700 transition-colors group">
                                <div className="flex items-center gap-3 overflow-hidden">
                                    {doc.type === 'link' ? <Link size={16} className="text-cyan-400 shrink-0"/> : 
                                     doc.type === 'openapi' ? <ExternalLink size={16} className="text-indigo-400 shrink-0"/> :
                                     <FileText size={16} className="text-slate-400 shrink-0"/>}
                                    <span className="text-sm text-slate-300 font-mono truncate">{doc.name}</span>
                                </div>
                                
                                {doc.type === 'link' ? (
                                   <a href={formatUrl(doc.path, project)} target="_blank" rel="noreferrer" className="text-xs text-cyan-400 hover:underline">Open Link</a>
                                ) : doc.type === 'markdown' ? (
                                    <button onClick={() => onViewDoc(doc)} className="text-xs text-blue-400 hover:underline">View Doc</button>
                                ) : (
                                    <button onClick={() => onLaunch(doc.path, 'vscode')} className="text-xs text-indigo-400 hover:underline">Open in Editor</button>
                                )}
                            </div>
                        ))}
                    </div>
                </div>
            )}

            {/* Danger Zone */}
            <div className="pt-6 border-t border-slate-800/50 mt-4">
                {!deleteConfirm ? (
                    <button 
                        onClick={() => setDeleteConfirm(true)} 
                        className="flex items-center gap-2 text-red-400 hover:text-red-300 hover:bg-red-900/20 px-4 py-2 rounded-lg transition-colors text-sm font-medium w-full justify-center md:w-auto"
                    >
                        <Trash2 size={16} />
                        Remove Project
                    </button>
                ) : (
                    <div className="flex items-center gap-3 justify-center md:justify-start bg-red-900/20 p-2 rounded-lg border border-red-900/30">
                        <span className="text-sm text-red-200 font-medium">Are you sure?</span>
                        <button 
                            onClick={onDelete}
                            className="px-3 py-1 bg-red-600 hover:bg-red-500 text-white text-xs rounded font-bold transition-colors"
                        >
                            Confirm
                        </button>
                        <button 
                            onClick={() => setDeleteConfirm(false)}
                            className="px-3 py-1 bg-slate-700 hover:bg-slate-600 text-slate-200 text-xs rounded transition-colors"
                        >
                            Cancel
                        </button>
                    </div>
                )}
            </div>
        </div>
      </div>
    </div>
  );
}
