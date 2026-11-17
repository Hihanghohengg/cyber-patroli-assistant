import React from 'react';
import { useAuth } from '../../context/AuthContext';
import { Shield, LogOut } from 'lucide-react';
import { ThemeToggle } from '../common/ThemeToggle';

export const Navbar: React.FC = () => {
  const { user, logout } = useAuth();

  return (
    <header className="h-14 border-b border-slate-200 dark:border-slate-800 bg-white/95 dark:bg-[#0c121e]/95 backdrop-blur-md px-4 sm:px-6 flex items-center justify-between sticky top-0 z-40 transition-colors duration-200 specular-border">
      {/* Brand & Radar Telemetry */}
      <div className="flex items-center gap-3.5">
        <div className="flex items-center gap-2.5">
          <div className="w-7 h-7 rounded-lg bg-blue-600 dark:bg-blue-600 flex items-center justify-center text-white shadow-sm">
            <Shield className="w-4 h-4" />
          </div>
          <div className="flex items-baseline gap-2">
            <span className="text-sm font-bold tracking-tight text-slate-900 dark:text-white font-mono">
              TILIK
            </span>
            <span className="hidden md:inline-block text-[11px] font-medium text-slate-500 dark:text-slate-400">
              Patroli Siber Terpadu v5.0
            </span>
          </div>
        </div>

        {/* Live Status Indicator */}
        <div className="hidden sm:flex items-center gap-2 px-2.5 py-0.5 rounded-full bg-slate-100 dark:bg-slate-900/90 border border-slate-200 dark:border-slate-800 text-[10px] font-mono">
          <span className="relative flex h-1.5 w-1.5">
            <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-emerald-400 opacity-75"></span>
            <span className="relative inline-flex rounded-full h-1.5 w-1.5 bg-emerald-500"></span>
          </span>
          <span className="text-slate-600 dark:text-slate-300 font-semibold tracking-wide">
            SISTEM ONLINE
          </span>
        </div>
      </div>

      {/* Right Controls: Minimalist Theme Segment & Operator Profile */}
      <div className="flex items-center gap-3">
        {/* Sleek Segmented Theme Switcher */}
        <ThemeToggle />

        {/* User Profile */}
        <div className="flex items-center gap-2.5 pl-2.5 border-l border-slate-200 dark:border-slate-800">
          <div className="flex items-center gap-2">
            <div className="w-7 h-7 rounded-md bg-slate-100 dark:bg-slate-800 border border-slate-200 dark:border-slate-700 flex items-center justify-center text-blue-600 dark:text-blue-400 font-bold text-xs font-mono">
              {user?.username ? user.username.slice(0, 2).toUpperCase() : 'OP'}
            </div>
            <div className="hidden sm:block text-left leading-tight">
              <div className="text-xs font-semibold text-slate-800 dark:text-slate-200">
                {user?.full_name || user?.username || 'Petugas'}
              </div>
              <div className="text-[10px] text-slate-500 dark:text-slate-400 font-mono">
                {user?.role || 'OPERATOR'}
              </div>
            </div>
          </div>

          <button
            onClick={logout}
            title="Keluar dari sesi"
            className="p-1.5 rounded-md text-slate-400 hover:text-rose-600 hover:bg-rose-50 dark:hover:text-rose-400 dark:hover:bg-rose-500/10 border border-transparent transition-all"
          >
            <LogOut className="w-4 h-4" />
          </button>
        </div>
      </div>
    </header>
  );
};
