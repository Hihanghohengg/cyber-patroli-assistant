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
    {
      to: '/assistant',
      label: 'Ekstensi Browser',
      icon: <Chrome className="w-4 h-4" />,
    },
  ];

  const governanceItems = isAdmin
    ? [
        {
          to: '/curation',
          label: 'Kurasi & HITL AI',
          icon: <Cpu className="w-4 h-4" />,
        },
      ]
    : [];

  return (
    <aside className="w-56 border-r border-slate-200 dark:border-slate-800 bg-white/70 dark:bg-[#0c121e]/70 backdrop-blur-md flex flex-col justify-between shrink-0 h-[calc(100vh-3.5rem)] sticky top-14 transition-colors duration-200">
      <div className="p-3 space-y-4">
        {/* Monitoring & Radar */}
        <div>
          <div className="px-2.5 mb-1.5">
            <span className="text-[10px] font-bold tracking-wider uppercase text-slate-400 dark:text-slate-500 font-mono">
              OPERASIONAL
            </span>
          </div>
          <nav className="space-y-1">
            {operationalItems.map((item) => (
              <NavLink
                key={item.to}
                to={item.to}
                className={({ isActive }) =>
                  `flex items-center gap-2.5 px-3 py-2 rounded-lg text-xs font-medium transition-all relative ${
                    isActive
                      ? 'bg-blue-50 dark:bg-blue-500/10 text-blue-700 dark:text-blue-400 border border-blue-200 dark:border-blue-500/25 font-semibold'
                      : 'text-slate-600 dark:text-slate-400 hover:text-slate-900 dark:hover:text-slate-100 hover:bg-slate-100 dark:hover:bg-slate-800/50 border border-transparent'
                  }`
                }
              >
                {({ isActive }) => (
                  <>
                    {isActive && (
                      <span className="absolute left-1 top-2 bottom-2 w-1 rounded-full bg-blue-600 dark:bg-blue-500" />
                    )}
                    <div
                      className={`pl-1 transition-colors ${
                        isActive
                          ? 'text-blue-600 dark:text-blue-400'
                          : 'text-slate-400 dark:text-slate-500'
                      }`}
                    >
                      {item.icon}
                    </div>
                    <span className="truncate">
                      {item.label}
                    </span>
                  </>
                )}
              </NavLink>
            ))}
          </nav>
        </div>

        {/* Tata Kelola (if Admin) */}
        {governanceItems.length > 0 && (
          <div>
            <div className="px-2.5 mb-1.5">
              <span className="text-[10px] font-bold tracking-wider uppercase text-slate-400 dark:text-slate-500 font-mono">
                TATA KELOLA
              </span>
            </div>
            <nav className="space-y-1">
              {governanceItems.map((item) => (
                <NavLink
                  key={item.to}
                  to={item.to}
                  className={({ isActive }) =>
                    `flex items-center gap-2.5 px-3 py-2 rounded-lg text-xs font-medium transition-all relative ${
                      isActive
                        ? 'bg-blue-50 dark:bg-blue-500/10 text-blue-700 dark:text-blue-400 border border-blue-200 dark:border-blue-500/25 font-semibold'
                        : 'text-slate-600 dark:text-slate-400 hover:text-slate-900 dark:hover:text-slate-100 hover:bg-slate-100 dark:hover:bg-slate-800/50 border border-transparent'
                    }`
                  }
                >
                  {({ isActive }) => (
                    <>
                      {isActive && (
                        <span className="absolute left-1 top-2 bottom-2 w-1 rounded-full bg-blue-600 dark:bg-blue-500" />
                      )}
                      <div
                        className={`pl-1 transition-colors ${
                          isActive
                            ? 'text-blue-600 dark:text-blue-400'
                            : 'text-slate-400 dark:text-slate-500'
                        }`}
                      >
                        {item.icon}
                      </div>
                      <span className="truncate">
                        {item.label}
                      </span>
                    </>
                  )}
                </NavLink>
              ))}
            </nav>
          </div>
        )}
      </div>

      {/* Clean Minimal Footer */}
      <div className="p-3 border-t border-slate-200 dark:border-slate-800 flex items-center justify-between text-[11px] text-slate-500 dark:text-slate-400 font-mono">
        <span>TILIK v5.0</span>
        <a
          href="http://localhost:8000/docs"
          target="_blank"
          rel="noreferrer"
          className="flex items-center gap-1 text-blue-600 dark:text-blue-400 hover:underline"
        >
          <span>API Docs</span>
          <ExternalLink className="w-3 h-3" />
        </a>
      </div>
    </aside>
  );
};
