import React from 'react';
import { Outlet } from 'react-router-dom';
import { Navbar } from './Navbar';
import { Sidebar } from './Sidebar';

export const DashboardLayout: React.FC = () => {
  return (
    <div className="min-h-dvh max-w-full overflow-x-hidden bg-slate-50 dark:bg-[#090A0F] text-slate-900 dark:text-slate-100 flex flex-col relative selection:bg-blue-500/20 selection:text-blue-700 dark:selection:bg-blue-500/30 dark:selection:text-blue-200 transition-colors duration-150">
      <div className="flex flex-col min-h-dvh max-w-full">
        <Navbar />
        <div className="flex flex-1 min-w-0">
          <Sidebar />
          <main className="flex-1 p-4 sm:p-6 lg:p-7 max-w-7xl mx-auto w-full min-w-0 overflow-y-auto">
            <Outlet />
          </main>
        </div>
      </div>
    </div>
  );
};
