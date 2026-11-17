import React, { useEffect, useState } from 'react';
import { apiClient } from '../api/client';
import { TrendTimelineChart } from '../components/common/Charts';
import { PlatformBadge } from '../components/common/Badge';
import { BarChart3, Users, Activity, AlertCircle } from 'lucide-react';

export const AnalyticsPage: React.FC = () => {
  const [timeseries, setTimeseries] = useState<any[]>([]);
  const [platforms, setPlatforms] = useState<any[]>([]);
  const [days, setDays] = useState<number>(7);
  const [loading, setLoading] = useState<boolean>(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const fetchAnalytics = async () => {
      try {
        setLoading(true);
        const [tsData, pData] = await Promise.all([
          apiClient.analytics.getTimeseries(days),
          apiClient.analytics.getPlatforms(),
        ]);
        setTimeseries(tsData);
        setPlatforms(pData);
      } catch (err) {
        setError('Gagal memuat analitik tren patroli');
      } finally {
        setLoading(false);
      }
    };
    fetchAnalytics();
  }, [days]);

  return (
    <div className="space-y-5">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3">
        <div>
          <h2 className="text-base font-bold tracking-tight text-slate-900 dark:text-white flex items-center gap-2">
            <BarChart3 className="w-5 h-5 text-blue-600 dark:text-blue-400" />
            Statistik & Tren Narasi
          </h2>
        </div>

        {/* Days Filter */}
        <div className="flex items-center gap-1 bg-white dark:bg-slate-900 p-0.5 rounded-lg border border-slate-200 dark:border-slate-800 text-xs">
          {[7, 14, 30].map((d) => (
            <button
              key={d}
              onClick={() => setDays(d)}
              className={`px-3 py-1 rounded-md font-medium transition-colors ${
                days === d
                  ? 'bg-blue-50 dark:bg-blue-600/20 text-blue-600 dark:text-blue-300 border border-blue-200 dark:border-blue-500/40'
                  : 'text-slate-600 dark:text-slate-400 hover:text-slate-900 dark:hover:text-slate-200'
              }`}
            >
              {d} Hari
            </button>
          ))}
        </div>
      </div>

      {loading ? (
        <div className="space-y-5">
          {/* Chart Skeleton */}
          <div className="cyber-card rounded-xl p-5 space-y-4">
            <div className="h-5 w-64 rounded skeleton-shimmer" />
            <div className="h-44 w-full rounded-lg skeleton-shimmer" />
          </div>
          {/* Table Skeleton */}
          <div className="cyber-card rounded-xl p-5 space-y-4">
            <div className="h-5 w-72 rounded skeleton-shimmer" />
            <div className="space-y-2">
              {[1, 2, 3, 4].map((i) => (
                <div key={i} className="flex items-center gap-4 py-3 border-b border-slate-100 dark:border-slate-800/60 last:border-0">
                  <div className="h-4 w-24 rounded skeleton-shimmer" />
                  <div className="h-4 flex-1 rounded skeleton-shimmer" />
                  <div className="h-4 w-16 rounded skeleton-shimmer" />
                  <div className="h-4 w-16 rounded skeleton-shimmer" />
                </div>
              ))}
            </div>
          </div>
        </div>
      ) : error ? (
        <div className="p-8 cyber-card rounded-xl text-center">
          <AlertCircle className="w-8 h-8 text-rose-500 mx-auto mb-2" />
          <p className="text-rose-600 dark:text-rose-300 text-sm font-semibold">{error}</p>
        </div>
      ) : (
        <>
          {/* Daily Discovery Chart */}
          <div className="cyber-card rounded-xl p-4 sm:p-5 space-y-3">
            <div className="flex items-center justify-between">
              <h3 className="text-sm font-bold text-slate-800 dark:text-white flex items-center gap-2">
                <Activity className="w-4 h-4 text-blue-500" />
                Tren Volume Temuan Harian ({days} Hari Terakhir)
              </h3>
            </div>
            <div className="pt-1">
              <TrendTimelineChart data={timeseries} height={190} metric="total" color="#3b82f6" />
            </div>
          </div>

          {/* Platform Performance & Engagement Table */}
          <div className="cyber-card rounded-xl p-4 sm:p-5 space-y-3">
            <h3 className="text-sm font-bold text-slate-800 dark:text-white flex items-center gap-2">
              <Users className="w-4 h-4 text-blue-500" />
              Performa Interaksi Berdasarkan Kanal Platform
            </h3>
            <div className="overflow-x-auto">
              <table className="w-full text-left text-xs">
                <thead className="bg-slate-100 dark:bg-slate-900/90 text-slate-600 dark:text-slate-400 uppercase text-[10px] font-semibold tracking-wider border-b border-slate-200 dark:border-slate-800">
                  <tr>
                    <th className="py-2.5 px-3.5">Platform</th>
                    <th className="py-2.5 px-3.5 text-center">Jumlah Konten</th>
                    <th className="py-2.5 px-3.5 text-center">Tayangan (Views)</th>
                    <th className="py-2.5 px-3.5 text-center">Suka (Likes)</th>
                    <th className="py-2.5 px-3.5 text-center">Komentar</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-slate-100 dark:divide-slate-800/60 font-medium">
                  {platforms.map((p) => (
                    <tr key={p.platform} className="hover:bg-slate-50 dark:hover:bg-slate-800/30 transition-colors">
                      <td className="py-2.5 px-3.5">
                        <PlatformBadge platform={p.platform} />
                      </td>
                      <td className="py-2.5 px-3.5 text-center font-mono text-slate-800 dark:text-slate-200">
                        {p.content_count}
                      </td>
                      <td className="py-2.5 px-3.5 text-center font-mono text-blue-600 dark:text-blue-300">
                        {p.total_views.toLocaleString()}
                      </td>
                      <td className="py-2.5 px-3.5 text-center font-mono text-slate-600 dark:text-slate-300">
                        {p.total_likes.toLocaleString()}
                      </td>
                      <td className="py-2.5 px-3.5 text-center font-mono text-slate-600 dark:text-slate-300">
                        {p.total_comments.toLocaleString()}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>
        </>
      )}
    </div>
  );
};
