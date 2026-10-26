import React from 'react';
import { HashRouter, Routes, Route, Navigate } from 'react-router-dom';
import { AuthProvider, useAuth } from './context/AuthContext';
import { DashboardLayout } from './components/layout/DashboardLayout';

import { OverviewPage } from './pages/Overview';
import { TrendingTopicsPage } from './pages/TrendingTopics';
import { IssueDetailPage } from './pages/IssueDetail';
import { ContentExplorerPage } from './pages/ContentExplorer';
import { ContentDetailPage } from './pages/ContentDetail';
import { AnalyticsPage } from './pages/Analytics';
import { CurationPage } from './pages/Curation';
import { OmnichannelAssistantPage } from './pages/OmnichannelAssistant';
import { LoginPage } from './pages/Login';

const ProtectedRoute: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  const { isAuthenticated, isLoading } = useAuth();

  if (isLoading) {
    return (
      <div className="min-h-screen bg-[#070b14] flex items-center justify-center">
        <div className="w-8 h-8 border-2 border-cyan-400 border-t-transparent rounded-full animate-spin" />
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
    <AuthProvider>
      <HashRouter>
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
            <Route path="assistant" element={<OmnichannelAssistantPage />} />
            <Route path="curation" element={<CurationPage />} />
          </Route>

          <Route path="*" element={<Navigate to="/" replace />} />
        </Routes>
      </HashRouter>
    </AuthProvider>
  );
};

export default App;
