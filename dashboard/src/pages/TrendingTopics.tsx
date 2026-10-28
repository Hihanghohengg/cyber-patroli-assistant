import React, { useEffect, useState } from 'react';
import { Link } from 'react-router-dom';
import { apiClient } from '../api/client';
import { TrendingTopicItem } from '../types';
import { ScoreGauge } from '../components/common/Charts';
import { Flame, Search, ArrowRight, Clock, Hash, AlertTriangle, Layers } from 'lucide-react';

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
    <div className="space-y-6">
      {/* Header */}
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4">
        <div>
          <h2 className="text-lg font-bold tracking-tight text-white flex items-center gap-2">
            <Flame className="w-5 h-5 text-amber-500" />
            Radar Trending Topics
          </h2>
          <p className="text-xs text-slate-400 mt-0.5">
            Deteksi lonjakan narasi dan agregasi isu terkini lintas platform.
          </p>
        </div>

        {/* Search */}
        <form onSubmit={handleSearchSubmit} className="relative w-full md:w-72">
          <input
            type="text"
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            placeholder="Cari topik atau kata kunci..."
            className="w-full pl-9 pr-4 py-2 bg-slate-900 border border-slate-800 rounded-lg text-xs text-slate-200 placeholder:text-slate-500 focus:outline-none focus:border-cyan-500"
          />
          <Search className="w-4 h-4 text-slate-500 absolute left-3 top-2.5" />
        </form>
      </div>

      {/* Category Filter Pills */}
      <div className="flex items-center gap-2 overflow-x-auto pb-1 scrollbar-none">
        {categories.map((cat) => (
          <button
            key={cat.id}
            onClick={() => setSelectedCategory(cat.id)}
            className={`px-3 py-1.5 rounded-lg text-xs font-medium whitespace-nowrap transition-colors ${
              selectedCategory === cat.id
                ? 'bg-cyan-500/20 text-cyan-300 border border-cyan-500/40 shadow-sm shadow-cyan-500/10'
                : 'bg-slate-900 text-slate-400 hover:text-slate-200 border border-slate-800'
            }`}
          >
            {cat.label}
          </button>
        ))}
      </div>

      {/* Topics Grid */}
      {loading ? (
        <div className="flex flex-col items-center justify-center min-h-[40vh] gap-3">
          <div className="w-8 h-8 border-2 border-cyan-400 border-t-transparent rounded-full animate-spin" />
          <span className="text-xs font-mono text-cyan-400">MEMUAT TOPIK TRENDING...</span>
        </div>
      ) : error ? (
        <div className="p-8 cyber-card rounded-xl text-center">
          <AlertTriangle className="w-8 h-8 text-rose-400 mx-auto mb-2" />
          <p className="text-rose-300 text-sm">{error}</p>
        </div>
      ) : topics.length === 0 ? (
        <div className="cyber-card rounded-xl p-12 text-center text-slate-400">
          <Layers className="w-10 h-10 text-slate-600 mx-auto mb-3" />
          <h3 className="text-sm font-semibold text-slate-300">Tidak ada topik yang sesuai kriteria</h3>
          <p className="text-xs text-slate-500 mt-1">Coba ubah kata kunci atau pilih filter kategori lainnya.</p>
        </div>
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-5">
          {topics.map((topic) => (
            <div
              key={topic.issue_id}
              className="cyber-card rounded-xl p-5 flex flex-col justify-between hover:border-cyan-500/40 transition-all duration-300"
            >
              <div>
                <div className="flex items-start justify-between gap-3 mb-3">
                  <div>
                    <span className="px-2 py-0.5 rounded text-[10px] font-semibold bg-cyan-950/80 text-cyan-400 border border-cyan-800/40 uppercase tracking-wider">
                      {topic.category}
                    </span>
                    <h3 className="text-sm font-bold text-slate-100 mt-2 line-clamp-2 leading-snug">
                      {topic.title}
                    </h3>
                  </div>
                  <ScoreGauge score={topic.trending_score} size={64} />
                </div>

                {/* Metrics Badges */}
                <div className="grid grid-cols-3 gap-2 py-3 px-3 rounded-lg bg-slate-900/60 border border-slate-800/80 text-center font-mono my-3">
                  <div>
                    <div className="text-[10px] text-slate-400 uppercase">Volume</div>
                    <div className="text-xs font-bold text-slate-200 mt-0.5">{topic.content_count}</div>
                  </div>
                  <div>
                    <div className="text-[10px] text-slate-400 uppercase">Tumbuh</div>
                    <div
                      className={`text-xs font-bold mt-0.5 ${
                        topic.growth_rate >= 0 ? 'text-emerald-400' : 'text-rose-400'
                      }`}
                    >
                      {topic.growth_rate >= 0 ? '+' : ''}
                      {Number(topic.growth_rate).toFixed(1)}%
                    </div>
                  </div>
                  <div>
                    <div className="text-[10px] text-slate-400 uppercase">Kecepatan</div>
                    <div className="text-xs font-bold text-cyan-300 mt-0.5">{Number(topic.velocity).toFixed(1)}/jam</div>
                  </div>
                </div>

                {/* Keywords & Hashtags */}
                <div className="space-y-1.5">
                  <div className="flex flex-wrap gap-1">
                    {topic.top_keywords.slice(0, 4).map((kw, i) => (
                      <span
                        key={i}
                        className="text-[10px] font-mono px-2 py-0.5 rounded bg-slate-800/80 text-slate-300 border border-slate-700/60"
                      >
                        {kw}
                      </span>
                    ))}
                  </div>
                </div>
              </div>

              {/* Card Footer */}
              <div className="pt-4 mt-4 border-t border-slate-800/80 flex items-center justify-between text-xs">
                <span className="text-[10px] text-slate-400 flex items-center gap-1 font-mono">
                  <Clock className="w-3 h-3 text-slate-500" />
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
                  className="inline-flex items-center gap-1.5 text-xs font-semibold text-cyan-400 hover:text-cyan-300 transition-colors"
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
