import React, { useState, useEffect } from 'react';
import { useAuth } from '../../context/AuthContext';
import { Shield, Radio, LogOut, User as UserIcon, RefreshCw } from 'lucide-react';
import { apiClient } from '../../api/client';

export const Navbar: React.FC = () => {
  const { user, logout } = useAuth();
  const [timeStr, setTimeStr] = useState<string>('');
  const [isRecalculating, setIsRecalculating] = useState<boolean>(false);
  const [recalcMsg, setRecalcMsg] = useState<string | null>(null);

  useEffect(() => {
    const updateTime = () => {
      const now = new Date();
      setTimeStr(
        now.toLocaleDateString('id-ID', {
          weekday: 'short',
          day: '2-digit',
          month: 'short',
          year: 'numeric',
          hour: '2-digit',
          minute: '2-digit',
          second: '2-digit',
        }) + ' WIB'
      );
    };
    updateTime();
    const timer = setInterval(updateTime, 1000);
    return () => clearInterval(timer);
  }, []);

  const handleRecalculate = async () => {
    setIsRecalculating(true);
    setRecalcMsg(null);
    try {
      const res = await apiClient.trending.recalculate();
      setRecalcMsg(res.message);
      setTimeout(() => setRecalcMsg(null), 4000);
    } catch (e) {
      setRecalcMsg('Gagal menghitung skor');
    } finally {
      setIsRecalculating(false);
    }
  };

  return (
    <header className="h-16 border-b border-slate-800 bg-[#070b14]/85 backdrop-blur-md px-6 flex items-center justify-between sticky top-0 z-40">
      <div className="flex items-center gap-4">
        <div className="flex items-center gap-2">
          <div className="w-9 h-9 rounded-lg bg-gradient-to-tr from-cyan-600 to-blue-500 flex items-center justify-center shadow-lg shadow-cyan-500/20">
            <Shield className="w-5 h-5 text-white" />
          </div>
          <div>
            <h1 className="text-sm font-bold tracking-tight text-white flex items-center gap-2">
              CYBER PATROL <span className="text-cyan-400 font-mono text-xs px-1.5 py-0.5 rounded bg-cyan-950/70 border border-cyan-500/30">INTEL</span>
            </h1>
            <p className="text-[10px] text-slate-400 font-mono">Social Intelligence & Trending Radar</p>
          </div>
        </div>

        {/* Live Status indicator */}
        <div className="hidden md:flex items-center gap-2 px-3 py-1 rounded-full bg-slate-900 border border-slate-800 text-xs">
          <span className="w-2 h-2 rounded-full bg-emerald-400 animate-pulse" />
          <span className="text-slate-300 font-mono text-[11px]">SISTEM AKTIF</span>
        </div>
      </div>

      <div className="flex items-center gap-4">
        {/* Quick manual recalculation button (ADMIN only per FR-12/NFR-05) */}
        {user?.role === 'ADMIN' && (
          <button
            onClick={handleRecalculate}
            disabled={isRecalculating}
            title="Hitung ulang trending score"
            className="hidden sm:flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-medium bg-slate-900 hover:bg-slate-800 text-cyan-400 border border-slate-800 hover:border-cyan-500/40 transition-colors disabled:opacity-50"
          >
            <RefreshCw className={`w-3.5 h-3.5 ${isRecalculating ? 'animate-spin' : ''}`} />
            {isRecalculating ? 'Menghitung...' : 'Sinkronkan Skor'}
          </button>
        )}

        {recalcMsg && (
          <span className="text-xs text-emerald-400 font-mono animate-fade-in hidden lg:inline">
            {recalcMsg}
          </span>
        )}

        {/* Clock */}
        <div className="hidden lg:block text-xs font-mono text-slate-400 bg-slate-900/50 px-3 py-1 rounded border border-slate-800">
          {timeStr}
        </div>

        {/* User Profile */}
        <div className="flex items-center gap-3 pl-3 border-l border-slate-800">
          <div className="flex items-center gap-2.5">
            <div className="w-8 h-8 rounded-full bg-slate-800 border border-slate-700 flex items-center justify-center text-cyan-300 font-bold text-xs font-mono">
              {user?.username ? user.username.slice(0, 2).toUpperCase() : 'PS'}
            </div>
            <div className="hidden sm:block text-left">
              <div className="text-xs font-semibold text-slate-200">{user?.full_name || user?.username || 'Petugas'}</div>
              <div className="text-[10px] font-mono uppercase">
                {user?.role === 'ADMIN' ? (
                  <span className="text-emerald-400 font-bold">ADMIN (Penuh)</span>
                ) : (
                  <span className="text-cyan-400 font-medium">USER (Read-Only)</span>
                )}
              </div>
            </div>
          </div>

          <button
            onClick={logout}
            title="Keluar"
            className="p-1.5 rounded-lg text-slate-400 hover:text-rose-400 hover:bg-rose-500/10 transition-colors"
          >
            <LogOut className="w-4 h-4" />
          </button>
        </div>
      </div>
    </header>
  );
};
