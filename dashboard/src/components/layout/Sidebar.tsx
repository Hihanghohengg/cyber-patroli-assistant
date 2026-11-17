import React from 'react';
import { NavLink } from 'react-router-dom';
import {
  LayoutDashboard,
  Flame,
  Search,
  BarChart2,
  ExternalLink,
  Cpu,
  Chrome,
  Terminal,
} from 'lucide-react';
import { useAuth } from '../../context/AuthContext';

export const Sidebar: React.FC = () => {
  const { user } = useAuth();
  const isAdmin = user?.role === 'ADMIN';

  const operationalItems = [
    {
      to: '/',
      label: 'Ringkasan',
      icon: <LayoutDashboard className="w-4 h-4" />,
    },
    {
      to: '/trending',
      label: 'Radar Isu',
      icon: <Flame className="w-4 h-4" />,
    },
    {
      to: '/contents',
      label: 'Arsip Temuan',
      icon: <Search className="w-4 h-4" />,
    },
    {
      to: '/analytics',
      label: 'Telemetri',
      icon: <BarChart2 className="w-4 h-4" />,
    },
    {
      to: '/assistant',
      label: 'Ekstensi Peramban',
      icon: <Chrome className="w-4 h-4" />,
    },
  ];

  const governanceItems = isAdmin
    ? [
        {
          to: '/curation',
          label: 'Kurasi & HITL',
          icon: <Cpu className="w-4 h-4" />,
        },
      ]
    : [];

  return (
    <aside className="w-56 border-r border-slate-200 dark:border-white/[0.06] bg-white dark:bg-[#0A0D14] flex flex-col justify-between shrink-0 h-[calc(100vh-3rem)] sticky top-12 transition-colors duration-150 z-30">
      <div className="p-3 space-y-4">
        {/* Operasional Nav */}
        <div>
          <div className="px-2 mb-1.5">
            <span className="text-[10px] font-semibold tracking-wider uppercase text-slate-400 dark:text-slate-500 font-mono">
              Operasional
            </span>
          </div>
          <nav className="space-y-0.5">
            {operationalItems.map((item) => (
              <NavLink
                key={item.to}
                to={item.to}
                className={({ isActive }) =>
                  `flex items-center gap-2.5 px-2.5 py-1.5 rounded-md text-xs transition-colors relative ${
                    isActive
                      ? 'bg-blue-500/10 text-blue-600 dark:text-blue-400 font-semibold border-l-2 border-blue-500'
                      : 'text-slate-600 dark:text-slate-400 hover:text-slate-900 dark:hover:text-slate-200 hover:bg-slate-100 dark:hover:bg-white/[0.04]'
                  }`
                }
              >
                {({ isActive }) => (
                  <>
                    <div
                      className={`transition-colors ${
                        isActive
                          ? 'text-blue-600 dark:text-blue-400'
                          : 'text-slate-400 dark:text-slate-500'
                      }`}
                    >
                      {item.icon}
                    </div>
                    <span className="truncate">{item.label}</span>
                  </>
                )}
              </NavLink>
            ))}
          </nav>
        </div>

        {/* Tata Kelola (Admin) */}
        {governanceItems.length > 0 && (
          <div>
            <div className="px-2 mb-1.5">
              <span className="text-[10px] font-semibold tracking-wider uppercase text-slate-400 dark:text-slate-500 font-mono">
                Tata Kelola
              </span>
            </div>
            <nav className="space-y-0.5">
              {governanceItems.map((item) => (
                <NavLink
                  key={item.to}
                  to={item.to}
                  className={({ isActive }) =>
                    `flex items-center gap-2.5 px-2.5 py-1.5 rounded-md text-xs transition-colors relative ${
                      isActive
                        ? 'bg-blue-500/10 text-blue-600 dark:text-blue-400 font-semibold border-l-2 border-blue-500'
                        : 'text-slate-600 dark:text-slate-400 hover:text-slate-900 dark:hover:text-slate-200 hover:bg-slate-100 dark:hover:bg-white/[0.04]'
                    }`
                  }
                >
                  {({ isActive }) => (
                    <>
                      <div
                        className={`transition-colors ${
                          isActive
                            ? 'text-blue-600 dark:text-blue-400'
                            : 'text-slate-400 dark:text-slate-500'
                        }`}
                      >
                        {item.icon}
                      </div>
                      <span className="truncate">{item.label}</span>
                    </>
                  )}
                </NavLink>
              ))}
            </nav>
          </div>
        )}
      </div>

      {/* Minimal Footer */}
      <div className="p-3 border-t border-slate-200 dark:border-white/[0.06] flex items-center justify-between text-[10.5px] text-slate-500 dark:text-slate-400 font-mono">
        <div className="flex items-center gap-1.5">
          <Terminal className="w-3 h-3 text-slate-400" />
          <span>TILIK v5.0</span>
        </div>
        <a
          href="http://localhost:8000/docs"
          target="_blank"
          rel="noreferrer"
          className="flex items-center gap-1 text-slate-500 hover:text-blue-400 transition-colors"
          title="Dokumentasi Swagger API"
        >
          <span>Docs</span>
          <ExternalLink className="w-2.5 h-2.5" />
        </a>
      </div>
    </aside>
  );
};
