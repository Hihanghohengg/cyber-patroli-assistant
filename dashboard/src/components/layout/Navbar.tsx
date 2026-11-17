import React from 'react';
import { useLocation } from 'react-router-dom';
import { useAuth } from '../../context/AuthContext';
import { Shield, LogOut, ChevronRight } from 'lucide-react';
import { ThemeToggle } from '../common/ThemeToggle';

export const Navbar: React.FC = () => {
  const { user, logout } = useAuth();
  const location = useLocation();

  const getPageTitle = (pathname: string) => {
    if (pathname === '/') return 'Ringkasan Operasi';
    if (pathname.startsWith('/trending')) return 'Radar Isu';
    if (pathname.startsWith('/contents')) return 'Arsip Temuan';
    return 'Workstation';
  };

  const currentTitle = getPageTitle(location.pathname);

  return (
    <header className="h-12 border-b border-slate-200 dark:border-white/[0.06] bg-white/95 dark:bg-[#090A0F]/95 backdrop-blur-md px-4 sm:px-6 flex items-center justify-between sticky top-0 z-40 transition-colors duration-150 specular-border">
      {/* Brand & Breadcrumbs */}
      <div className="flex items-center gap-3">
        <div className="flex items-center gap-2">
          <div className="w-6 h-6 rounded-md bg-blue-600 flex items-center justify-center text-white shadow-sm shadow-blue-500/20">
            <Shield className="w-3.5 h-3.5" />
          </div>
          <span className="text-xs font-bold tracking-tight text-slate-900 dark:text-white font-mono">
            TILIK
          </span>
        </div>

        <ChevronRight className="w-3.5 h-3.5 text-slate-400 dark:text-slate-600" />

        <div className="flex items-center gap-2">
          <span className="text-xs font-semibold text-slate-700 dark:text-slate-200">
            {currentTitle}
          </span>
          {/* Subtle Live Dot */}
          <span className="hidden sm:inline-flex items-center gap-1.5 px-2 py-0.5 rounded-full bg-emerald-500/10 text-emerald-600 dark:text-emerald-400 border border-emerald-500/20 text-[10px] font-mono font-medium">
            <span className="w-1.5 h-1.5 rounded-full bg-emerald-500 animate-pulse" />
            Online
          </span>
        </div>
      </div>

      {/* Right Controls: Theme Segment & Operator Profile */}
      <div className="flex items-center gap-2.5">
        <ThemeToggle />

        {/* User Profile Pill */}
        <div className="flex items-center gap-2 pl-2.5 border-l border-slate-200 dark:border-white/[0.06]">
          <div className="flex items-center gap-2">
            <div className="w-6 h-6 rounded bg-slate-100 dark:bg-white/[0.06] border border-slate-200 dark:border-white/[0.08] flex items-center justify-center text-blue-600 dark:text-blue-400 font-bold text-[10px] font-mono">
              {user?.username ? user.username.slice(0, 2).toUpperCase() : 'OP'}
            </div>
            <div className="hidden sm:block text-left leading-none">
              <span className="text-xs font-semibold text-slate-800 dark:text-slate-200">
                {user?.full_name || user?.username || 'Operator'}
              </span>
            </div>
          </div>

          <button
            onClick={logout}
            title="Keluar dari sesi"
            className="p-1 rounded text-slate-400 hover:text-rose-500 hover:bg-rose-500/10 transition-colors"
          >
            <LogOut className="w-3.5 h-3.5" />
          </button>
        </div>
      </div>
    </header>
  );
};
