import React, { useEffect, useState } from 'react';
import { Link } from 'react-router-dom';
import { apiClient } from '../api/client';
import { TrendingTopicItem } from '../types';
import { ScoreGauge } from '../components/common/Charts';
import { Flame, Search, ArrowRight, Clock, AlertTriangle, Layers } from 'lucide-react';

export const TrendingTopicsPage: React.FC = () => {
  const [topics, setTopics] = useState<TrendingTopicItem[]>([]);
  const [loading, setLoading] = useState<boolean>(true);
  const [error, setError] = useState<string | null>(null);

  const [search, setSearch] = useState<string>('');
  const [selectedCategory, setSelectedCategory] = useState<string>('ALL');

  const categories = [
    { id: 'ALL', label: 'Semua Kategori' },
    { id: 'Kejahatan Finansial', label: 'Kejahatan Finansial' },
    { id: 'Perjudian Daring', label: 'Perjudian Daring' },
    { id: 'Disinformasi Politik & Kebijakan Publik', label: 'Disinformasi Politik' },
    { id: 'Hoaks Kesehatan & Pangan', label: 'Hoaks Kesehatan' },
    { id: 'Klarifikasi & Edukasi Resmi', label: 'Klarifikasi Resmi' },
  ];

  const fetchTopics = async () => {
    try {
      setLoading(true);
      const params: any = { status: 'ACTIVE' };
      if (selectedCategory !== 'ALL') params.category = selectedCategory;
      if (search.trim()) params.search = search.trim();

      const data = await apiClient.trending.list(params);
      setTopics(data);
    } catch (err) {
      setError('Gagal memuat daftar topik trending');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchTopics();
  }, [selectedCategory]);

  const handleSearchSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    fetchTopics();
  };

  return (
    <div className="space-y-5">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3">
        <div>
          <h2 className="text-base font-bold tracking-tight text-slate-900 dark:text-white flex items-center gap-2">
            <Flame className="w-5 h-5 text-amber-500" />
            Radar Trending Topics
          </h2>
        </div>

        {/* Search */}
        <form onSubmit={handleSearchSubmit} className="relative w-full sm:w-64">
          <input
            type="text"
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            placeholder="Cari topik / isu..."
            className="w-full pl-8 pr-3 py-1.5 bg-white dark:bg-slate-900 border border-slate-300 dark:border-slate-800 rounded-lg text-xs text-slate-800 dark:text-slate-200 placeholder:text-slate-400 dark:placeholder:text-slate-500 focus:outline-none focus:border-blue-500"
          />
          <Search className="w-3.5 h-3.5 text-slate-400 absolute left-2.5 top-2" />
        </form>
      </div>

      {/* Category Filter Pills */}
      <div className="flex items-center gap-1.5 overflow-x-auto pb-1 scrollbar-none">
        {categories.map((cat) => (
          <button
            key={cat.id}
            onClick={() => setSelectedCategory(cat.id)}
            className={`px-3 py-1 rounded-lg text-xs font-medium whitespace-nowrap transition-colors ${
              selectedCategory === cat.id
                ? 'bg-blue-50 dark:bg-blue-600/20 text-blue-600 dark:text-blue-300 border border-blue-200 dark:border-blue-500/40'
                : 'bg-white dark:bg-slate-900 text-slate-600 dark:text-slate-400 hover:text-slate-900 dark:hover:text-slate-200 border border-slate-200 dark:border-slate-800'
            }`}
          >
            {cat.label}
          </button>
        ))}
      </div>

      {/* Topics Grid */}
      {loading ? (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
          {[1, 2, 3, 4, 5, 6].map((i) => (
            <div key={i} className="cyber-card rounded-xl p-4 flex flex-col justify-between space-y-4">
              <div>
                <div className="flex items-start justify-between gap-3 mb-2.5">
                  <div className="flex-1 space-y-2">
                    <div className="flex gap-1.5">
                      <div className="h-4 w-20 rounded skeleton-shimmer" />
                      <div className="h-4 w-16 rounded skeleton-shimmer" />
                    </div>
                    <div className="h-4 w-full rounded skeleton-shimmer" />
                    <div className="h-3 w-3/4 rounded skeleton-shimmer" />
                  </div>
                  <div className="w-12 h-12 rounded-full skeleton-shimmer shrink-0" />
                </div>
                <div className="grid grid-cols-4 gap-2 py-2 px-2.5 rounded-lg bg-slate-50 dark:bg-slate-900/60 border border-slate-200 dark:border-slate-800/80 my-2.5">
                  <div className="h-6 rounded skeleton-shimmer" />
                  <div className="h-6 rounded skeleton-shimmer" />
                  <div className="h-6 rounded skeleton-shimmer" />
                  <div className="h-6 rounded skeleton-shimmer" />
                </div>
                <div className="flex gap-1">
                  <div className="h-4 w-12 rounded skeleton-shimmer" />
                  <div className="h-4 w-14 rounded skeleton-shimmer" />
                  <div className="h-4 w-10 rounded skeleton-shimmer" />
                </div>
              </div>
              <div className="pt-3 border-t border-slate-100 dark:border-slate-800/80 flex justify-between">
                <div className="h-3 w-24 rounded skeleton-shimmer" />
                <div className="h-3 w-16 rounded skeleton-shimmer" />
              </div>
            </div>
          ))}
        </div>
      ) : error ? (
        <div className="p-8 cyber-card rounded-xl text-center">
          <AlertTriangle className="w-8 h-8 text-rose-500 mx-auto mb-2" />
          <p className="text-rose-600 dark:text-rose-300 text-sm">{error}</p>
        </div>
      ) : topics.length === 0 ? (
        <div className="cyber-card rounded-xl p-10 text-center text-slate-400">
          <Layers className="w-8 h-8 text-slate-400 mx-auto mb-2" />
          <h3 className="text-xs font-semibold text-slate-600 dark:text-slate-300">Tidak ada topik yang sesuai kriteria</h3>
          <p className="text-[11px] text-slate-400 mt-0.5">Coba ubah kata kunci atau pilih filter kategori lainnya.</p>
        </div>
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
          {topics.map((topic) => (
            <div
              key={topic.issue_id}
              className="cyber-card rounded-xl p-4 flex flex-col justify-between hover:border-blue-400 dark:hover:border-blue-500/40 transition-all duration-200"
            >
              <div>
                <div className="flex items-start justify-between gap-3 mb-2.5">
                  <div className="flex-1">
                    <div className="flex items-center gap-1.5 flex-wrap">
                      <span className="px-2 py-0.5 rounded text-[10px] font-semibold bg-blue-50 dark:bg-blue-950/80 text-blue-600 dark:text-blue-400 border border-blue-200 dark:border-blue-800/40 uppercase tracking-wider">
                        {topic.category}
                      </span>
                      {/* Status Eskalasi Badge */}
                      <span
                        className={`px-2 py-0.5 rounded text-[10px] font-bold tracking-wider font-mono uppercase border ${
                          topic.trending_score >= 75
                            ? 'bg-rose-50 dark:bg-rose-950/80 text-rose-600 dark:text-rose-400 border-rose-300 dark:border-rose-800/60 shadow-sm shadow-rose-500/10'
                            : topic.trending_score >= 50
                            ? 'bg-amber-50 dark:bg-amber-950/80 text-amber-600 dark:text-amber-400 border-amber-300 dark:border-amber-800/60'
                            : 'bg-blue-50 dark:bg-blue-950/80 text-blue-600 dark:text-blue-400 border-blue-200 dark:border-blue-800/60'
                        }`}
                      >
                        {topic.escalation_label || (topic.trending_score >= 75 ? 'ESKALASI TINGGI' : topic.trending_score >= 50 ? 'MENGHANGAT' : 'PANTAU')}
                      </span>
                    </div>
                    <h3 className="text-xs font-bold text-slate-800 dark:text-slate-100 mt-2 line-clamp-2 leading-snug">
                      {topic.title}
                    </h3>
                  </div>
                  <div className="flex flex-col items-center">
                    <ScoreGauge score={topic.trending_score} size={54} />
                    <span className="text-[9px] font-mono text-slate-400 font-semibold mt-0.5">HotScore</span>
                  </div>
                </div>

                {/* 4 Sinyal Operasional Nyata TILIK */}
                <div className="grid grid-cols-2 sm:grid-cols-4 gap-2 py-2 px-2.5 rounded-lg bg-slate-50 dark:bg-slate-900/60 border border-slate-200 dark:border-slate-800/80 text-center font-mono my-2.5">
                  <div>
                    <div className="text-[9px] text-slate-400 uppercase tracking-tight">Skor Tren</div>
                    <div
                      className={`text-xs font-bold mt-0.5 ${
                        topic.trending_score >= 75
                          ? 'text-rose-600 dark:text-rose-400'
                          : topic.trending_score >= 50
                          ? 'text-amber-600 dark:text-amber-400'
                          : 'text-blue-600 dark:text-blue-400'
                      }`}
                    >
                      {Number(topic.trending_score).toFixed(1)}
                    </div>
                  </div>
                  <div>
                    <div className="text-[9px] text-slate-400 uppercase tracking-tight">Platform</div>
                    <div className="text-xs font-bold text-slate-800 dark:text-slate-200 mt-0.5">
                      {topic.platform_count || 1}/5 Kanal
                    </div>
                  </div>
                  <div>
                    <div className="text-[9px] text-slate-400 uppercase tracking-tight">Temuan 24J</div>
                    <div className="text-xs font-bold text-emerald-600 dark:text-emerald-400 mt-0.5">
                      {topic.recent_count_24h ?? topic.content_count ?? 0} post
                    </div>
                  </div>
                  <div>
                    <div className="text-[9px] text-slate-400 uppercase tracking-tight">Rerata Urgensi</div>
                    <div className="text-xs font-bold text-indigo-600 dark:text-indigo-400 mt-0.5">
                      {(topic.avg_urgency || 2.5).toFixed(1)}/5
                    </div>
                  </div>
                </div>

                {/* Keywords */}
                <div className="space-y-1">
                  <div className="flex flex-wrap gap-1">
                    {topic.top_keywords.slice(0, 4).map((kw, i) => (
                      <span
                        key={i}
                        className="text-[10px] font-mono px-2 py-0.5 rounded bg-slate-100 dark:bg-slate-800 text-slate-600 dark:text-slate-300 border border-slate-200 dark:border-slate-700"
                      >
                        {kw}
                      </span>
                    ))}
                  </div>
                </div>
              </div>

              {/* Card Footer */}
              <div className="pt-3 mt-3 border-t border-slate-100 dark:border-slate-800/80 flex items-center justify-between text-xs">
                <span className="text-[10px] text-slate-400 flex items-center gap-1 font-mono">
                  <Clock className="w-3 h-3 text-slate-400" />
                  {topic.last_seen_at
                    ? new Date(topic.last_seen_at).toLocaleDateString('id-ID', {
                        day: '2-digit',
                        month: 'short',
                        hour: '2-digit',
                        minute: '2-digit',
                      })
                    : '-'}
                </span>

                <Link
                  to={`/trending/${topic.issue_id}`}
                  className="inline-flex items-center gap-1 text-xs font-semibold text-blue-600 dark:text-blue-400 hover:underline"
                >
                  Buka Dossier
                  <ArrowRight className="w-3.5 h-3.5" />
                </Link>
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
};
