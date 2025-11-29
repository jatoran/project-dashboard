"use client";

import { useState, useEffect } from "react";
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";
import { X, Copy, Check } from "lucide-react";

interface DocViewerProps {
  isOpen: boolean;
  onClose: () => void;
  filePath: string | null;
  fileName: string | null;
}

export default function DocViewer({ isOpen, onClose, filePath, fileName }: DocViewerProps) {
  const [content, setContent] = useState<string>("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [copied, setCopied] = useState(false);

  useEffect(() => {
    if (isOpen && filePath) {
      fetchContent();
    } else {
        setContent(""); // Clear content on close
    }
  }, [isOpen, filePath]);

  const fetchContent = async () => {
    if (!filePath) return;
    setLoading(true);
    setError(null);
    try {
      // Encode the path to handle spaces/special chars
      const res = await fetch(`/api/files/content?path=${encodeURIComponent(filePath)}`);
      if (!res.ok) throw new Error("Failed to load file");
      const data = await res.json();
      setContent(data.content);
    } catch (err) {
      setError("Could not load documentation content.");
    } finally {
      setLoading(false);
    }
  };

  const handleCopy = () => {
      if (content) {
          navigator.clipboard.writeText(content);
          setCopied(true);
          setTimeout(() => setCopied(false), 2000);
      }
  }

  if (!isOpen) return null;

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 sm:p-6">
      <div 
        className="absolute inset-0 bg-black/60 backdrop-blur-sm" 
        onClick={onClose}
      />
      <div className="relative w-full max-w-4xl max-h-[85vh] bg-slate-900 border border-slate-800 rounded-xl shadow-2xl flex flex-col overflow-hidden">
        
        {/* Header */}
        <div className="flex items-center justify-between px-6 py-4 border-b border-slate-800 bg-slate-900/50">
          <h2 className="text-lg font-semibold text-white truncate flex-1 pr-4 font-mono">
             {fileName}
          </h2>
          <div className="flex items-center gap-2">
            <button 
                onClick={handleCopy}
                className="p-2 text-slate-400 hover:text-white hover:bg-slate-800 rounded-lg transition-colors"
                title="Copy raw markdown"
            >
                {copied ? <Check size={18} className="text-green-400" /> : <Copy size={18} />}
            </button>
            <button 
              onClick={onClose}
              className="p-2 text-slate-400 hover:text-white hover:bg-slate-800 rounded-lg transition-colors"
            >
              <X size={20} />
            </button>
          </div>
        </div>

        {/* Content */}
        <div className="flex-1 overflow-y-auto p-6 bg-slate-950">
          {loading ? (
            <div className="flex items-center justify-center h-full text-slate-500 animate-pulse">
              Loading documentation...
            </div>
          ) : error ? (
            <div className="flex items-center justify-center h-full text-red-400">
              {error}
            </div>
          ) : (
            <div className="prose prose-invert prose-sm sm:prose-base max-w-none prose-pre:bg-slate-900 prose-pre:border prose-pre:border-slate-800">
              <ReactMarkdown remarkPlugins={[remarkGfm]}>
                {content}
              </ReactMarkdown>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
