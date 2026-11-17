import React, { useEffect, useState, useMemo } from 'react';
import { Link } from 'react-router-dom';
import { apiClient } from '../api/client';
import { TrendingTopicItem, WordCloudItem, HotActorItem, TrendingResponse } from '../types';
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
  BarChart3,
  X,
  RotateCcw,
  Sparkles,
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
    { id: 'ALL', label: 'Semua Kategori' },
    { id: 'Politik', label: 'Politik' },
    { id: 'Keamanan', label: 'Keamanan' },
    { id: 'Sosial', label: 'Sosial' },
    { id: 'Ekonomi', label: 'Ekonomi' },
    { id: 'Ideologi', label: 'Ideologi' },
    { id: 'Pertahanan', label: 'Pertahanan' },
    { id: 'Budaya', label: 'Budaya' },
    { id: 'Non-Isu', label: 'Non-Isu' },
  ];

  const pillarDescriptions = {
    ALL: 'Seluruh isu strategis dan percakapan ruang siber yang terkelompokkan oleh algoritma klastering semantik TILIK.',
    AKTUAL: 'Isu Sedang Hangat & Mendesak: Masalah pemerintahan atau pelayanan publik yang ramai diperbincangkan masyarakat saat ini dan membutuhkan respons cepat aparatur intelijen.',
    KRITIKAL: 'Isu Paling Berisiko & Prioritas: Masalah krusial dengan tingkat bahaya/urgensi tinggi (≥3.8/5) seperti kebocoran data, penyadapan pejabat negara, korupsi, atau ancaman keamanan nasional.',
    TEMATIK: 'Payung Perencanaan & Fokus Kerja: Topik agenda strategis pemerintah lintas instansi/kementerian, seperti krisis iklim/karhutla, reformasi birokrasi, dan ketahanan pendidikan tinggi.',
  };

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
      setError(err?.message || 'Gagal memuat data radar trending topics');
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

  // Filter topics based on client-side keyword click (if active)
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

  // Top 8 issues for HotScore comparison bar chart
  const top8Issues = useMemo(() => {
    if (!data?.topics) return [];
    return [...data.topics].sort((a, b) => b.trending_score - a.trending_score).slice(0, 8);
  }, [data?.topics]);

  // Max mentions for relative actor progress bars
  const maxActorMentions = useMemo(() => {
    if (!data?.hot_actors || data.hot_actors.length === 0) return 1;
    return Math.max(...data.hot_actors.map((a) => a.mentions), 1);
  }, [data?.hot_actors]);

  // Max word count for word cloud scaling
  const maxWordCount = useMemo(() => {
    if (!data?.word_cloud || data.word_cloud.length === 0) return 1;
    return Math.max(...data.word_cloud.map((w) => w.count), 1);
  }, [data?.word_cloud]);

  return (
    <div className="space-y-6 pb-12">
      {/* ─────────────────────────────────────────────────────────────
          1. HEADER & SEARCH BAR
      ───────────────────────────────────────────────────────────── */}
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 border-b border-slate-200 dark:border-slate-800/80 pb-4">
        <div>
          <div className="flex items-center gap-2.5">
            <div className="w-9 h-9 rounded-xl bg-amber-500/10 border border-amber-500/30 flex items-center justify-center text-amber-500 shadow-sm shadow-amber-500/10">
              <Flame className="w-5 h-5" />
            </div>
            <div>
              <h1 className="text-lg font-extrabold tracking-tight text-slate-900 dark:text-white flex items-center gap-2">
                Radar Trending Topics & Tiga Pilar Isu
              </h1>
              <p className="text-xs text-slate-500 dark:text-slate-400">
                Pemantauan dinamika percakapan siber, eskalasi narasi publik, dan klasifikasi isu strategis nasional.
              </p>
            </div>
          </div>
        </div>

        {/* Search */}
        <form onSubmit={handleSearchSubmit} className="relative w-full md:w-72">
          <input
            type="text"
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            placeholder="Cari isu, tokoh, atau hashtag..."
            className="w-full pl-9 pr-8 py-2 bg-white dark:bg-slate-900 border border-slate-300 dark:border-slate-800 rounded-xl text-xs text-slate-800 dark:text-slate-200 placeholder:text-slate-400 dark:placeholder:text-slate-500 focus:outline-none focus:border-blue-500 focus:ring-1 focus:ring-blue-500 transition-all shadow-sm"
          />
          <Search className="w-3.5 h-3.5 text-slate-400 absolute left-3 top-3" />
          {search && (
            <button
              type="button"
              onClick={() => {
                setSearch('');
                fetchTrendingData();
              }}
              className="absolute right-2.5 top-2.5 text-slate-400 hover:text-slate-600 dark:hover:text-slate-200"
            >
              <X className="w-3.5 h-3.5" />
            </button>
          )}
        </form>
      </div>

      {/* ─────────────────────────────────────────────────────────────
          2. TOP KPI SUMMARY BAR (4 PILAR CARDS)
      ───────────────────────────────────────────────────────────── */}
      <div className="grid grid-cols-2 lg:grid-cols-4 gap-3.5">
        {/* Isu Aktual */}
        <button
          type="button"
          onClick={() => setSelectedPillar(selectedPillar === 'AKTUAL' ? 'ALL' : 'AKTUAL')}
          className={`p-3.5 rounded-xl border text-left transition-all duration-200 relative overflow-hidden ${
            selectedPillar === 'AKTUAL'
              ? 'bg-amber-500/10 border-amber-500/60 shadow-md shadow-amber-500/10 ring-1 ring-amber-500/30'
              : 'bg-white dark:bg-slate-900/80 border-slate-200 dark:border-slate-800 hover:border-amber-400 dark:hover:border-amber-500/40'
          }`}
        >
          <div className="flex items-center justify-between">
            <span className="text-[11px] font-bold text-amber-600 dark:text-amber-400 tracking-wide uppercase flex items-center gap-1.5">
              <Flame className="w-3.5 h-3.5" />
              Isu Aktual
            </span>
            <span className="text-xl font-extrabold font-mono text-slate-900 dark:text-white">
              {data ? data.total_actual : '–'}
            </span>
          </div>
          <div className="text-[10.5px] text-slate-500 dark:text-slate-400 mt-1 line-clamp-1">
            Masalah ramai saat ini & butuh respons cepat
          </div>
          <div className="text-[9px] font-mono text-amber-700 dark:text-amber-300/80 mt-2 font-semibold">
            {selectedPillar === 'AKTUAL' ? '● Aktif difilter' : 'Klik untuk filter →'}
          </div>
        </button>

        {/* Isu Kritikal */}
        <button
          type="button"
          onClick={() => setSelectedPillar(selectedPillar === 'KRITIKAL' ? 'ALL' : 'KRITIKAL')}
          className={`p-3.5 rounded-xl border text-left transition-all duration-200 relative overflow-hidden ${
            selectedPillar === 'KRITIKAL'
              ? 'bg-rose-500/10 border-rose-500/60 shadow-md shadow-rose-500/10 ring-1 ring-rose-500/30'
              : 'bg-white dark:bg-slate-900/80 border-slate-200 dark:border-slate-800 hover:border-rose-400 dark:hover:border-rose-500/40'
          }`}
        >
          <div className="flex items-center justify-between">
            <span className="text-[11px] font-bold text-rose-600 dark:text-rose-400 tracking-wide uppercase flex items-center gap-1.5">
              <ShieldAlert className="w-3.5 h-3.5" />
              Isu Kritikal
            </span>
            <span className="text-xl font-extrabold font-mono text-slate-900 dark:text-white">
              {data ? data.total_critical : '–'}
            </span>
          </div>
          <div className="text-[10.5px] text-slate-500 dark:text-slate-400 mt-1 line-clamp-1">
            Risiko tinggi & urgensi nasional (≥3.8/5)
          </div>
          <div className="text-[9px] font-mono text-rose-700 dark:text-rose-300/80 mt-2 font-semibold">
            {selectedPillar === 'KRITIKAL' ? '● Aktif difilter' : 'Klik untuk filter →'}
          </div>
        </button>

        {/* Isu Tematik */}
        <button
          type="button"
          onClick={() => setSelectedPillar(selectedPillar === 'TEMATIK' ? 'ALL' : 'TEMATIK')}
          className={`p-3.5 rounded-xl border text-left transition-all duration-200 relative overflow-hidden ${
            selectedPillar === 'TEMATIK'
              ? 'bg-indigo-500/10 border-indigo-500/60 shadow-md shadow-indigo-500/10 ring-1 ring-indigo-500/30'
              : 'bg-white dark:bg-slate-900/80 border-slate-200 dark:border-slate-800 hover:border-indigo-400 dark:hover:border-indigo-500/40'
          }`}
        >
          <div className="flex items-center justify-between">
            <span className="text-[11px] font-bold text-indigo-600 dark:text-indigo-400 tracking-wide uppercase flex items-center gap-1.5">
              <Briefcase className="w-3.5 h-3.5" />
              Isu Tematik
            </span>
            <span className="text-xl font-extrabold font-mono text-slate-900 dark:text-white">
              {data ? data.total_thematic : '–'}
            </span>
          </div>
          <div className="text-[10.5px] text-slate-500 dark:text-slate-400 mt-1 line-clamp-1">
            Payung kerja strategis (RKP & Reformasi)
          </div>
          <div className="text-[9px] font-mono text-indigo-700 dark:text-indigo-300/80 mt-2 font-semibold">
            {selectedPillar === 'TEMATIK' ? '● Aktif difilter' : 'Klik untuk filter →'}
          </div>
        </button>

        {/* Total Terpantau */}
        <button
          type="button"
          onClick={() => setSelectedPillar('ALL')}
          className={`p-3.5 rounded-xl border text-left transition-all duration-200 relative overflow-hidden ${
            selectedPillar === 'ALL'
              ? 'bg-blue-500/10 border-blue-500/60 shadow-md shadow-blue-500/10 ring-1 ring-blue-500/30'
              : 'bg-white dark:bg-slate-900/80 border-slate-200 dark:border-slate-800 hover:border-blue-400 dark:hover:border-blue-500/40'
          }`}
        >
          <div className="flex items-center justify-between">
            <span className="text-[11px] font-bold text-blue-600 dark:text-blue-400 tracking-wide uppercase flex items-center gap-1.5">
              <Globe className="w-3.5 h-3.5" />
              Total Terpantau
            </span>
            <span className="text-xl font-extrabold font-mono text-slate-900 dark:text-white">
              {data ? data.total_topics : '–'}
            </span>
          </div>
          <div className="text-[10.5px] text-slate-500 dark:text-slate-400 mt-1 line-clamp-1">
            Seluruh klaster isu aktif di ruang siber
          </div>
          <div className="text-[9px] font-mono text-blue-700 dark:text-blue-300/80 mt-2 font-semibold">
            {selectedPillar === 'ALL' ? '● Semua Pilar' : 'Klik tampilkan semua'}
          </div>
        </button>
      </div>

      {/* ─────────────────────────────────────────────────────────────
          3. SEGMENTED TABS FOR 3 PILLARS + CONTEXT BANNER
      ───────────────────────────────────────────────────────────── */}
      <div className="space-y-2.5">
        <div className="flex items-center gap-2 overflow-x-auto pb-1 scrollbar-none">
          <button
            onClick={() => setSelectedPillar('ALL')}
            className={`px-3 py-1.5 rounded-lg text-xs font-semibold whitespace-nowrap transition-colors flex items-center gap-1.5 ${
              selectedPillar === 'ALL'
                ? 'bg-slate-900 dark:bg-white text-white dark:text-slate-900 shadow-sm'
                : 'bg-white dark:bg-slate-900 text-slate-600 dark:text-slate-400 border border-slate-200 dark:border-slate-800 hover:border-slate-300'
            }`}
          >
            <Globe className="w-3.5 h-3.5" />
            Semua Isu ({data?.total_topics ?? 0})
          </button>

          <button
            onClick={() => setSelectedPillar('AKTUAL')}
            className={`px-3 py-1.5 rounded-lg text-xs font-semibold whitespace-nowrap transition-colors flex items-center gap-1.5 ${
              selectedPillar === 'AKTUAL'
                ? 'bg-amber-500 text-slate-950 font-bold shadow-sm shadow-amber-500/20'
                : 'bg-white dark:bg-slate-900 text-slate-600 dark:text-slate-400 border border-slate-200 dark:border-slate-800 hover:border-amber-400'
            }`}
          >
            <Flame className="w-3.5 h-3.5 text-amber-500" />
            Isu Aktual (Top Trending: {data?.total_actual ?? 0})
          </button>

          <button
            onClick={() => setSelectedPillar('KRITIKAL')}
            className={`px-3 py-1.5 rounded-lg text-xs font-semibold whitespace-nowrap transition-colors flex items-center gap-1.5 ${
              selectedPillar === 'KRITIKAL'
                ? 'bg-rose-600 text-white font-bold shadow-sm shadow-rose-600/20'
                : 'bg-white dark:bg-slate-900 text-slate-600 dark:text-slate-400 border border-slate-200 dark:border-slate-800 hover:border-rose-400'
            }`}
          >
            <ShieldAlert className="w-3.5 h-3.5 text-rose-500" />
            Isu Kritikal (Prioritas Risiko: {data?.total_critical ?? 0})
          </button>

          <button
            onClick={() => setSelectedPillar('TEMATIK')}
            className={`px-3 py-1.5 rounded-lg text-xs font-semibold whitespace-nowrap transition-colors flex items-center gap-1.5 ${
              selectedPillar === 'TEMATIK'
                ? 'bg-indigo-600 text-white font-bold shadow-sm shadow-indigo-600/20'
                : 'bg-white dark:bg-slate-900 text-slate-600 dark:text-slate-400 border border-slate-200 dark:border-slate-800 hover:border-indigo-400'
            }`}
          >
            <Briefcase className="w-3.5 h-3.5 text-indigo-400" />
            Isu Tematik (Payung Kerja: {data?.total_thematic ?? 0})
          </button>
        </div>

        {/* Context Definition Banner */}
        <div className="px-3.5 py-2 rounded-xl bg-slate-100/80 dark:bg-slate-900/60 border border-slate-200 dark:border-slate-800 text-[11px] text-slate-600 dark:text-slate-300 flex items-start gap-2 leading-relaxed">
          <Sparkles className="w-3.5 h-3.5 text-amber-500 shrink-0 mt-0.5" />
          <span>
            <strong>Panduan Intelijen:</strong> {pillarDescriptions[selectedPillar]}
          </span>
        </div>
      </div>

      {/* ─────────────────────────────────────────────────────────────
          4. IPOLEKSOSBUDHANKAM CATEGORY PILLS
      ───────────────────────────────────────────────────────────── */}
      <div className="flex items-center gap-1.5 overflow-x-auto pb-1 scrollbar-none">
        {categories.map((cat) => (
          <button
            key={cat.id}
            onClick={() => setSelectedCategory(cat.id)}
            className={`px-3 py-1 rounded-lg text-xs font-medium whitespace-nowrap transition-colors ${
              selectedCategory === cat.id
                ? 'bg-blue-600 text-white font-semibold shadow-sm shadow-blue-500/20'
                : 'bg-white dark:bg-slate-900 text-slate-600 dark:text-slate-400 hover:text-slate-900 dark:hover:text-slate-200 border border-slate-200 dark:border-slate-800'
            }`}
          >
            {cat.label}
          </button>
        ))}
      </div>

      {/* ─────────────────────────────────────────────────────────────
          5. ROW 1: WORD CLOUD & HOT ACTORS DUAL PANEL
      ───────────────────────────────────────────────────────────── */}
      <div className="grid grid-cols-1 lg:grid-cols-12 gap-4">
        {/* Left: Word Cloud / Kata Kunci Percakapan (7 Cols) */}
        <div className="lg:col-span-7 cyber-card rounded-xl p-4 flex flex-col justify-between">
          <div>
            <div className="flex items-center justify-between mb-2">
              <div className="flex items-center gap-2">
                <Tag className="w-4 h-4 text-blue-500" />
                <h3 className="text-xs font-bold text-slate-900 dark:text-white uppercase tracking-wider">
                  Radar Kata Kunci & Percakapan Siber
                </h3>
              </div>
              <span className="text-[10px] font-mono text-slate-400">
                {data?.word_cloud?.length || 0} Kata Terpilih
              </span>
            </div>
            <p className="text-[11px] text-slate-500 dark:text-slate-400 mb-3">
              Kata kunci berfrekuensi tinggi setelah pembersihan stopwords bilingual (ID & EN) dan sampah antarmuka. Klik kata untuk memfilter isu.
            </p>

            {/* Keyword Filter Indicator */}
            {selectedKeyword && (
              <div className="mb-3 px-2.5 py-1 rounded-lg bg-blue-50 dark:bg-blue-950/80 border border-blue-200 dark:border-blue-800/60 flex items-center justify-between text-xs">
                <span className="text-blue-700 dark:text-blue-300 font-medium">
                  Memfilter isu dengan kata kunci: <strong>"{selectedKeyword}"</strong>
                </span>
                <button
                  onClick={() => setSelectedKeyword(null)}
                  className="inline-flex items-center gap-1 text-[11px] font-semibold text-rose-500 hover:underline"
                >
                  <RotateCcw className="w-3 h-3" />
                  Reset Filter
                </button>
              </div>
            )}

            {/* Word Cloud Box */}
            <div className="min-h-[140px] p-3 rounded-lg bg-slate-50 dark:bg-slate-950/60 border border-slate-200 dark:border-slate-800/80 flex flex-wrap items-center gap-2">
              {loading ? (
                <div className="flex flex-wrap gap-2 w-full">
                  {[...Array(16)].map((_, i) => (
                    <div
                      key={i}
                      className="h-6 rounded-md skeleton-shimmer"
                      style={{ width: `${40 + (i % 5) * 18}px` }}
                    />
                  ))}
                </div>
              ) : !data?.word_cloud || data.word_cloud.length === 0 ? (
                <div className="w-full text-center py-6 text-slate-400 text-xs">
                  Belum ada kata kunci yang terkumpul dari postingan aktif.
                </div>
              ) : (
                data.word_cloud.map((item, idx) => {
                  const weightRatio = item.count / maxWordCount;
                  const isSelected = selectedKeyword === item.text;

                  // Dynamic font size classes
                  const sizeClass =
                    weightRatio > 0.75
                      ? 'text-sm font-extrabold px-2.5 py-1'
                      : weightRatio > 0.45
                      ? 'text-xs font-bold px-2 py-0.5'
                      : 'text-[11px] font-medium px-1.5 py-0.5';

                  // Dynamic urgency color classes
                  const colorClass =
                    item.avg_urgency >= 3.8
                      ? isSelected
                        ? 'bg-rose-600 text-white border-rose-600 ring-2 ring-rose-400'
                        : 'bg-rose-50 dark:bg-rose-950/70 text-rose-700 dark:text-rose-300 border-rose-300 dark:border-rose-800/80 hover:bg-rose-100 dark:hover:bg-rose-900/50'
                      : item.avg_urgency >= 2.8
                      ? isSelected
                        ? 'bg-amber-600 text-white border-amber-600 ring-2 ring-amber-400'
                        : 'bg-amber-50 dark:bg-amber-950/70 text-amber-700 dark:text-amber-300 border-amber-300 dark:border-amber-800/80 hover:bg-amber-100 dark:hover:bg-amber-900/50'
                      : isSelected
                      ? 'bg-blue-600 text-white border-blue-600 ring-2 ring-blue-400'
                      : 'bg-white dark:bg-slate-900 text-slate-700 dark:text-slate-300 border-slate-200 dark:border-slate-800 hover:border-slate-400 dark:hover:border-slate-700';

                  return (
                    <button
                      key={idx}
                      onClick={() =>
                        setSelectedKeyword(selectedKeyword === item.text ? null : item.text)
                      }
                      title={`Frekuensi: ${item.count} post | Rerata Urgensi: ${item.avg_urgency.toFixed(1)}/5`}
                      className={`rounded-lg border transition-all duration-150 inline-flex items-center gap-1 cursor-pointer select-none ${sizeClass} ${colorClass}`}
                    >
                      <span>{item.text}</span>
                      <span className="text-[9px] font-mono opacity-70">({item.count})</span>
                    </button>
                  );
                })
              )}
            </div>
          </div>

          <div className="flex items-center justify-between text-[10px] text-slate-400 mt-2.5 pt-2 border-t border-slate-100 dark:border-slate-800/60 font-mono">
            <div className="flex items-center gap-3">
              <span className="flex items-center gap-1">
                <span className="w-2 h-2 rounded-full bg-rose-500 inline-block" />
                Urgensi Tinggi (≥3.8)
              </span>
              <span className="flex items-center gap-1">
                <span className="w-2 h-2 rounded-full bg-amber-500 inline-block" />
                Urgensi Menengah (≥2.8)
              </span>
              <span className="flex items-center gap-1">
                <span className="w-2 h-2 rounded-full bg-slate-400 inline-block" />
                Normal
              </span>
            </div>
            <span>Koreksi Sastrawi & Stopwords</span>
          </div>
        </div>

        {/* Right: Hot Actors / Tokoh Kunci (5 Cols) */}
        <div className="lg:col-span-5 cyber-card rounded-xl p-4 flex flex-col justify-between">
          <div>
            <div className="flex items-center justify-between mb-2">
              <div className="flex items-center gap-2">
                <Users className="w-4 h-4 text-emerald-500" />
                <h3 className="text-xs font-bold text-slate-900 dark:text-white uppercase tracking-wider">
                  Tokoh & Institusi Kunci Terpantau
                </h3>
              </div>
              <span className="text-[10px] font-mono text-slate-400">Top 8 Aktor</span>
            </div>
            <p className="text-[11px] text-slate-500 dark:text-slate-400 mb-3">
              Entitas politisi, pejabat negara, dan lembaga pemerintah dengan intensitas kemunculan tertinggi.
            </p>

            {/* Actors List with Proportional Progress Bars */}
            <div className="space-y-2">
              {loading ? (
                <div className="space-y-2">
                  {[...Array(5)].map((_, i) => (
                    <div key={i} className="h-9 rounded-lg skeleton-shimmer" />
                  ))}
                </div>
              ) : !data?.hot_actors || data.hot_actors.length === 0 ? (
                <div className="text-center py-6 text-slate-400 text-xs">
                  Belum ada tokoh spesifik yang terdeteksi pada klaster aktif.
                </div>
              ) : (
                data.hot_actors.map((actor, idx) => {
                  const percent = Math.min(100, Math.round((actor.mentions / maxActorMentions) * 100));
                  return (
                    <button
                      key={idx}
                      onClick={() => setSearch(actor.name)}
                      className="w-full text-left p-2 rounded-lg bg-slate-50 dark:bg-slate-950/60 border border-slate-200 dark:border-slate-800/80 hover:border-emerald-500/50 transition-all group"
                    >
                      <div className="flex items-center justify-between text-xs mb-1">
                        <span className="font-bold text-slate-800 dark:text-slate-100 group-hover:text-emerald-500 transition-colors line-clamp-1">
                          {actor.name}
                        </span>
                        <div className="flex items-center gap-1.5 shrink-0">
                          <span className="text-[9.5px] px-1.5 py-0.2 rounded font-mono bg-slate-200 dark:bg-slate-800 text-slate-700 dark:text-slate-300">
                            {actor.category}
                          </span>
                          <span className="text-[10px] font-mono font-bold text-emerald-600 dark:text-emerald-400">
                            {actor.mentions} post
                          </span>
                        </div>
                      </div>

                      {/* Progress Bar */}
                      <div className="w-full h-1.5 rounded-full bg-slate-200 dark:bg-slate-800 overflow-hidden">
                        <div
                          className="h-full rounded-full bg-gradient-to-r from-emerald-500 to-teal-400 transition-all duration-300"
                          style={{ width: `${percent}%` }}
                        />
                      </div>
                    </button>
                  );
                })
              )}
            </div>
          </div>

          <div className="text-[10px] text-slate-400 mt-2.5 pt-2 border-t border-slate-100 dark:border-slate-800/60 flex items-center justify-between font-mono">
            <span>Klik nama tokoh untuk mencari postingan</span>
            <span>NER Regex & Named Entity Extraction</span>
          </div>
        </div>
      </div>

      {/* ─────────────────────────────────────────────────────────────
          6. ROW 2: ESCALATION COMPARISON HORIZONTAL BAR CHART (TOP 8)
      ───────────────────────────────────────────────────────────── */}
      {top8Issues.length > 0 && (
        <div className="cyber-card rounded-xl p-4">
          <div className="flex items-center justify-between mb-2">
            <div className="flex items-center gap-2">
              <BarChart3 className="w-4 h-4 text-amber-500" />
              <h3 className="text-xs font-bold text-slate-900 dark:text-white uppercase tracking-wider">
                Komparasi Skor Eskalasi Isu (Top 8 HotScore)
              </h3>
            </div>
            <span className="text-[10px] font-mono text-slate-400">Peringkat Berjalan</span>
          </div>
          <p className="text-[11px] text-slate-500 dark:text-slate-400 mb-3.5">
            Perbandingan tingkat resonansi dan keparahan dampak isu berdasarkan kalkulasi multivariat TILIK (Volumetrik 24J + Kecepatan + Multi-Platform + Bobot Urgensi).
          </p>

          <div className="space-y-2.5">
            {top8Issues.map((issue, idx) => {
              const score = issue.trending_score || 0;
              const barPercent = Math.min(100, Math.max(10, score));

              const isCritical = issue.issue_type === 'KRITIKAL' || score >= 60;
              const isActual = issue.issue_type === 'AKTUAL';

              const barBg = isCritical
                ? 'from-rose-500 to-amber-500'
                : isActual
                ? 'from-amber-500 to-yellow-400'
                : 'from-blue-500 to-indigo-500';

              return (
                <div
                  key={issue.issue_id}
                  className="p-2.5 rounded-lg bg-slate-50 dark:bg-slate-950/60 border border-slate-200 dark:border-slate-800/80 flex flex-col sm:flex-row sm:items-center justify-between gap-2.5 hover:border-slate-400 dark:hover:border-slate-700 transition-all"
                >
                  <div className="flex items-center gap-2.5 flex-1 min-w-0">
                    <span className="w-6 h-6 rounded-md bg-slate-200 dark:bg-slate-800 text-slate-700 dark:text-slate-300 font-mono text-xs font-extrabold flex items-center justify-center shrink-0">
                      #{idx + 1}
                    </span>

                    <div className="min-w-0 flex-1">
                      <div className="flex items-center gap-2 flex-wrap">
                        {issue.hashtag && (
                          <span className="font-mono text-[10px] font-bold text-blue-600 dark:text-blue-400 bg-blue-50 dark:bg-blue-950/80 px-1.5 py-0.5 rounded border border-blue-200 dark:border-blue-800/40">
                            {issue.hashtag}
                          </span>
                        )}
                        <span className="text-[10px] px-1.5 py-0.2 rounded font-semibold bg-slate-100 dark:bg-slate-800 text-slate-600 dark:text-slate-300 border border-slate-200 dark:border-slate-700">
                          {issue.category}
                        </span>
                        <span
                          className={`text-[9px] px-1.5 py-0.2 rounded font-bold uppercase ${
                            issue.issue_type === 'KRITIKAL'
                              ? 'bg-rose-50 dark:bg-rose-950 text-rose-600 dark:text-rose-400 border border-rose-300 dark:border-rose-800'
                              : issue.issue_type === 'AKTUAL'
                              ? 'bg-amber-50 dark:bg-amber-950 text-amber-600 dark:text-amber-400 border border-amber-300 dark:border-amber-800'
                              : 'bg-indigo-50 dark:bg-indigo-950 text-indigo-600 dark:text-indigo-400 border border-indigo-300 dark:border-indigo-800'
                          }`}
                        >
                          {issue.issue_type || 'AKTUAL'}
                        </span>
                      </div>
                      <h4 className="text-xs font-bold text-slate-800 dark:text-slate-200 truncate mt-0.5">
                        {issue.title}
                      </h4>
                    </div>
                  </div>

                  {/* Horizontal Bar Fill */}
                  <div className="flex items-center gap-3 shrink-0 sm:w-64">
                    <div className="flex-1 h-3 rounded-full bg-slate-200 dark:bg-slate-800 overflow-hidden">
                      <div
                        className={`h-full rounded-full bg-gradient-to-r ${barBg} transition-all duration-300`}
                        style={{ width: `${barPercent}%` }}
                      />
                    </div>
                    <div className="text-right w-14 font-mono font-extrabold text-xs text-slate-800 dark:text-slate-100">
                      {score.toFixed(1)}
                    </div>
                    <Link
                      to={`/trending/${issue.issue_id}`}
                      className="text-slate-400 hover:text-blue-500 p-1 transition-colors"
                      title="Buka Dossier Isu"
                    >
                      <ArrowRight className="w-4 h-4" />
                    </Link>
                  </div>
                </div>
              );
            })}
          </div>
        </div>
      )}

      {/* ─────────────────────────────────────────────────────────────
          7. ROW 3: RANKED ISSUE CARDS GRID
      ───────────────────────────────────────────────────────────── */}
      <div>
        <div className="flex items-center justify-between mb-3">
          <div className="flex items-center gap-2">
            <Layers className="w-4 h-4 text-blue-500" />
            <h3 className="text-xs font-bold text-slate-900 dark:text-white uppercase tracking-wider">
              Daftar Isu Terpantau ({filteredTopics.length} Isu)
            </h3>
          </div>
          {(selectedKeyword || selectedCategory !== 'ALL' || selectedPillar !== 'ALL' || search) && (
            <button
              onClick={resetAllFilters}
              className="text-xs text-blue-600 dark:text-blue-400 hover:underline flex items-center gap-1 font-medium"
            >
              <RotateCcw className="w-3 h-3" />
              Reset Semua Filter
            </button>
          )}
        </div>

        {loading ? (
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
            {[1, 2, 3, 4, 5, 6].map((i) => (
              <div key={i} className="cyber-card rounded-xl p-4 flex flex-col justify-between space-y-4">
                <div className="space-y-2.5">
                  <div className="flex justify-between items-start">
                    <div className="h-5 w-24 rounded skeleton-shimmer" />
                    <div className="w-12 h-12 rounded-full skeleton-shimmer shrink-0" />
                  </div>
                  <div className="h-4 w-full rounded skeleton-shimmer" />
                  <div className="h-3 w-4/5 rounded skeleton-shimmer" />
                  <div className="h-10 w-full rounded skeleton-shimmer" />
                </div>
                <div className="h-4 w-32 rounded skeleton-shimmer" />
              </div>
            ))}
          </div>
        ) : error ? (
          <div className="p-8 cyber-card rounded-xl text-center">
            <AlertTriangle className="w-8 h-8 text-rose-500 mx-auto mb-2" />
            <p className="text-rose-600 dark:text-rose-300 text-sm font-semibold">{error}</p>
            <button
              onClick={fetchTrendingData}
              className="mt-3 px-3 py-1.5 rounded-lg bg-blue-600 text-white text-xs font-medium hover:bg-blue-700 transition-colors"
            >
              Coba Muat Ulang
            </button>
          </div>
        ) : filteredTopics.length === 0 ? (
          <div className="cyber-card rounded-xl p-10 text-center text-slate-400">
            <Layers className="w-8 h-8 text-slate-400 mx-auto mb-2" />
            <h3 className="text-xs font-semibold text-slate-600 dark:text-slate-300">
              Tidak ada topik yang sesuai kriteria pencarian
            </h3>
            <p className="text-[11px] text-slate-400 mt-0.5">
              Coba ubah kata kunci, hapus filter pilar, atau pilih kategori lainnya.
            </p>
            <button
              onClick={resetAllFilters}
              className="mt-4 px-3.5 py-1.5 rounded-lg bg-blue-600 text-white text-xs font-medium hover:bg-blue-700 transition-colors inline-flex items-center gap-1.5"
            >
              <RotateCcw className="w-3.5 h-3.5" />
              Reset Semua Filter
            </button>
          </div>
        ) : (
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
            {filteredTopics.map((topic, index) => {
              const displayRank = topic.rank ?? index + 1;
              const isCritical = topic.issue_type === 'KRITIKAL';
              const isThematic = topic.issue_type === 'TEMATIK';

              return (
                <div
                  key={topic.issue_id}
                  className={`cyber-card rounded-xl p-4 flex flex-col justify-between transition-all duration-200 relative ${
                    isCritical
                      ? 'border-rose-300/60 dark:border-rose-900/40 hover:border-rose-500'
                      : isThematic
                      ? 'border-indigo-300/60 dark:border-indigo-900/40 hover:border-indigo-500'
                      : 'hover:border-blue-400 dark:hover:border-blue-500/40'
                  }`}
                >
                  <div>
                    {/* Header: Rank, Badges, Gauge */}
                    <div className="flex items-start justify-between gap-3 mb-2.5">
                      <div className="flex-1">
                        <div className="flex items-center gap-1.5 flex-wrap">
                          {/* Rank Badge */}
                          <span className="w-6 h-6 rounded-lg font-mono text-xs font-extrabold flex items-center justify-center bg-slate-900 text-white dark:bg-white dark:text-slate-900 shadow-sm">
                            #{displayRank}
                          </span>

                          {/* Category Badge */}
                          <span className="px-2 py-0.5 rounded text-[10px] font-semibold bg-blue-50 dark:bg-blue-950/80 text-blue-600 dark:text-blue-400 border border-blue-200 dark:border-blue-800/40 uppercase tracking-wider">
                            {topic.category}
                          </span>

                          {/* 3 Pillar Badge */}
                          <span
                            className={`px-2 py-0.5 rounded text-[10px] font-bold tracking-wider font-mono uppercase border ${
                              isCritical
                                ? 'bg-rose-50 dark:bg-rose-950/80 text-rose-600 dark:text-rose-400 border-rose-300 dark:border-rose-800/60'
                                : isThematic
                                ? 'bg-indigo-50 dark:bg-indigo-950/80 text-indigo-600 dark:text-indigo-400 border-indigo-300 dark:border-indigo-800/60'
                                : 'bg-amber-50 dark:bg-amber-950/80 text-amber-600 dark:text-amber-400 border-amber-300 dark:border-amber-800/60'
                            }`}
                          >
                            {topic.issue_type || 'AKTUAL'}
                          </span>
                        </div>

                        {/* Title with Hashtag */}
                        <h3 className="text-xs font-bold text-slate-800 dark:text-slate-100 mt-2.5 line-clamp-2 leading-snug">
                          {topic.title}
                        </h3>

                        {/* Classification Reason / Note */}
                        {topic.issue_type_reason && (
                          <p className="text-[10px] text-slate-500 dark:text-slate-400 mt-1 line-clamp-1 italic">
                            {topic.issue_type_reason}
                          </p>
                        )}
                      </div>

                      {/* Score Gauge */}
                      <div className="flex flex-col items-center shrink-0">
                        <ScoreGauge score={topic.trending_score} size={52} />
                        <span className="text-[9px] font-mono text-slate-400 font-semibold mt-0.5">
                          HotScore
                        </span>
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

                    {/* Keywords Chips */}
                    <div className="space-y-1">
                      <div className="flex flex-wrap gap-1">
                        {topic.top_keywords && topic.top_keywords.slice(0, 4).map((kw, i) => (
                          <button
                            key={i}
                            onClick={() => setSelectedKeyword(selectedKeyword === kw ? null : kw)}
                            className={`text-[10px] font-mono px-2 py-0.5 rounded border transition-colors ${
                              selectedKeyword === kw
                                ? 'bg-blue-600 text-white border-blue-600'
                                : 'bg-slate-100 dark:bg-slate-800 text-slate-600 dark:text-slate-300 border-slate-200 dark:border-slate-700 hover:border-blue-400'
                            }`}
                          >
                            {kw}
                          </button>
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
              );
            })}
          </div>
        )}
      </div>
    </div>
  );
};
