import React, { useState } from 'react';
import { NavLink } from 'react-router-dom';
import {
  LayoutDashboard,
  Flame,
  Search,
  ExternalLink,
  Terminal,
  PanelLeftClose,
  PanelLeftOpen,
} from 'lucide-react';

export const Sidebar: React.FC = () => {
  const [isCollapsed, setIsCollapsed] = useState<boolean>(() => {
    try {
      return localStorage.getItem('tilik_sidebar_collapsed') === 'true';
    } catch {
      return false;
    }
  });

  const toggleSidebar = () => {
    setIsCollapsed((prev) => {
      const next = !prev;
      try {
        localStorage.setItem('tilik_sidebar_collapsed', String(next));
      } catch {
        // ignore
      }
      return next;
    });
  };

  const menuItems = [
    {
      to: '/',
      label: 'Ringkasan',
      icon: <LayoutDashboard className="w-4 h-4 shrink-0" />,
    },
    {
      to: '/trending',
      label: 'Radar Isu',
      icon: <Flame className="w-4 h-4 shrink-0" />,
    },
    {
      to: '/contents',
      label: 'Arsip Temuan',
      icon: <Search className="w-4 h-4 shrink-0" />,
    },
  ];

  return (
    <aside
      className={`${
        isCollapsed ? 'w-[68px]' : 'w-60'
      } border-r border-slate-200 dark:border-white/[0.06] bg-white dark:bg-[#0A0D14] flex flex-col justify-between shrink-0 h-[calc(100vh-3rem)] sticky top-12 transition-all duration-200 ease-in-out z-30 select-none`}
    >
      <div className="p-2.5 space-y-3">
        {/* Toggle Collapse & Brand Header */}
        <div
          className={`flex items-center ${
            isCollapsed ? 'flex-col gap-2 justify-center' : 'justify-between'
          } pb-2.5 border-b border-slate-200/80 dark:border-white/[0.06]`}
        >
          <div className={`flex items-center gap-2 ${isCollapsed ? 'justify-center' : 'pl-1.5'}`}>
            <img
              src="./logo-tilik.png"
              alt="TILIK"
              className="w-5 h-5 object-contain"
            />
            {!isCollapsed && (
              <span className="text-[11px] font-mono font-bold tracking-wider text-slate-700 dark:text-slate-300 uppercase">
                Menu
              </span>
            )}
          </div>
          <button
            type="button"
            onClick={toggleSidebar}
            className="p-1.5 rounded-md text-slate-400 hover:text-slate-700 dark:hover:text-slate-200 hover:bg-slate-100 dark:hover:bg-white/[0.06] transition-colors"
            title={isCollapsed ? 'Perluas Sidebar' : 'Lipat Sidebar'}
            aria-label={isCollapsed ? 'Perluas Sidebar' : 'Lipat Sidebar'}
          >
            {isCollapsed ? (
              <PanelLeftOpen className="w-4 h-4" />
            ) : (
              <PanelLeftClose className="w-4 h-4" />
            )}
          </button>
        </div>

        {/* 3 Core Nav Items */}
        <div>
          {!isCollapsed && (
            <div className="px-2 mb-1.5">
              <span className="text-[10px] font-semibold tracking-wider uppercase text-slate-400 dark:text-slate-500 font-mono">
                Operasional
              </span>
            </div>
          )}
          <nav className="space-y-1">
            {menuItems.map((item) => (
              <NavLink
                key={item.to}
                to={item.to}
                title={isCollapsed ? item.label : undefined}
                className={({ isActive }) =>
                  `flex items-center ${
                    isCollapsed ? 'justify-center py-2 px-0' : 'gap-2.5 px-2.5 py-1.5'
                  } rounded-md text-xs transition-colors relative ${
                    isActive
                      ? 'bg-blue-500/10 text-blue-600 dark:text-blue-400 font-semibold border-l-2 border-blue-500'
                      : 'text-slate-600 dark:text-slate-400 hover:text-slate-900 dark:hover:text-slate-200 hover:bg-slate-100 dark:hover:bg-white/[0.04]'
                  }`
                }
              >
                {({ isActive }) => (
                  <>
                    <div
                      className={`transition-colors shrink-0 ${
                        isActive
                          ? 'text-blue-600 dark:text-blue-400'
                          : 'text-slate-400 dark:text-slate-500'
                      }`}
                    >
                      {item.icon}
                    </div>
                    {!isCollapsed && <span className="truncate">{item.label}</span>}
                  </>
                )}
              </NavLink>
            ))}
          </nav>
        </div>
      </div>

      {/* Footer */}
      {isCollapsed ? (
        <div className="p-2.5 border-t border-slate-200 dark:border-white/[0.06] flex items-center justify-center text-slate-500 dark:text-slate-400">
          <a
            href="http://localhost:8000/docs"
            target="_blank"
            rel="noreferrer"
            className="p-1.5 rounded text-slate-400 hover:text-blue-500 hover:bg-slate-100 dark:hover:bg-white/[0.06] transition-colors"
            title="Dokumentasi Swagger API (Docs)"
          >
            <Terminal className="w-4 h-4" />
          </a>
        </div>
      ) : (
        <div className="p-3 border-t border-slate-200 dark:border-white/[0.06] flex items-center justify-between text-[10.5px] text-slate-500 dark:text-slate-400 font-mono">
          <div className="flex items-center gap-1.5">
            <Terminal className="w-3.5 h-3.5 text-slate-400" />
            <span>TILIK</span>
          </div>
          <a
            href="http://localhost:8000/docs"
            target="_blank"
            rel="noreferrer"
            className="flex items-center gap-1 text-slate-500 hover:text-blue-500 dark:hover:text-blue-400 transition-colors"
            title="Dokumentasi Swagger API"
          >
            <span>Docs</span>
            <ExternalLink className="w-2.5 h-2.5" />
          </a>
        </div>
      )}
    </aside>
  );
};
