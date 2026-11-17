import React, { useEffect, useState, useMemo } from 'react';
import { Link } from 'react-router-dom';
import { apiClient } from '../api/client';
import { TrendingResponse } from '../types';
import { ScoreGauge } from '../components/common/Charts';
import {
  Flame,
  Search,
  ArrowRight,
  Clock,
  AlertTriangle,
  Layers,
  ShieldAlert,
  Briefcase,
  Globe,
  Tag,
  Users,
  X,
  RotateCcw,
} from 'lucide-react';

export const TrendingTopicsPage: React.FC = () => {
  const [data, setData] = useState<TrendingResponse | null>(null);
  const [loading, setLoading] = useState<boolean>(true);
  const [error, setError] = useState<string | null>(null);

  const [search, setSearch] = useState<string>('');
  const [selectedCategory, setSelectedCategory] = useState<string>('ALL');
  const [selectedPillar, setSelectedPillar] = useState<'ALL' | 'AKTUAL' | 'KRITIKAL' | 'TEMATIK'>('ALL');
  const [selectedKeyword, setSelectedKeyword] = useState<string | null>(null);

  const categories = [
    { id: 'ALL', label: 'Semua' },
    { id: 'Politik', label: 'Politik' },
    { id: 'Keamanan', label: 'Keamanan' },
    { id: 'Sosial', label: 'Sosial' },
    { id: 'Ekonomi', label: 'Ekonomi' },
    { id: 'Ideologi', label: 'Ideologi' },
    { id: 'Pertahanan', label: 'Pertahanan' },
    { id: 'Budaya', label: 'Budaya' },
    { id: 'Non-Isu', label: 'Non-Isu' },
  ];

  const fetchTrendingData = async () => {
    try {
      setLoading(true);
      setError(null);
      const params: any = { status: 'ACTIVE' };
      if (selectedCategory !== 'ALL') params.category = selectedCategory;
      if (selectedPillar !== 'ALL') params.issue_type = selectedPillar;
      if (search.trim()) params.search = search.trim();

      const res = await apiClient.trending.list(params);
      setData(res);
    } catch (err: any) {
      setError(err?.message || 'Gagal memuat radar isu');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchTrendingData();
  }, [selectedCategory, selectedPillar]);

  const handleSearchSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    fetchTrendingData();
  };

  const resetAllFilters = () => {
    setSearch('');
    setSelectedCategory('ALL');
    setSelectedPillar('ALL');
    setSelectedKeyword(null);
  };

  const filteredTopics = useMemo(() => {
    if (!data?.topics) return [];
    if (!selectedKeyword) return data.topics;
    const kw = selectedKeyword.toLowerCase();
    return data.topics.filter(
      (t) =>
        t.title.toLowerCase().includes(kw) ||
        t.canonical_name.toLowerCase().includes(kw) ||
        (t.top_keywords && t.top_keywords.some((k) => k.toLowerCase().includes(kw))) ||
        (t.hashtag && t.hashtag.toLowerCase().includes(kw))
    );
  }, [data?.topics, selectedKeyword]);

  const maxActorMentions = useMemo(() => {
    if (!data?.hot_actors || data.hot_actors.length === 0) return 1;
    return Math.max(...data.hot_actors.map((a) => a.mentions), 1);
  }, [data?.hot_actors]);

  const maxWordCount = useMemo(() => {
    if (!data?.word_cloud || data.word_cloud.length === 0) return 1;
    return Math.max(...data.word_cloud.map((w) => w.count), 1);
  }, [data?.word_cloud]);

  return (
    <div className="space-y-5 pb-10">
      {/* ── 1. HEADER RINGKAS & PENCARIAN ── */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 border-b border-slate-200 dark:border-white/[0.06] pb-3">
        <h1 className="text-lg font-semibold tracking-tight text-slate-900 dark:text-white flex items-center gap-2">
          Radar Isu
        </h1>

        <form onSubmit={handleSearchSubmit} className="relative w-full sm:w-64">
          <input
            type="text"
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            placeholder="Cari isu atau hashtag..."
            className="w-full pl-8 pr-7 py-1.5 bg-white dark:bg-[#0A0D14] border border-slate-200 dark:border-white/[0.08] rounded-lg text-xs text-slate-800 dark:text-slate-200 placeholder:text-slate-400 dark:placeholder:text-slate-600 focus:outline-none focus:border-blue-500 font-mono transition-colors"
          />
          <Search className="w-3.5 h-3.5 text-slate-400 absolute left-2.5 top-2.5" />
          {search && (
            <button
              type="button"
              onClick={() => {
                setSearch('');
                fetchTrendingData();
              }}
              className="absolute right-2 top-2 text-slate-400 hover:text-slate-200"
            >
              <X className="w-3.5 h-3.5" />
            </button>
          )}
        </form>
      </div>

      {/* ── 2. TAB FILTER KATEGORI (UNDERLINE STYLE) ── */}
      <div className="flex items-center gap-1 overflow-x-auto border-b border-slate-200 dark:border-white/[0.06] scrollbar-none">
        {categories.map((cat) => (
          <button
            key={cat.id}
            onClick={() => setSelectedCategory(cat.id)}
            className={`px-3 py-2 text-xs font-medium whitespace-nowrap transition-colors border-b-2 -mb-[2px] ${
              selectedCategory === cat.id
                ? 'border-blue-500 text-blue-600 dark:text-blue-400 font-semibold'
                : 'border-transparent text-slate-500 dark:text-slate-400 hover:text-slate-800 dark:hover:text-slate-200'
            }`}
          >
            {cat.label}
          </button>
        ))}
      </div>

      {/* ── 3. INLINE KPI STRIP (4 PILAR ISU) ── */}
      <div className="cyber-card rounded-xl border border-slate-200 dark:border-white/[0.06] overflow-hidden">
        <div className="grid grid-cols-2 lg:grid-cols-4 divide-y lg:divide-y-0 lg:divide-x divide-slate-100 dark:divide-white/[0.06]">
          {/* Isu Aktual */}
          <button
            type="button"
            onClick={() => setSelectedPillar(selectedPillar === 'AKTUAL' ? 'ALL' : 'AKTUAL')}
            className={`p-3.5 text-left transition-colors ${
              selectedPillar === 'AKTUAL' ? 'bg-amber-500/10' : 'hover:bg-slate-50 dark:hover:bg-white/[0.02]'
            }`}
          >
            <div className="flex items-center justify-between text-slate-400 dark:text-slate-500">
              <span className="text-[10.5px] font-mono font-semibold uppercase tracking-wider flex items-center gap-1.5 text-amber-500">
                <Flame className="w-3.5 h-3.5" />
                Isu Aktual
              </span>
              <span className="text-[10px] font-mono text-slate-400">Trending</span>
            </div>
            <div className="text-xl font-bold font-mono tabular-nums text-slate-900 dark:text-white mt-1">
              {data ? data.total_actual : '–'}
            </div>
            <div className="text-[10px] text-slate-500 font-mono mt-0.5 truncate">
              Hangat & butuh respons
            </div>
          </button>

          {/* Isu Kritikal */}
          <button
            type="button"
            onClick={() => setSelectedPillar(selectedPillar === 'KRITIKAL' ? 'ALL' : 'KRITIKAL')}
            className={`p-3.5 text-left transition-colors ${
              selectedPillar === 'KRITIKAL' ? 'bg-rose-500/10' : 'hover:bg-slate-50 dark:hover:bg-white/[0.02]'
            }`}
          >
            <div className="flex items-center justify-between text-slate-400 dark:text-slate-500">
              <span className="text-[10.5px] font-mono font-semibold uppercase tracking-wider flex items-center gap-1.5 text-rose-500">
                <ShieldAlert className="w-3.5 h-3.5" />
                Isu Kritikal
              </span>
              <span className="text-[10px] font-mono text-slate-400">Prioritas</span>
            </div>
            <div className="text-xl font-bold font-mono tabular-nums text-slate-900 dark:text-white mt-1">
              {data ? data.total_critical : '–'}
            </div>
            <div className="text-[10px] text-slate-500 font-mono mt-0.5 truncate">
              Risiko tinggi (≥3.8/5)
            </div>
          </button>

          {/* Isu Tematik */}
          <button
            type="button"
            onClick={() => setSelectedPillar(selectedPillar === 'TEMATIK' ? 'ALL' : 'TEMATIK')}
            className={`p-3.5 text-left transition-colors ${
              selectedPillar === 'TEMATIK' ? 'bg-indigo-500/10' : 'hover:bg-slate-50 dark:hover:bg-white/[0.02]'
            }`}
          >
            <div className="flex items-center justify-between text-slate-400 dark:text-slate-500">
              <span className="text-[10.5px] font-mono font-semibold uppercase tracking-wider flex items-center gap-1.5 text-indigo-400">
                <Briefcase className="w-3.5 h-3.5" />
                Isu Tematik
              </span>
              <span className="text-[10px] font-mono text-slate-400">Agenda</span>
            </div>
            <div className="text-xl font-bold font-mono tabular-nums text-slate-900 dark:text-white mt-1">
              {data ? data.total_thematic : '–'}
            </div>
            <div className="text-[10px] text-slate-500 font-mono mt-0.5 truncate">
              Payung program kerja
            </div>
          </button>

          {/* Total Terpantau */}
          <button
            type="button"
            onClick={() => setSelectedPillar('ALL')}
            className={`p-3.5 text-left transition-colors ${
              selectedPillar === 'ALL' ? 'bg-blue-500/10' : 'hover:bg-slate-50 dark:hover:bg-white/[0.02]'
            }`}
          >
            <div className="flex items-center justify-between text-slate-400 dark:text-slate-500">
              <span className="text-[10.5px] font-mono font-semibold uppercase tracking-wider flex items-center gap-1.5 text-blue-400">
                <Globe className="w-3.5 h-3.5" />
                Total Isu
              </span>
              <span className="text-[10px] font-mono text-slate-400">Semua</span>
            </div>
            <div className="text-xl font-bold font-mono tabular-nums text-slate-900 dark:text-white mt-1">
              {data ? data.total_topics : '–'}
            </div>
            <div className="text-[10px] text-slate-500 font-mono mt-0.5 truncate">
              Seluruh klaster aktif
            </div>
          </button>
        </div>
      </div>

      {/* ── 4. VISUAL GRID (6:6) DUAL PANEL ── */}
      <div className="grid grid-cols-1 lg:grid-cols-12 gap-4">
        {/* Left: Word Cloud (6 Cols) */}
        <div className="lg:col-span-6 cyber-card rounded-xl p-4 flex flex-col justify-between">
          <div>
            <div className="flex items-center justify-between mb-2">
              <div className="flex items-center gap-2">
                <Tag className="w-4 h-4 text-blue-500" />
                <h3 className="text-xs font-bold text-slate-800 dark:text-slate-100 uppercase tracking-wider font-mono">
                  Radar Kata Kunci Percakapan
                </h3>
              </div>
              <span className="text-[10px] font-mono text-slate-400">
                {data?.word_cloud?.length || 0} Kata
              </span>
            </div>

            {selectedKeyword && (
              <div className="mb-2.5 px-2.5 py-1 rounded bg-blue-500/10 border border-blue-500/20 flex items-center justify-between text-xs font-mono">
                <span className="text-blue-400">Filter: "{selectedKeyword}"</span>
                <button
                  onClick={() => setSelectedKeyword(null)}
                  className="text-[10px] text-rose-400 hover:underline flex items-center gap-1"
                >
                  <RotateCcw className="w-3 h-3" />
                  Batal
                </button>
              </div>
            )}

            <div className="p-3 rounded-lg bg-slate-50 dark:bg-[#0A0D14] border border-slate-200 dark:border-white/[0.06] flex flex-wrap gap-1.5 min-h-[140px]">
              {loading ? (
                <div className="flex flex-wrap gap-1.5 w-full">
                  {[...Array(14)].map((_, i) => (
                    <div key={i} className="h-6 rounded skeleton-shimmer" style={{ width: `${45 + (i % 4) * 20}px` }} />
                  ))}
                </div>
              ) : !data?.word_cloud || data.word_cloud.length === 0 ? (
                <div className="w-full text-center py-8 text-slate-400 text-xs font-mono">
                  Belum ada kata kunci terpantau.
                </div>
              ) : (
                data.word_cloud.map((item, idx) => {
                  const isSelected = selectedKeyword === item.text;
                  const ratio = item.count / maxWordCount;

                  const fontClass =
                    ratio > 0.65
                      ? 'text-xs font-bold px-2 py-0.5'
                      : 'text-[11px] font-medium px-1.5 py-0.5';

                  const colorClass =
                    item.avg_urgency >= 3.8
                      ? isSelected
                        ? 'bg-rose-500 text-white border-rose-500'
                        : 'bg-rose-500/10 text-rose-400 border-rose-500/20 hover:bg-rose-500/20'
                      : isSelected
                      ? 'bg-blue-500 text-white border-blue-500'
                      : 'bg-white dark:bg-white/[0.03] text-slate-700 dark:text-slate-300 border-slate-200 dark:border-white/[0.08] hover:border-slate-400';

                  return (
                    <button
                      key={idx}
                      onClick={() => setSelectedKeyword(isSelected ? null : item.text)}
                      className={`rounded border transition-colors inline-flex items-center gap-1 font-mono ${fontClass} ${colorClass}`}
                      title={`Frekuensi: ${item.count} | Urgensi: ${item.avg_urgency.toFixed(1)}/5`}
                    >
                      <span>{item.text}</span>
                      <span className="text-[9px] opacity-60">({item.count})</span>
                    </button>
                  );
                })
              )}
            </div>
          </div>

          <div className="pt-2.5 mt-2 border-t border-slate-100 dark:border-white/[0.06] flex items-center justify-between text-[10px] font-mono text-slate-400">
            <span>Klik kata untuk memfilter isu</span>
            <span>Stopwords ID & EN Filtered</span>
          </div>
        </div>

        {/* Right: Hot Actors (6 Cols) */}
        <div className="lg:col-span-6 cyber-card rounded-xl p-4 flex flex-col justify-between">
          <div>
            <div className="flex items-center justify-between mb-2">
              <div className="flex items-center gap-2">
                <Users className="w-4 h-4 text-emerald-500" />
                <h3 className="text-xs font-bold text-slate-800 dark:text-slate-100 uppercase tracking-wider font-mono">
                  Tokoh & Institusi Terpantau
                </h3>
              </div>
              <span className="text-[10px] font-mono text-slate-400">Top 8</span>
            </div>

            <div className="space-y-1.5">
              {loading ? (
                <div className="space-y-1.5">
                  {[...Array(5)].map((_, i) => (
                    <div key={i} className="h-8 rounded skeleton-shimmer" />
                  ))}
                </div>
              ) : !data?.hot_actors || data.hot_actors.length === 0 ? (
                <div className="text-center py-8 text-slate-400 text-xs font-mono">
                  Belum ada tokoh spesifik terdeteksi.
                </div>
              ) : (
                data.hot_actors.map((actor, idx) => {
                  const percent = Math.min(100, Math.round((actor.mentions / maxActorMentions) * 100));
                  return (
                    <button
                      key={idx}
                      onClick={() => setSearch(actor.name)}
                      className="w-full text-left p-1.5 px-2 rounded-lg bg-slate-50 dark:bg-[#0A0D14] border border-slate-200 dark:border-white/[0.06] hover:border-emerald-500/40 transition-colors group"
                    >
                      <div className="flex items-center justify-between text-xs mb-1">
                        <span className="font-semibold text-slate-800 dark:text-slate-200 group-hover:text-emerald-400 transition-colors line-clamp-1">
                          {actor.name}
                        </span>
                        <div className="flex items-center gap-1.5 shrink-0 font-mono">
                          <span className="text-[9px] px-1.5 py-0.2 rounded bg-slate-200 dark:bg-white/[0.06] text-slate-600 dark:text-slate-400">
                            {actor.category}
                          </span>
                          <span className="text-[10px] font-bold text-emerald-500">
                            {actor.mentions} post
                          </span>
                        </div>
                      </div>
                      <div className="w-full h-1 rounded-full bg-slate-200 dark:bg-white/[0.06] overflow-hidden">
                        <div
                          className="h-full rounded-full bg-emerald-500 transition-all duration-300"
                          style={{ width: `${percent}%` }}
                        />
                      </div>
                    </button>
                  );
                })
              )}
            </div>
          </div>

          <div className="pt-2.5 mt-2 border-t border-slate-100 dark:border-white/[0.06] flex items-center justify-between text-[10px] font-mono text-slate-400">
            <span>Klik tokoh untuk cari postingan</span>
            <span>NER Regex Engine</span>
          </div>
        </div>
      </div>

      {/* ── 5. DAFTAR PERINGKAT ISU (HORIZONTAL LINEAR CARDS) ── */}
      <div className="space-y-2.5">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-2">
            <Layers className="w-4 h-4 text-blue-500" />
            <h3 className="text-xs font-bold text-slate-800 dark:text-slate-100 uppercase tracking-wider font-mono">
              Daftar Isu Terpantau ({filteredTopics.length})
            </h3>
          </div>
          {(selectedKeyword || selectedCategory !== 'ALL' || selectedPillar !== 'ALL' || search) && (
            <button
              onClick={resetAllFilters}
              className="text-xs text-blue-500 hover:underline flex items-center gap-1 font-mono"
            >
              <RotateCcw className="w-3 h-3" />
              Reset Semua Filter
            </button>
          )}
        </div>

        {loading ? (
          <div className="space-y-2.5">
            {[1, 2, 3, 4].map((i) => (
              <div key={i} className="cyber-card p-4 rounded-xl h-20 skeleton-shimmer" />
            ))}
          </div>
        ) : error ? (
          <div className="p-8 cyber-card rounded-xl text-center">
            <AlertTriangle className="w-8 h-8 text-rose-500 mx-auto mb-2" />
            <p className="text-rose-500 text-sm font-semibold">{error}</p>
          </div>
        ) : filteredTopics.length === 0 ? (
          <div className="cyber-card rounded-xl p-10 text-center text-slate-400 font-mono text-xs">
            Tidak ada isu yang sesuai filter saat ini.
          </div>
        ) : (
          <div className="space-y-2">
            {filteredTopics.map((topic, index) => {
              const displayRank = String(topic.rank ?? index + 1).padStart(2, '0');
              const isCritical = topic.issue_type === 'KRITIKAL';
              const isActual = topic.issue_type === 'AKTUAL';

              return (
                <div
                  key={topic.issue_id}
                  className="cyber-card rounded-xl p-3.5 sm:p-4 hover:border-slate-300 dark:hover:border-white/[0.12] transition-colors flex flex-col md:flex-row md:items-center justify-between gap-3"
                >
                  {/* Left: Rank & Title */}
                  <div className="flex items-start gap-3 flex-1 min-w-0">
                    <span className="w-7 h-7 rounded-lg bg-slate-100 dark:bg-white/[0.06] text-slate-700 dark:text-slate-300 font-mono text-xs font-bold flex items-center justify-center shrink-0">
                      #{displayRank}
                    </span>

                    <div className="min-w-0 flex-1">
                      <div className="flex items-center gap-1.5 flex-wrap mb-1">
                        <span
                          className={`text-[9.5px] px-1.5 py-0.2 rounded font-mono font-bold uppercase ${
                            isCritical
                              ? 'bg-rose-500/10 text-rose-500 border border-rose-500/20'
                              : isActual
                              ? 'bg-amber-500/10 text-amber-500 border border-amber-500/20'
                              : 'bg-indigo-500/10 text-indigo-400 border border-indigo-500/20'
                          }`}
                        >
                          {topic.issue_type || 'AKTUAL'}
                        </span>

                        <span className="text-[9.5px] px-1.5 py-0.2 rounded font-mono bg-slate-100 dark:bg-white/[0.04] text-slate-600 dark:text-slate-400 border border-slate-200 dark:border-white/[0.06]">
                          {topic.category}
                        </span>

                        {topic.hashtag && (
                          <span className="text-[10px] font-mono font-semibold text-blue-500">
                            {topic.hashtag}
                          </span>
                        )}
                      </div>

                      <h3 className="text-xs font-semibold text-slate-800 dark:text-slate-100 truncate">
                        {topic.title}
                      </h3>

                      {/* Keywords Chips */}
                      <div className="flex items-center gap-1 mt-1.5 flex-wrap">
                        {topic.top_keywords?.slice(0, 4).map((kw, i) => (
                          <span
                            key={i}
                            className="text-[9.5px] font-mono px-1.5 py-0.2 rounded bg-slate-100 dark:bg-white/[0.03] text-slate-500 dark:text-slate-400"
                          >
                            {kw}
                          </span>
                        ))}
                      </div>
                    </div>
                  </div>

                  {/* Right: Metrics & Link */}
                  <div className="flex items-center justify-between md:justify-end gap-4 shrink-0 pt-2 md:pt-0 border-t md:border-t-0 border-slate-100 dark:border-white/[0.04]">
                    <div className="flex items-center gap-3 font-mono text-center">
                      <div>
                        <div className="text-[9px] text-slate-400 uppercase">Kanal</div>
                        <div className="text-xs font-semibold text-slate-700 dark:text-slate-300">
                          {topic.platform_count || 1}/5
                        </div>
                      </div>
                      <div>
                        <div className="text-[9px] text-slate-400 uppercase">Temuan</div>
                        <div className="text-xs font-semibold text-emerald-500">
                          {topic.recent_count_24h ?? topic.content_count ?? 0}
                        </div>
                      </div>
                      <div>
                        <div className="text-[9px] text-slate-400 uppercase">Urgensi</div>
                        <div className="text-xs font-semibold text-indigo-400">
                          {(topic.avg_urgency || 2.5).toFixed(1)}/5
                        </div>
                      </div>
                    </div>

                    <div className="flex items-center gap-2">
                      <div className="flex flex-col items-center">
                        <ScoreGauge score={topic.trending_score} size={46} />
                        <span className="text-[8px] font-mono text-slate-400">HotScore</span>
                      </div>

                      <Link
                        to={`/trending/${topic.issue_id}`}
                        className="px-2.5 py-1.5 rounded-lg bg-blue-500/10 text-blue-600 dark:text-blue-400 hover:bg-blue-500 hover:text-white transition-colors text-xs font-semibold flex items-center gap-1 font-mono"
                      >
                        <span>Buka</span>
                        <ArrowRight className="w-3 h-3" />
                      </Link>
                    </div>
                  </div>
                </div>
              );
            })}
          </div>
        )}
      </div>
    </div>
  );
};
