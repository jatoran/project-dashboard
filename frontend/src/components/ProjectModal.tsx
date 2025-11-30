import { Dialog } from "@/types"; // You might need to adjust types location
import { Project } from "@/types";
import { X, Terminal, Code2, Command, Folder, Globe, Link, ExternalLink, FileText, Copy, Check } from "lucide-react";
import { useState, useEffect } from "react";

interface ProjectModalProps {
  project: Project;
  isOpen: boolean;
  onClose: () => void;
  onLaunch: (path: string, type: string) => void;
  onViewDoc: (doc: {path: string, name: string}) => void;
  formatUrl: (url: string) => string;
  status: boolean | null;
}

export default function ProjectModal({ project, isOpen, onClose, onLaunch, onViewDoc, formatUrl, status }: ProjectModalProps) {
  const [copiedPath, setCopiedPath] = useState(false);

  // Handle Escape Key
  useEffect(() => {
    const handleEsc = (e: KeyboardEvent) => {
        if (e.key === 'Escape') onClose();
    };
    if (isOpen) window.addEventListener('keydown', handleEsc);
    return () => window.removeEventListener('keydown', handleEsc);
  }, [isOpen, onClose]);

  if (!isOpen) return null;

  const handleCopyPath = async () => {
    try {
        await navigator.clipboard.writeText(project.path);
        setCopiedPath(true);
        setTimeout(() => setCopiedPath(false), 2000);
    } catch (err) {
        // Fallback handled in parent or ignored for simplicity here
    }
  };

  return (
    <div 
      className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/60 backdrop-blur-sm animate-in fade-in duration-200"
      onClick={onClose} // Click backdrop to close
    >
      <div 
        className="relative w-full max-w-2xl bg-slate-900 border border-slate-800 rounded-xl shadow-2xl overflow-hidden flex flex-col max-h-[90vh] animate-in zoom-in-95 duration-200"
        onClick={(e) => e.stopPropagation()} // Prevent closing when clicking inside modal
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
                       href={formatUrl(project.frontend_url)}
                       target="_blank"
                       rel="noopener noreferrer"
                       className="flex items-center gap-2 bg-indigo-600 hover:bg-indigo-500 text-white px-4 py-2 rounded-lg font-medium transition-colors"
                    >
                        <Globe size={18} />
                        Open App
                    </a>
                </div>
            )}

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
                    <button onClick={() => onLaunch(project.vscode_workspace_file || project.path, 'vscode')} className="action-btn">
                        <Code2 size={20} className="text-blue-400"/>
                        <span>VS Code</span>
                    </button>
                    <button onClick={() => onLaunch(project.path, 'terminal')} className="action-btn">
                        <Terminal size={20} className="text-emerald-400"/>
                        <span>Terminal</span>
                    </button>
                    <button onClick={() => onLaunch(project.path, 'wsl')} className="action-btn">
                        <Command size={20} className="text-orange-400"/>
                        <span>WSL</span>
                    </button>
                    <button onClick={() => onLaunch(project.path, 'explorer')} className="action-btn">
                        <Folder size={20} className="text-yellow-400"/>
                        <span>Explorer</span>
                    </button>
                </div>
            </div>

            {/* Documentation */}
            {project.docs.length > 0 && (
                <div>
                    <h3 className="text-sm font-medium text-slate-500 uppercase tracking-wider mb-3">Documentation ({project.docs.length})</h3>
                    <div className="space-y-2">
                        {project.docs.map((doc) => (
                            <div key={doc.name} className="flex items-center justify-between p-3 bg-slate-900 rounded border border-slate-800 hover:border-slate-700 transition-colors group">
                                <div className="flex items-center gap-3 overflow-hidden">
                                    {doc.type === 'link' ? <Link size={16} className="text-emerald-400 shrink-0"/> : 
                                     doc.type === 'openapi' ? <ExternalLink size={16} className="text-indigo-400 shrink-0"/> :
                                     <FileText size={16} className="text-slate-400 shrink-0"/>}
                                    <span className="text-sm text-slate-300 font-mono truncate">{doc.name}</span>
                                </div>
                                
                                {doc.type === 'link' ? (
                                   <a href={formatUrl(doc.path)} target="_blank" rel="noreferrer" className="text-xs text-emerald-400 hover:underline">Open Link</a>
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
        </div>
      </div>
      <style jsx>{`
        .action-btn {
            @apply flex flex-col items-center justify-center gap-2 p-4 rounded-lg bg-slate-900 border border-slate-800 hover:bg-slate-800 hover:border-slate-600 transition-all text-slate-300 font-medium text-sm;
        }
      `}</style>
    </div>
  );
}
