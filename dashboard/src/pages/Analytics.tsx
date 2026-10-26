import React, { useEffect, useState } from 'react';
import { apiClient } from '../api/client';
import { TrendTimelineChart, HorizontalBarList } from '../components/common/Charts';
import { PlatformBadge } from '../components/common/Badge';
import { BarChart3, TrendingUp, Users, Activity, AlertCircle } from 'lucide-react';

export const AnalyticsPage: React.FC = () => {
  const [timeseries, setTimeseries] = useState<any[]>([]);
  const [platforms, setPlatforms] = useState<any[]>([]);
  const [sentiments, setSentiments] = useState<any[]>([]);
  const [days, setDays] = useState<number>(7);
  const [loading, setLoading] = useState<boolean>(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const fetchAnalytics = async () => {
      try {
        setLoading(true);
        const [tsData, pData, sData] = await Promise.all([
          apiClient.analytics.getTimeseries(days),
          apiClient.analytics.getPlatforms(),
          apiClient.analytics.getSentiments(),
        ]);
        setTimeseries(tsData);
        setPlatforms(pData);
        setSentiments(sData);
      } catch (err) {
        setError('Gagal memuat analitik tren patroli');
      } finally {
        setLoading(false);
      }
    };
    fetchAnalytics();
  }, [days]);

  return (
    <div className="space-y-8">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <h2 className="text-xl font-bold tracking-tight text-white flex items-center gap-2">
            <BarChart3 className="w-5 h-5 text-cyan-400" />
            Statistik & Analisis Tren Narasi Siber
          </h2>
          <p className="text-xs text-slate-400 mt-1">
            Visualisasi historis volume temuan, interaksi audiens, dan dinamika sentimen.
          </p>
        </div>

        {/* Days Filter */}
        <div className="flex items-center gap-1.5 bg-slate-900 p-1 rounded-lg border border-slate-800 text-xs">
          {[7, 14, 30].map((d) => (
            <button
              key={d}
              onClick={() => setDays(d)}
              className={`px-3 py-1 rounded font-medium transition-colors ${
                days === d
                  ? 'bg-cyan-500/20 text-cyan-300 border border-cyan-500/40'
                  : 'text-slate-400 hover:text-slate-200'
              }`}
            >
              {d} Hari
            </button>
          ))}
        </div>
      </div>

      {loading ? (
        <div className="flex flex-col items-center justify-center min-h-[40vh] gap-3">
          <div className="w-8 h-8 border-2 border-cyan-400 border-t-transparent rounded-full animate-spin" />
          <span className="text-xs font-mono text-cyan-400">MEMUAT GRAFIK ANALITIK...</span>
        </div>
      ) : error ? (
        <div className="p-8 cyber-card rounded-xl text-center">
          <AlertCircle className="w-8 h-8 text-rose-400 mx-auto mb-2" />
          <p className="text-rose-300 text-sm font-semibold">{error}</p>
        </div>
      ) : (
        <>
          {/* Daily Discovery Chart */}
          <div className="cyber-card rounded-xl p-6 space-y-4">
            <div className="flex items-center justify-between">
              <div>
                <h3 className="text-sm font-bold text-white flex items-center gap-2">
                  <Activity className="w-4 h-4 text-cyan-400" />
                  Tren Volume Temuan Harian ({days} Hari Terakhir)
                </h3>
                <p className="text-xs text-slate-400 mt-0.5">
                  Jumlah konten baru yang terdeteksi dan dianalisis per hari.
                </p>
              </div>
            </div>
            <div className="pt-2">
              <TrendTimelineChart data={timeseries} height={200} metric="total" color="#00f0ff" />
            </div>
          </div>

          {/* Platform Performance & Engagement Table */}
          <div className="cyber-card rounded-xl p-6 space-y-4">
            <h3 className="text-sm font-bold text-white flex items-center gap-2">
              <Users className="w-4 h-4 text-cyan-400" />
              Performa Interaksi Berdasarkan Kanal Platform
            </h3>
            <div className="overflow-x-auto">
              <table className="w-full text-left text-xs">
                <thead className="bg-slate-900/90 text-slate-400 uppercase text-[10px] font-semibold tracking-wider border-b border-slate-800">
                  <tr>
                    <th className="py-3 px-4">Platform</th>
                    <th className="py-3 px-4 text-center">Jumlah Konten</th>
                    <th className="py-3 px-4 text-center">Total Tayangan (Views)</th>
                    <th className="py-3 px-4 text-center">Total Suka (Likes)</th>
                    <th className="py-3 px-4 text-center">Total Komentar</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-slate-800/60 font-medium">
                  {platforms.map((p) => (
                    <tr key={p.platform} className="hover:bg-slate-800/30 transition-colors">
                      <td className="py-3.5 px-4">
                        <PlatformBadge platform={p.platform} />
                      </td>
                      <td className="py-3.5 px-4 text-center font-mono text-slate-200">
                        {p.content_count}
                      </td>
                      <td className="py-3.5 px-4 text-center font-mono text-cyan-300">
                        {p.total_views.toLocaleString()}
                      </td>
                      <td className="py-3.5 px-4 text-center font-mono text-slate-300">
                        {p.total_likes.toLocaleString()}
                      </td>
                      <td className="py-3.5 px-4 text-center font-mono text-slate-300">
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
