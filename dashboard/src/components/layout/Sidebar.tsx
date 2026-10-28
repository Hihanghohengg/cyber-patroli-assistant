import React from 'react';
import { NavLink } from 'react-router-dom';
import {
  LayoutDashboard,
  Flame,
  Search,
  BarChart2,
  Bot,
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
      label: 'Ringkasan',
      icon: <LayoutDashboard className="w-4 h-4" />,
    },
    {
      to: '/trending',
      label: 'Trending Topics',
      icon: <Flame className="w-4 h-4" />,
    },
    {
      to: '/contents',
      label: 'Daftar Temuan',
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
            label: 'Pusat Kurasi',
            icon: <Database className="w-4 h-4" />,
          },
        ]
      : []),
  ];

  return (
    <aside className="w-60 border-r border-slate-800/80 bg-[#070b14]/80 flex flex-col justify-between shrink-0 h-[calc(100vh-4rem)] sticky top-16">
      <div className="p-3.5 space-y-4">
        <div>
          <span className="text-[10px] font-bold tracking-wider uppercase text-slate-500 px-3">
            Menu
          </span>
          <nav className="mt-2 space-y-1">
            {navItems.map((item) => (
              <NavLink
                key={item.to}
                to={item.to}
                className={({ isActive }) =>
                  `flex items-center gap-3 px-3 py-2 rounded-lg text-xs font-medium transition-all ${
                    isActive
                      ? 'bg-cyan-500/10 text-cyan-400 border border-cyan-500/30 shadow-sm shadow-cyan-500/10'
                      : 'text-slate-400 hover:text-slate-200 hover:bg-slate-900/60 border border-transparent'
                  }`
                }
              >
                {item.icon}
                {item.label}
              </NavLink>
            ))}
          </nav>
        </div>
      </div>

      <div className="p-3.5 border-t border-slate-800/60">
        <div className="flex items-center justify-between text-[11px] text-slate-500 font-mono">
          <span>Cyber Patrol</span>
          <a
            href="http://localhost:8000/docs"
            target="_blank"
            rel="noreferrer"
            className="flex items-center gap-1 hover:text-cyan-400 transition-colors"
          >
            <span>API Docs</span>
            <ExternalLink className="w-3 h-3" />
          </a>
        </div>
      </div>
    </aside>
  );
};
