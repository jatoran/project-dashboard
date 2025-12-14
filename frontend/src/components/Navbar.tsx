import { Menu, X, LayoutGrid, Activity, Server, HardDrive, ScrollText, Globe } from "lucide-react";
import { useState } from "react";

interface NavbarProps {
  activeTab: string;
  onTabChange: (tab: string) => void;
}

export default function Navbar({ activeTab, onTabChange }: NavbarProps) {
  const [isMobileMenuOpen, setIsMobileMenuOpen] = useState(false);

  const tabs = [
    { id: 'projects', label: 'Projects', icon: LayoutGrid },
    { id: 'links', label: 'Links', icon: Globe },
    { id: 'dashboard', label: 'Proxmox Dashboard', icon: Activity },
    { id: 'scrutiny', label: 'Scrutiny Drives', icon: HardDrive },
    { id: 'host', label: 'PC Monitoring', icon: Server },
    { id: 'services', label: 'PC Services', icon: ScrollText },
  ];

  const handleTabClick = (id: string) => {
    onTabChange(id);
    setIsMobileMenuOpen(false);
  };

  return (
    <>
      {/* Top Fixed Bar */}
      <nav className="fixed top-0 left-0 right-0 h-16 bg-slate-950 border-b border-slate-800 z-40 flex items-center justify-between px-4 md:px-8">

        {/* Logo / Brand */}
        <div className="flex items-center gap-3">
          <div className="w-8 h-8 bg-indigo-600 rounded-lg flex items-center justify-center shadow-lg shadow-indigo-900/20">
            <LayoutGrid className="text-white w-5 h-5" />
          </div>
          <span className="font-bold text-white tracking-tight text-lg hidden md:block">DevConsole</span>
        </div>

        {/* Desktop Tabs */}
        <div className="hidden md:flex items-center gap-1 bg-slate-900/50 p-1 rounded-lg border border-slate-800">
          {tabs.map(tab => (
            <button
              key={tab.id}
              onClick={() => handleTabClick(tab.id)}
              className={`flex items-center gap-2 px-4 py-2 rounded-md text-sm font-medium transition-all ${activeTab === tab.id
                ? 'bg-slate-800 text-white shadow-sm'
                : 'text-slate-400 hover:text-slate-200 hover:bg-slate-800/50'
                }`}
            >
              <tab.icon size={16} />
              {tab.label}
            </button>
          ))}
        </div>

        {/* Mobile Hamburger */}
        <button
          className="md:hidden p-2 text-slate-400 hover:text-white"
          onClick={() => setIsMobileMenuOpen(true)}
        >
          <Menu size={24} />
        </button>
      </nav>

      {/* Mobile Sidebar / Drawer */}
      {isMobileMenuOpen && (
        <div className="fixed inset-0 z-50 md:hidden">
          {/* Backdrop */}
          <div
            className="absolute inset-0 bg-black/60 backdrop-blur-sm animate-in fade-in duration-200"
            onClick={() => setIsMobileMenuOpen(false)}
          />

          {/* Sidebar Content */}
          <div className="absolute top-0 right-0 bottom-0 w-64 bg-slate-900 border-l border-slate-800 p-6 shadow-2xl animate-in slide-in-from-right duration-300">
            <div className="flex justify-between items-center mb-8">
              <span className="font-bold text-white text-lg">Menu</span>
              <button onClick={() => setIsMobileMenuOpen(false)} className="p-1 text-slate-400 hover:text-white">
                <X size={24} />
              </button>
            </div>

            <div className="space-y-2">
              {tabs.map(tab => (
                <button
                  key={tab.id}
                  onClick={() => handleTabClick(tab.id)}
                  className={`w-full flex items-center gap-3 px-4 py-3 rounded-lg text-sm font-medium transition-all ${activeTab === tab.id
                    ? 'bg-indigo-600 text-white'
                    : 'text-slate-400 hover:bg-slate-800 hover:text-white'
                    }`}
                >
                  <tab.icon size={18} />
                  {tab.label}
                </button>
              ))}
            </div>
          </div>
        </div>
      )}

      {/* Spacer for fixed navbar */}
      <div className="h-16" />
    </>
  );
}
