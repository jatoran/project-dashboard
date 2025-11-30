import { Project } from "@/types";
import { Globe, Code2, FileText, Terminal, Command, Folder } from "lucide-react";

interface ProjectCardProps {
  project: Project;
  status: boolean | null;
  onClick: () => void;
  onLaunch: (path: string, type: string) => void;
  formatUrl: (url: string) => string;
}

export default function ProjectCard({ project, status, onClick, onLaunch, formatUrl }: ProjectCardProps) {
  return (
    <div 
        className="group relative bg-slate-900 border border-slate-800 rounded-xl p-4 hover:border-slate-600 transition-all cursor-pointer shadow-sm hover:shadow-md"
        onClick={onClick}
    >
      {/* Status Indicator Dot (Absolute Top Right) */}
      <div className={`absolute top-4 right-4 w-2.5 h-2.5 rounded-full border border-slate-900/50 ${
        status === true ? "bg-green-500 shadow-[0_0_6px_rgba(34,197,94,0.6)]" : 
        status === false ? "bg-red-500" : 
        "bg-slate-700"
      }`} />

      <div className="flex flex-col h-full justify-between space-y-4">
          
          {/* Top Section: Name & Path */}
          <div>
            <h3 className="text-base font-bold text-white truncate pr-4 group-hover:text-indigo-400 transition-colors">
                {project.name}
            </h3>
            <p className="text-[10px] text-slate-500 font-mono truncate mt-1 opacity-70 group-hover:opacity-100 transition-opacity">
                {project.path}
            </p>
          </div>

          {/* Middle: Tags (Compact) */}
          <div className="flex flex-wrap gap-1 h-[24px] overflow-hidden">
             {project.tags.slice(0, 3).map(tag => (
                <span key={tag} className="text-[10px] px-1.5 py-0.5 rounded bg-slate-800 text-slate-400 border border-slate-700">
                    {tag}
                </span>
             ))}
             {project.tags.length > 3 && (
                <span className="text-[10px] px-1.5 py-0.5 rounded bg-slate-800 text-slate-500 border border-slate-700">+{project.tags.length - 3}</span>
             )}
          </div>

          {/* Bottom: Quick Info (Docs Count) & Primary Action */}
          <div className="flex items-center justify-between pt-2 border-t border-slate-800/50">
             <div className="flex items-center gap-1 text-xs text-slate-500">
                <FileText size={12} />
                <span>{project.docs.length} Docs</span>
             </div>

             {/* Primary Action Button - Stops propagation to prevent modal open */}
             <div className="flex gap-2">
                {/* Desktop-only extra actions */}
                <div className="hidden md:flex gap-2">
                    <button 
                        onClick={(e) => { e.stopPropagation(); onLaunch(project.path, 'terminal'); }}
                        className="p-1.5 rounded-md bg-slate-800 text-slate-400 hover:text-emerald-400 hover:bg-slate-700 transition-colors"
                        title="Open Terminal"
                    >
                        <Terminal size={14} />
                    </button>
                    <button 
                        onClick={(e) => { e.stopPropagation(); onLaunch(project.path, 'wsl'); }}
                        className="p-1.5 rounded-md bg-slate-800 text-slate-400 hover:text-orange-400 hover:bg-slate-700 transition-colors"
                        title="Open WSL"
                    >
                        <Command size={14} />
                    </button>
                    <button 
                        onClick={(e) => { e.stopPropagation(); onLaunch(project.path, 'explorer'); }}
                        className="p-1.5 rounded-md bg-slate-800 text-slate-400 hover:text-yellow-400 hover:bg-slate-700 transition-colors"
                        title="Open Explorer"
                    >
                        <Folder size={14} />
                    </button>
                </div>

                <button 
                    onClick={(e) => {
                        e.stopPropagation();
                        onLaunch(project.vscode_workspace_file || project.path, 'vscode');
                    }}
                    className="p-1.5 rounded-md bg-slate-800 text-slate-400 hover:text-blue-400 hover:bg-slate-700 transition-colors"
                    title="Open Code"
                >
                    <Code2 size={14} />
                </button>
                {project.frontend_url && (
                     <a 
                        href={formatUrl(project.frontend_url)}
                        target="_blank"
                        rel="noopener noreferrer"
                        onClick={(e) => e.stopPropagation()}
                        className="p-1.5 rounded-md bg-indigo-900/30 text-indigo-400 hover:bg-indigo-600 hover:text-white transition-colors"
                        title="Open App"
                     >
                        <Globe size={14} />
                     </a>
                )}
             </div>
          </div>
      </div>
    </div>
  );
}
