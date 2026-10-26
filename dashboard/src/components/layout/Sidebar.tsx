import React from 'react';
import { NavLink } from 'react-router-dom';
import {
  LayoutDashboard,
  Flame,
  Search,
  BarChart2,
  Send,
  ExternalLink,
  ShieldAlert,
  Database,
} from 'lucide-react';
import { useAuth } from '../../context/AuthContext';

export const Sidebar: React.FC = () => {
  const { user } = useAuth();
  const isAdmin = user?.role === 'ADMIN';

  const navItems = [
    {
      to: '/',
      label: 'Ringkasan Proposal',
      icon: <LayoutDashboard className="w-4 h-4" />,
    },
    {
      to: '/trending',
      label: 'Trending Topics',
      icon: <Flame className="w-4 h-4" />,
    },
    {
      to: '/contents',
      label: 'Content Explorer',
      icon: <Search className="w-4 h-4" />,
    },
    {
      to: '/analytics',
      label: 'Statistik & Tren',
      icon: <BarChart2 className="w-4 h-4" />,
    },
    ...(isAdmin
      ? [
          {
            to: '/curation',
            label: 'Admin: RAG & Entitas',
            icon: <Database className="w-4 h-4" />,
          },
        ]
      : []),
  ];

  return (
    <aside className="w-64 border-r border-slate-800 bg-[#070b14]/60 flex flex-col justify-between shrink-0 h-[calc(100vh-4rem)] sticky top-16">
      <div className="p-4 space-y-6">
        <div>
          <span className="text-[10px] font-bold tracking-wider uppercase text-slate-500 px-3">
            Menu Operasional
          </span>
          <nav className="mt-2 space-y-1">
            {navItems.map((item) => (
              <NavLink
                key={item.to}
                to={item.to}
                className={({ isActive }) =>
                  `flex items-center gap-3 px-3 py-2.5 rounded-lg text-xs font-medium transition-all ${
                    isActive
                      ? 'bg-cyan-500/10 text-cyan-400 border border-cyan-500/30 shadow-sm shadow-cyan-500/10'
                      : 'text-slate-400 hover:text-slate-200 hover:bg-slate-900 border border-transparent'
                  }`
                }
              >
                {item.icon}
                {item.label}
              </NavLink>
            ))}
          </nav>
        </div>

        {/* Telegram Operasional Box */}
        <div className="p-3.5 rounded-xl bg-gradient-to-b from-slate-900 to-[#070b14] border border-slate-800">
          <div className="flex items-center gap-2 text-cyan-400 mb-2">
            <Send className="w-4 h-4" />
            <span className="text-xs font-semibold">Integrasi Bot Telegram</span>
          </div>
          <p className="text-[11px] text-slate-400 leading-relaxed">
            Patroli lapangan berjalan otomatis via Telegram Bot. Hasil triase tersinkron langsung ke dashboard ini.
          </p>
        </div>
      </div>

      <div className="p-4 border-t border-slate-800/80">
        <div className="flex items-center justify-between text-[11px] text-slate-500 font-mono">
          <span>v2.0 Social-Intel</span>
          <a
            href="http://localhost:8000/docs"
            target="_blank"
            rel="noreferrer"
            className="flex items-center gap-1 hover:text-cyan-400 transition-colors"
          >
            <span>FastAPI Docs</span>
            <ExternalLink className="w-3 h-3" />
          </a>
        </div>
      </div>
    </aside>
  );
};
