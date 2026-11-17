import React, { Suspense, lazy } from 'react';
import { HashRouter, Routes, Route, Navigate } from 'react-router-dom';
import { AuthProvider, useAuth } from './context/AuthContext';
import { ThemeProvider } from './context/ThemeContext';
import { DashboardLayout } from './components/layout/DashboardLayout';

// Performance optimization: Route-level code splitting & lazy loading
const OverviewPage = lazy(() => import('./pages/Overview').then((m) => ({ default: m.OverviewPage })));
const TrendingTopicsPage = lazy(() => import('./pages/TrendingTopics').then((m) => ({ default: m.TrendingTopicsPage })));
const IssueDetailPage = lazy(() => import('./pages/IssueDetail').then((m) => ({ default: m.IssueDetailPage })));
const ContentExplorerPage = lazy(() => import('./pages/ContentExplorer').then((m) => ({ default: m.ContentExplorerPage })));
const ContentDetailPage = lazy(() => import('./pages/ContentDetail').then((m) => ({ default: m.ContentDetailPage })));
const AnalyticsPage = lazy(() => import('./pages/Analytics').then((m) => ({ default: m.AnalyticsPage })));
const CurationPage = lazy(() => import('./pages/Curation').then((m) => ({ default: m.CurationPage })));
const LoginPage = lazy(() => import('./pages/Login').then((m) => ({ default: m.LoginPage })));

// Minimalist, high-performance page transition fallback
const PageLoadingFallback: React.FC = () => (
  <div className="flex items-center justify-center min-h-[50vh] w-full">
    <div className="flex flex-col items-center gap-3">
      <div className="w-8 h-8 rounded-full border-2 border-blue-500/20 border-t-blue-500 animate-spin" />
      <span className="text-[11px] font-mono font-medium text-slate-500 dark:text-slate-400 tracking-wider">
        MEMUAT MODUL PATROLI...
      </span>
    </div>
  </div>
);

const ProtectedRoute: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  const { isAuthenticated, isLoading } = useAuth();

  if (isLoading) {
    return (
      <div className="min-h-screen bg-slate-50 dark:bg-[#070b14] flex items-center justify-center">
        <div className="w-8 h-8 border-2 border-blue-500 border-t-transparent rounded-full animate-spin" />
      </div>
    );
  }

  if (!isAuthenticated) {
    return <Navigate to="/login" replace />;
  }

  return <>{children}</>;
};

export const App: React.FC = () => {
  return (
    <ThemeProvider>
      <AuthProvider>
        <HashRouter>
          <Suspense fallback={<PageLoadingFallback />}>
            <Routes>
              <Route path="/login" element={<LoginPage />} />

              <Route
                path="/"
                element={
                  <ProtectedRoute>
                    <DashboardLayout />
                  </ProtectedRoute>
                }
              >
                <Route index element={<OverviewPage />} />
                <Route path="trending" element={<TrendingTopicsPage />} />
                <Route path="trending/:id" element={<IssueDetailPage />} />
                <Route path="contents" element={<ContentExplorerPage />} />
                <Route path="contents/:id" element={<ContentDetailPage />} />
                <Route path="analytics" element={<AnalyticsPage />} />
                <Route path="assistant" element={<Navigate to="/" replace />} />
                <Route path="curation" element={<CurationPage />} />
              </Route>

              <Route path="*" element={<Navigate to="/" replace />} />
            </Routes>
          </Suspense>
        </HashRouter>
      </AuthProvider>
    </ThemeProvider>
  );
};

export default App;
