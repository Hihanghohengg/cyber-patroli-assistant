import React, { useEffect, useState, useMemo, useRef } from 'react';
import { Link } from 'react-router-dom';
import { apiClient } from '../api/client';
import { useAuth } from '../context/AuthContext';
import { KPICard } from '../components/common/KPICard';
import {
  DualLineChart,
  DualLinePoint,
  VerticalBarChart,
  VerticalBarItem,
  DonutChart,
  DonutItem,
  HorizontalBarList,
  ScoreGauge,
} from '../components/common/Charts';
import {
  FileText,
  Flame,
  CheckCircle,
  AlertTriangle,
  ArrowRight,
  TrendingUp,
  ShieldCheck,
  UserCheck,
  Radio,
  Download,
  FileDown,
  Filter,
  RotateCcw,
  ExternalLink,
  Layers,
  BarChart2,
  XCircle,
  Tag,
  Edit3,
  ChevronDown,
} from 'lucide-react';

export const OverviewPage: React.FC = () => {
  const { user } = useAuth();

  // Active View Tab
  const [activeTab, setActiveTab] = useState<'proposal' | 'intel'>('proposal');

  // Filter Bar State
  const [dateFrom, setDateFrom] = useState<string>('');
  const [dateTo, setDateTo] = useState<string>('');
  const [selectedPlatform, setSelectedPlatform] = useState<string>('Semua');
  const [selectedCategory, setSelectedCategory] = useState<string>('Semua');
  const [selectedRisk, setSelectedRisk] = useState<string>('Semua');
  const [selectedStatus, setSelectedStatus] = useState<string>('Semua');

  // Export dropdown state
  const [showExportMenu, setShowExportMenu] = useState<boolean>(false);
  const [exportingFormat, setExportingFormat] = useState<'pdf' | 'csv' | 'daily_md' | 'daily_pdf' | null>(null);
  const exportMenuRef = useRef<HTMLDivElement>(null);

  // Data states
  const [summary, setSummary] = useState<any>(null);
  const [timeseries, setTimeseries] = useState<DualLinePoint[]>([]);
  const [topTopics, setTopTopics] = useState<any[]>([]);
  const [topActors, setTopActors] = useState<any[]>([]);
  const [topSources, setTopSources] = useState<any[]>([]);
  const [reports, setReports] = useState<any[]>([]);
  const [trendingStats, setTrendingStats] = useState<any>(null);

  const [loading, setLoading] = useState<boolean>(true);
  const [error, setError] = useState<string | null>(null);

  // Close export dropdown when clicking outside
  useEffect(() => {
    const handleClickOutside = (event: MouseEvent) => {
      if (exportMenuRef.current && !exportMenuRef.current.contains(event.target as Node)) {
        setShowExportMenu(false);
      }
    };
    document.addEventListener('mousedown', handleClickOutside);
    return () => document.removeEventListener('mousedown', handleClickOutside);
  }, []);

  // Fetch all analytical data based on active filters
  const fetchData = async () => {
    try {
      setLoading(true);
      setError(null);

      const filterParams: any = {};
      if (dateFrom) filterParams.date_from = dateFrom;
      if (dateTo) filterParams.date_to = dateTo;
      if (selectedPlatform !== 'Semua') filterParams.platform = selectedPlatform.toLowerCase();
      if (selectedCategory !== 'Semua') filterParams.category = selectedCategory;
      if (selectedRisk !== 'Semua') filterParams.risk_level = selectedRisk;

      const [sumRes, tsRes, topTRes, topARes, topSRes, repRes, trendRes] = await Promise.all([
        apiClient.v1.getSummary(filterParams).catch(() => null),
        apiClient.v1.getTimeseries({
          date_from: dateFrom || undefined,
          date_to: dateTo || undefined,
          interval: 'day',
        }).catch(() => ({ series: [] })),
        apiClient.v1.getTop('topics', 8).catch(() => ({ items: [] })),
        apiClient.v1.getTop('actors', 8).catch(() => ({ items: [] })),
        apiClient.v1.getTop('sources', 8).catch(() => ({ items: [] })),
        apiClient.v1.getReports({
          platform: selectedPlatform !== 'Semua' ? selectedPlatform.toLowerCase() : undefined,
          category: selectedCategory !== 'Semua' ? selectedCategory : undefined,
          risk: selectedRisk !== 'Semua' ? selectedRisk : undefined,
          status: selectedStatus !== 'Semua' ? selectedStatus : undefined,
          limit: 50,
        }).catch(() => ({ items: [] })),
        apiClient.overview.get().catch(() => null),
      ]);

      setSummary(sumRes);
      setTimeseries(tsRes?.series || []);
      setTopTopics(topTRes?.items || []);
      setTopActors(topARes?.items || []);
      setTopSources(topSRes?.items || []);
      setReports(repRes?.items || []);
      setTrendingStats(trendRes);
    } catch (err: any) {
      setError('Gagal memuat data analitik patroli siber.');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchData();
  }, [dateFrom, dateTo, selectedPlatform, selectedCategory, selectedRisk, selectedStatus]);

  // Reset Filters
  const handleResetFilters = () => {
    setDateFrom('');
    setDateTo('');
    setSelectedPlatform('Semua');
    setSelectedCategory('Semua');
    setSelectedRisk('Semua');
    setSelectedStatus('Semua');
  };

  const hasActiveFilters =
    dateFrom ||
    dateTo ||
    selectedPlatform !== 'Semua' ||
    selectedCategory !== 'Semua' ||
    selectedRisk !== 'Semua' ||
    selectedStatus !== 'Semua';

  // Secure Blob Export PDF Dossier / CSV Metadata / Laporan Harian
  const handleExport = async (fmt: 'pdf' | 'csv' | 'daily_md' | 'daily_pdf') => {
    setShowExportMenu(false);
    try {
      setExportingFormat(fmt);
      if (fmt === 'daily_md') {
        await apiClient.reports.dailyExportBlob(undefined, 'md');
      } else if (fmt === 'daily_pdf') {
        await apiClient.reports.dailyExportBlob(undefined, 'pdf');
      } else {
        await apiClient.v1.exportBlob(fmt, {
          date_from: dateFrom || undefined,
          date_to: dateTo || undefined,
          category: selectedCategory !== 'Semua' ? selectedCategory : undefined,
          risk_level: selectedRisk !== 'Semua' ? selectedRisk : undefined,
        });
      }
    } catch (err) {
      alert('Gagal mengekspor berkas laporan.');
    } finally {
      setExportingFormat(null);
    }
  };

  // Visual 2: Data Per Platform
  const platformBarItems: VerticalBarItem[] = useMemo(() => {
    if (!summary?.distribusi_platform) return [];
    const colorMap: Record<string, string> = {
      INSTAGRAM: '#ec4899',
      TIKTOK: '#06b6d4',
      YOUTUBE: '#ef4444',
      MANUAL: '#a855f7',
    };
    return ['INSTAGRAM', 'TIKTOK', 'YOUTUBE'].map((plat) => ({
      label: plat,
      count: summary.distribusi_platform[plat] || 0,
      color: colorMap[plat] || '#38bdf8',
      key: plat,
    }));
  }, [summary]);

  // Visual 3: Data Per Kategori
  const categoryBarItems = useMemo(() => {
    if (!summary?.distribusi_kategori) return [];
    const colorMap: Record<string, string> = {
      HOAKS: '#ef4444',
      DI_LUAR_KONTEKS: '#f59e0b',
      UJARAN_KEBENCIAN: '#ec4899',
      PROVOKASI_SARA: '#8b5cf6',
    };
    const desired = ['HOAKS', 'DI_LUAR_KONTEKS', 'UJARAN_KEBENCIAN', 'PROVOKASI_SARA'];
    return desired.map((cat) => ({
      label: cat.replace(/_/g, ' '),
      count: summary.distribusi_kategori[cat] || 0,
      color: colorMap[cat] || '#3b82f6',
      key: cat,
    }));
  }, [summary]);

  // Visual 4: Donut Distribusi Risiko
  const riskDonutItems: DonutItem[] = useMemo(() => {
    if (!summary?.distribusi_risiko) return [];
    const colorMap: Record<string, string> = {
      TINGGI: '#ef4444',
      SEDANG: '#f59e0b',
      RENDAH: '#10b981',
    };
    return ['SEDANG', 'TINGGI', 'RENDAH'].map((rsk) => ({
      label: rsk,
      count: summary.distribusi_risiko[rsk] || 0,
      color: colorMap[rsk] || '#64748b',
      key: rsk,
    }));
  }, [summary]);

  // Visual 8: Vertical Bar Kesepakatan AI vs Analis
  const agreementBarItems: VerticalBarItem[] = useMemo(() => {
    if (!summary?.putusan_evaluasi) return [];
    return [
      {
        label: 'VALIDATED',
        count: summary.putusan_evaluasi.VALIDATED || 0,
        color: '#10b981',
        key: 'VALIDATED',
      },
      {
        label: 'MODIFIED',
        count: summary.putusan_evaluasi.MODIFIED || 0,
        color: '#f59e0b',
        key: 'MODIFIED',
      },
      {
        label: 'REJECTED',
        count: summary.putusan_evaluasi.REJECTED || 0,
        color: '#f43f5e',
        key: 'REJECTED',
      },
    ];
  }, [summary]);

  return (
    <div className="space-y-5">
      {/* ── Page Header & Single Download Dropdown ── */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3">
        <div>
          <h1 className="text-base font-bold tracking-tight text-slate-900 dark:text-white flex items-center gap-2">
            <ShieldCheck className="w-5 h-5 text-blue-600 dark:text-blue-400" />
            Operasional Patroli Siber
          </h1>
        </div>

        {/* Tab Selector & Sleek Download Dropdown Button */}
        <div className="flex items-center gap-2.5">
          <div className="bg-slate-200/80 dark:bg-slate-900/80 p-0.5 rounded-lg border border-slate-300 dark:border-slate-800 flex items-center text-xs">
            <button
              onClick={() => setActiveTab('proposal')}
              className={`px-3 py-1 rounded-md font-medium transition-all flex items-center gap-1.5 ${
                activeTab === 'proposal'
                  ? 'bg-white dark:bg-blue-600/20 text-blue-600 dark:text-blue-300 shadow-sm'
                  : 'text-slate-600 dark:text-slate-400 hover:text-slate-900 dark:hover:text-slate-200'
              }`}
            >
              <BarChart2 className="w-3.5 h-3.5" />
              <span>Ringkasan Metrik</span>
            </button>
            <button
              onClick={() => setActiveTab('intel')}
              className={`px-3 py-1 rounded-md font-medium transition-all flex items-center gap-1.5 ${
                activeTab === 'intel'
                  ? 'bg-white dark:bg-blue-600/20 text-blue-600 dark:text-blue-300 shadow-sm'
                  : 'text-slate-600 dark:text-slate-400 hover:text-slate-900 dark:hover:text-slate-200'
              }`}
            >
              <Flame className="w-3.5 h-3.5" />
              <span>Radar & Sentimen</span>
            </button>
          </div>

          {/* Single Download Dropdown Button */}
          <div className="relative" ref={exportMenuRef}>
            <button
              onClick={() => setShowExportMenu(!showExportMenu)}
              disabled={exportingFormat !== null}
              className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-semibold bg-white dark:bg-slate-900 text-slate-800 dark:text-slate-200 border border-slate-300 dark:border-slate-700 hover:border-blue-500 shadow-sm transition-all disabled:opacity-50"
              title="Unduh / Ekspor data patroli"
            >
              <Download className={`w-3.5 h-3.5 text-blue-600 dark:text-blue-400 ${exportingFormat ? 'animate-bounce' : ''}`} />
              <span>{exportingFormat ? `Mengunduh ${exportingFormat.toUpperCase()}...` : 'Ekspor'}</span>
              <ChevronDown className="w-3 h-3 text-slate-400" />
            </button>

            {showExportMenu && (
              <div className="absolute right-0 mt-1.5 w-60 rounded-xl bg-white dark:bg-[#0f1523] border border-slate-200 dark:border-slate-800 shadow-xl py-1.5 z-50 text-xs">
                <button
                  onClick={() => handleExport('daily_pdf')}
                  className="w-full px-3.5 py-2 text-left flex items-start gap-2.5 hover:bg-slate-50 dark:hover:bg-slate-800 transition-colors"
                >
                  <FileText className="w-4 h-4 text-rose-500 shrink-0 mt-0.5" />
                  <div>
                    <div className="font-semibold text-slate-800 dark:text-slate-200">Laporan Harian (PDF)</div>
                    <div className="text-[10px] text-slate-500">Eksekutif IPOLEKSOSBUDHANKAM & Segel HMAC</div>
                  </div>
                </button>
                <button
                  onClick={() => handleExport('daily_md')}
                  className="w-full px-3.5 py-2 text-left flex items-start gap-2.5 hover:bg-slate-50 dark:hover:bg-slate-800 transition-colors"
                >
                  <FileText className="w-4 h-4 text-blue-500 shrink-0 mt-0.5" />
                  <div>
                    <div className="font-semibold text-slate-800 dark:text-slate-200">Laporan Harian (Markdown)</div>
                    <div className="text-[10px] text-slate-500">Tabel 5W+1H & Rantai Bukti Forensik</div>
                  </div>
                </button>
                <div className="border-t border-slate-100 dark:border-slate-800 my-1" />
                <button
                  onClick={() => handleExport('pdf')}
                  className="w-full px-3.5 py-2 text-left flex items-start gap-2.5 hover:bg-slate-50 dark:hover:bg-slate-800 transition-colors"
                >
                  <FileText className="w-4 h-4 text-slate-500 shrink-0 mt-0.5" />
                  <div>
                    <div className="font-semibold text-slate-800 dark:text-slate-200">Dossier Lengkap (PDF)</div>
                    <div className="text-[10px] text-slate-500">Seluruh temuan terfilter & visual</div>
                  </div>
                </button>
                <button
                  onClick={() => handleExport('csv')}
                  className="w-full px-3.5 py-2 text-left flex items-start gap-2.5 hover:bg-slate-50 dark:hover:bg-slate-800 transition-colors"
                >
                  <FileDown className="w-4 h-4 text-emerald-500 shrink-0 mt-0.5" />
                  <div>
                    <div className="font-semibold text-slate-800 dark:text-slate-200">Metadata Temuan (CSV)</div>
                    <div className="text-[10px] text-slate-500">Rekap tabular data olahan analis</div>
                  </div>
                </button>
              </div>
            )}
          </div>
        </div>
      </div>

      {/* ── 1. BAR FILTER COMPACT & CLEAN ── */}
      <div className="cyber-card p-3 sm:p-4 rounded-xl border border-slate-200 dark:border-slate-800/80 space-y-2.5">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-1.5 text-xs font-semibold text-slate-700 dark:text-slate-300">
            <Filter className="w-3.5 h-3.5 text-blue-500" />
            <span>Filter Data</span>
          </div>
          {hasActiveFilters && (
            <button
              onClick={handleResetFilters}
              className="text-[11px] font-mono text-blue-600 dark:text-blue-400 hover:underline flex items-center gap-1 transition-colors"
            >
              <RotateCcw className="w-3 h-3" />
              Reset Filter
            </button>
          )}
        </div>

        <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-5 gap-2.5">
          <div>
            <label className="block text-[10px] font-mono font-semibold uppercase text-slate-500 dark:text-slate-400 mb-1">Dari Tanggal</label>
            <input
              type="date"
              value={dateFrom}
              onChange={(e) => setDateFrom(e.target.value)}
              className="w-full bg-white dark:bg-[#0c121e] border border-slate-200 dark:border-slate-800 rounded-lg px-2.5 py-1.5 text-xs text-slate-800 dark:text-slate-200 focus:outline-none focus:border-blue-500 focus:ring-1 focus:ring-blue-500 transition-colors"
            />
          </div>

          <div>
            <label className="block text-[10px] font-mono font-semibold uppercase text-slate-500 dark:text-slate-400 mb-1">Sampai Tanggal</label>
            <input
              type="date"
              value={dateTo}
              onChange={(e) => setDateTo(e.target.value)}
              className="w-full bg-white dark:bg-[#0c121e] border border-slate-200 dark:border-slate-800 rounded-lg px-2.5 py-1.5 text-xs text-slate-800 dark:text-slate-200 focus:outline-none focus:border-blue-500 focus:ring-1 focus:ring-blue-500 transition-colors"
            />
          </div>

          <div>
            <label className="block text-[10px] font-mono font-semibold uppercase text-slate-500 dark:text-slate-400 mb-1">Platform</label>
            <select
              value={selectedPlatform}
              onChange={(e) => setSelectedPlatform(e.target.value)}
              className="w-full bg-white dark:bg-[#0c121e] border border-slate-200 dark:border-slate-800 rounded-lg px-2.5 py-1.5 text-xs text-slate-800 dark:text-slate-200 focus:outline-none focus:border-blue-500 focus:ring-1 focus:ring-blue-500 transition-colors"
            >
              <option value="Semua">Semua Platform</option>
              <option value="Instagram">Instagram</option>
              <option value="YouTube">YouTube</option>
              <option value="TikTok">TikTok</option>
            </select>
          </div>

          <div>
            <label className="block text-[10px] font-mono font-semibold uppercase text-slate-500 dark:text-slate-400 mb-1">Kategori</label>
            <select
              value={selectedCategory}
              onChange={(e) => setSelectedCategory(e.target.value)}
              className="w-full bg-white dark:bg-[#0c121e] border border-slate-200 dark:border-slate-800 rounded-lg px-2.5 py-1.5 text-xs text-slate-800 dark:text-slate-200 focus:outline-none focus:border-blue-500 focus:ring-1 focus:ring-blue-500 transition-colors"
            >
              <option value="Semua">Semua Kategori</option>
              <option value="HOAKS">HOAKS</option>
              <option value="DI_LUAR_KONTEKS">DI LUAR KONTEKS</option>
              <option value="UJARAN_KEBENCIAN">UJARAN KEBENCIAN</option>
              <option value="PROVOKASI_SARA">PROVOKASI SARA</option>
            </select>
          </div>

          <div className="col-span-2 sm:col-span-1">
            <label className="block text-[10px] font-mono font-semibold uppercase text-slate-500 dark:text-slate-400 mb-1">Risiko</label>
            <select
              value={selectedRisk}
              onChange={(e) => setSelectedRisk(e.target.value)}
              className="w-full bg-white dark:bg-[#0c121e] border border-slate-200 dark:border-slate-800 rounded-lg px-2.5 py-1.5 text-xs text-slate-800 dark:text-slate-200 focus:outline-none focus:border-blue-500 focus:ring-1 focus:ring-blue-500 transition-colors"
            >
              <option value="Semua">Semua Risiko</option>
              <option value="TINGGI">TINGGI</option>
              <option value="SEDANG">SEDANG</option>
              <option value="RENDAH">RENDAH</option>
            </select>
          </div>
        </div>

        {/* Filter Chips */}
        {hasActiveFilters && (
          <div className="pt-2 border-t border-slate-200 dark:border-slate-800 flex flex-wrap items-center gap-1.5">
            {selectedPlatform !== 'Semua' && (
              <span className="inline-flex items-center gap-1 text-[11px] bg-blue-50 dark:bg-blue-500/10 text-blue-700 dark:text-blue-400 border border-blue-200 dark:border-blue-500/20 px-2 py-0.5 rounded-md font-medium">
                Platform: {selectedPlatform}
                <button onClick={() => setSelectedPlatform('Semua')}><XCircle className="w-3 h-3 hover:opacity-75" /></button>
              </span>
            )}
            {selectedCategory !== 'Semua' && (
              <span className="inline-flex items-center gap-1 text-[11px] bg-amber-50 dark:bg-amber-500/10 text-amber-700 dark:text-amber-400 border border-amber-200 dark:border-amber-500/20 px-2 py-0.5 rounded-md font-medium">
                Kategori: {selectedCategory}
                <button onClick={() => setSelectedCategory('Semua')}><XCircle className="w-3 h-3 hover:opacity-75" /></button>
              </span>
            )}
            {selectedRisk !== 'Semua' && (
              <span className="inline-flex items-center gap-1 text-[11px] bg-rose-50 dark:bg-rose-500/10 text-rose-700 dark:text-rose-400 border border-rose-200 dark:border-rose-500/20 px-2 py-0.5 rounded-md font-medium">
                Risiko: {selectedRisk}
                <button onClick={() => setSelectedRisk('Semua')}><XCircle className="w-3 h-3 hover:opacity-75" /></button>
              </span>
            )}
            {selectedStatus !== 'Semua' && (
              <span className="inline-flex items-center gap-1 text-[11px] bg-purple-50 dark:bg-purple-500/10 text-purple-700 dark:text-purple-400 border border-purple-200 dark:border-purple-500/20 px-2 py-0.5 rounded-md font-medium">
                Status: {selectedStatus}
                <button onClick={() => setSelectedStatus('Semua')}><XCircle className="w-3 h-3 hover:opacity-75" /></button>
              </span>
            )}
          </div>
        )}
      </div>

      {loading && !summary ? (
        <div className="space-y-4">
          <div className="grid grid-cols-2 lg:grid-cols-4 gap-3 sm:gap-4">
            {[1, 2, 3, 4].map((i) => (
              <div key={i} className="cyber-card p-4 sm:p-5 rounded-xl space-y-3">
                <div className="flex justify-between items-center">
                  <div className="h-3 w-20 rounded skeleton-shimmer" />
                  <div className="h-7 w-7 rounded-lg skeleton-shimmer" />
                </div>
                <div className="h-7 w-28 rounded skeleton-shimmer" />
              </div>
            ))}
          </div>
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-4 sm:gap-5">
            <div className="cyber-card p-5 rounded-xl space-y-4">
              <div className="h-4 w-40 rounded skeleton-shimmer" />
              <div className="h-48 w-full rounded-lg skeleton-shimmer" />
            </div>
            <div className="cyber-card p-5 rounded-xl space-y-4">
              <div className="h-4 w-40 rounded skeleton-shimmer" />
              <div className="h-48 w-full rounded-lg skeleton-shimmer" />
            </div>
          </div>
        </div>
      ) : error ? (
        <div className="p-8 cyber-card rounded-xl text-center">
          <AlertTriangle className="w-8 h-8 text-rose-500 mx-auto mb-2" />
          <p className="text-rose-600 dark:text-rose-300 text-sm font-semibold">{error}</p>
        </div>
      ) : activeTab === 'proposal' ? (
        /* ══════════════════════════════════════════════════════════════
           TAB 1: RINGKASAN METRIK
           ══════════════════════════════════════════════════════════════ */
        <div className="space-y-5">
          {/* 4 Kartu KPI Ringkasan */}
          <div className="grid grid-cols-2 lg:grid-cols-4 gap-3 sm:gap-4">
            <div
              className="cursor-pointer transition-transform hover:-translate-y-0.5"
              onClick={() => setSelectedStatus('Semua')}
            >
              <KPICard
                title="Total Laporan"
                value={summary?.total_laporan ?? 0}
                icon={<FileText className="w-4 h-4 text-blue-500" />}
                accentColor="blue"
              />
            </div>

            <div
              className="cursor-pointer transition-transform hover:-translate-y-0.5"
              onClick={() => setSelectedStatus('VALIDATED')}
            >
              <KPICard
                title="Temuan Tervalidasi"
                value={summary?.temuan_tervalidasi ?? 0}
                icon={<CheckCircle className="w-4 h-4 text-emerald-500" />}
                accentColor="emerald"
              />
            </div>

            <div
              className="cursor-pointer transition-transform hover:-translate-y-0.5"
              onClick={() => setSelectedStatus('MODIFIED')}
            >
              <KPICard
                title="Koreksi Analis"
                value={summary?.koreksi_analis ?? 0}
                icon={<Edit3 className="w-4 h-4 text-amber-500" />}
                accentColor="amber"
              />
            </div>

            <div
              className="cursor-pointer transition-transform hover:-translate-y-0.5"
              onClick={() => setSelectedStatus('REJECTED')}
            >
              <KPICard
                title="Bukan Pelanggaran"
                value={summary?.bukan_pelanggaran ?? 0}
                icon={<XCircle className="w-4 h-4 text-rose-500" />}
                accentColor="rose"
              />
            </div>
          </div>

          {/* Grafik Analitik Utama */}
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-4 sm:gap-5">
            {/* Visual 1 (Tren Waktu) */}
            <div className="cyber-card p-4 sm:p-5 rounded-xl space-y-2">
              <div className="flex items-center justify-between">
                <h3 className="text-sm font-bold text-slate-800 dark:text-white flex items-center gap-2">
                  <TrendingUp className="w-4 h-4 text-blue-500" />
                  Tren Aktivitas Temuan
                </h3>
              </div>
              <div className="pt-1">
                <DualLineChart
                  data={timeseries}
                  height={185}
                  onPointClick={(pt) => {
                    if (pt.timestamp) {
                      setDateFrom(pt.timestamp.slice(0, 10));
                      setDateTo(pt.timestamp.slice(0, 10));
                    }
                  }}
                />
              </div>
            </div>

            {/* Visual 2 (Per Platform) */}
            <div className="cyber-card p-4 sm:p-5 rounded-xl space-y-2">
              <div className="flex items-center justify-between">
                <h3 className="text-sm font-bold text-slate-800 dark:text-white flex items-center gap-2">
                  <Layers className="w-4 h-4 text-blue-500" />
                  Distribusi Platform
                </h3>
              </div>
              <div className="pt-1">
                <VerticalBarChart
                  items={platformBarItems}
                  height={185}
                  onBarClick={(item) => setSelectedPlatform(item.label)}
                />
              </div>
            </div>

            {/* Visual 3 (Per Kategori) */}
            <div className="cyber-card p-4 sm:p-5 rounded-xl space-y-2">
              <div className="flex items-center justify-between">
                <h3 className="text-sm font-bold text-slate-800 dark:text-white flex items-center gap-2">
                  <Tag className="w-4 h-4 text-amber-500" />
                  Kategori Isu
                </h3>
              </div>
              <div className="pt-1">
                <HorizontalBarList
                  items={categoryBarItems}
                  onBarClick={(item) => setSelectedCategory(item.key)}
                />
              </div>
            </div>

            {/* Visual 4 (Distribusi Risiko) */}
            <div className="cyber-card p-4 sm:p-5 rounded-xl space-y-2">
              <div className="flex items-center justify-between">
                <h3 className="text-sm font-bold text-slate-800 dark:text-white flex items-center gap-2">
                  <AlertTriangle className="w-4 h-4 text-rose-500" />
                  Tingkat Risiko
                </h3>
              </div>
              <div className="pt-1">
                <DonutChart
                  items={riskDonutItems}
                  centerLabel="Temuan"
                  centerValue={summary?.temuan_tervalidasi ?? 0}
                  onItemClick={(item) => setSelectedRisk(item.label)}
                />
              </div>
            </div>

            {/* Visual 5 (Topik Teratas) */}
            <div className="cyber-card p-4 sm:p-5 rounded-xl space-y-2">
              <div className="flex items-center justify-between">
                <h3 className="text-sm font-bold text-slate-800 dark:text-white flex items-center gap-2">
                  <TrendingUp className="w-4 h-4 text-blue-500" />
                  Topik Teratas
                </h3>
              </div>
              <div className="pt-1">
                <HorizontalBarList
                  items={topTopics.map((t) => ({
                    label: t.name,
                    count: t.count,
                    color: '#3b82f6',
                    subtitle: t.category,
                  }))}
                  onBarClick={() => {}}
                />
              </div>
            </div>

            {/* Visual 6 (Aktor Target Teratas) */}
            <div className="cyber-card p-4 sm:p-5 rounded-xl space-y-2">
              <div className="flex items-center justify-between">
                <h3 className="text-sm font-bold text-slate-800 dark:text-white flex items-center gap-2">
                  <UserCheck className="w-4 h-4 text-emerald-500" />
                  Aktor & Tokoh Sasaran
                </h3>
              </div>
              <div className="pt-1">
                <HorizontalBarList
                  items={topActors.map((a) => ({
                    label: a.name,
                    count: a.count,
                    color: '#10b981',
                    subtitle: a.category,
                  }))}
                  onBarClick={() => {}}
                />
              </div>
            </div>

            {/* Visual 7 (Sumber Konten Teratas) */}
            <div className="cyber-card p-4 sm:p-5 rounded-xl space-y-2">
              <div className="flex items-center justify-between">
                <h3 className="text-sm font-bold text-slate-800 dark:text-white flex items-center gap-2">
                  <Radio className="w-4 h-4 text-violet-500" />
                  Kanal Sumber Konten
                </h3>
              </div>
              <div className="pt-1">
                <HorizontalBarList
                  items={topSources.map((s) => ({
                    label: s.name,
                    count: s.count,
                    color: '#a855f7',
                    subtitle: s.category,
                  }))}
                  onBarClick={() => {}}
                />
              </div>
            </div>

            {/* Visual 8 (Kesepakatan AI vs Analis) */}
            <div className="cyber-card p-4 sm:p-5 rounded-xl space-y-2">
              <div className="flex items-center justify-between">
                <h3 className="text-sm font-bold text-slate-800 dark:text-white flex items-center gap-2">
                  <CheckCircle className="w-4 h-4 text-emerald-500" />
                  Akurasi AI vs Analis
                </h3>
              </div>
              <div className="pt-1">
                <VerticalBarChart
                  items={agreementBarItems}
                  height={185}
                  onBarClick={(item) => setSelectedStatus(item.key || 'Semua')}
                />
              </div>
            </div>
          </div>

          {/* Tabel Laporan Hasil Filter */}
          <div className="cyber-card rounded-xl p-4 sm:p-5 space-y-3">
            <div className="flex items-center justify-between">
              <h3 className="text-sm font-bold text-slate-800 dark:text-white flex items-center gap-2">
                <FileText className="w-4 h-4 text-blue-500" />
                Daftar Temuan ({reports.length})
              </h3>
              <Link
                to="/contents"
                className="text-xs font-semibold text-blue-600 dark:text-blue-400 hover:underline flex items-center gap-1"
              >
                <span>Lihat Semua</span>
                <ArrowRight className="w-3.5 h-3.5" />
              </Link>
            </div>

            {reports.length === 0 ? (
              <div className="text-center py-10 text-slate-400 dark:text-slate-500 text-xs font-mono">
                Tidak ada laporan yang sesuai dengan kriteria filter saat ini.
              </div>
            ) : (
              <div className="overflow-x-auto">
                <table className="w-full text-left text-xs">
                  <thead className="bg-slate-100 dark:bg-slate-900/90 text-slate-600 dark:text-slate-400 uppercase text-[10px] font-semibold tracking-wider border-b border-slate-200 dark:border-slate-800">
                    <tr>
                      <th className="py-2.5 px-3">Tiket & Waktu</th>
                      <th className="py-2.5 px-3">Platform & Akun</th>
                      <th className="py-2.5 px-3">Kategori</th>
                      <th className="py-2.5 px-3">Risiko</th>
                      <th className="py-2.5 px-3">Topik / Sasaran</th>
                      <th className="py-2.5 px-3">Status</th>
                      <th className="py-2.5 px-3 text-right">Aksi</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-slate-100 dark:divide-slate-800/60 font-mono">
                    {reports.map((r: any) => {
                      const statusColor =
                        r.status === 'VALIDATED'
                          ? 'text-emerald-700 bg-emerald-50 border-emerald-200 dark:text-emerald-400 dark:bg-emerald-950/60 dark:border-emerald-800/40'
                          : r.status === 'MODIFIED'
                          ? 'text-amber-700 bg-amber-50 border-amber-200 dark:text-amber-400 dark:bg-amber-950/60 dark:border-amber-800/40'
                          : r.status === 'REJECTED'
                          ? 'text-rose-700 bg-rose-50 border-rose-200 dark:text-rose-400 dark:bg-rose-950/60 dark:border-rose-800/40'
                          : 'text-blue-700 bg-blue-50 border-blue-200 dark:text-blue-400 dark:bg-blue-950/60 dark:border-blue-800/40';

                      const riskColor =
                        r.final_risk === 'TINGGI'
                          ? 'text-rose-600 dark:text-rose-400'
                          : r.final_risk === 'SEDANG'
                          ? 'text-amber-600 dark:text-amber-400'
                          : r.final_risk === 'RENDAH'
                          ? 'text-emerald-600 dark:text-emerald-400'
                          : 'text-slate-500';

                      return (
                        <tr key={r.report_id} className="hover:bg-slate-50 dark:hover:bg-slate-800/40 transition-colors">
                          <td className="py-2.5 px-3">
                            <div className="font-bold text-slate-800 dark:text-slate-200">{r.ticket_number}</div>
                            <div className="text-[10px] text-slate-400">
                              {r.created_at ? r.created_at.slice(0, 16).replace('T', ' ') : '-'}
                            </div>
                          </td>
                          <td className="py-2.5 px-3">
                            <span className="text-[11px] font-bold text-blue-600 dark:text-blue-300 uppercase">{r.platform}</span>
                            <div className="text-[10px] text-slate-500 dark:text-slate-400">@{r.account?.username || 'anonim'}</div>
                          </td>
                          <td className="py-2.5 px-3">
                            <span className="font-sans font-semibold text-slate-700 dark:text-slate-200">
                              {r.final_label || r.ai_predicted_label || '-'}
                            </span>
                          </td>
                          <td className="py-2.5 px-3">
                            <span className={`font-bold ${riskColor}`}>{r.final_risk || 'NIHIL'}</span>
                          </td>
                          <td className="py-2.5 px-3 font-sans">
                            <div className="text-slate-700 dark:text-slate-300 text-[11px] font-medium">{r.topic || '-'}</div>
                            {r.actors && r.actors.length > 0 && (
                              <div className="text-[10px] text-slate-400">Sasaran: {r.actors.join(', ')}</div>
                            )}
                          </td>
                          <td className="py-2.5 px-3">
                            <span className={`text-[10px] px-2 py-0.5 rounded border font-semibold ${statusColor}`}>
                              {r.status}
                            </span>
                          </td>
                          <td className="py-2.5 px-3 text-right">
                            {r.url ? (
                              <a
                                href={r.url}
                                target="_blank"
                                rel="noreferrer"
                                className="inline-flex items-center gap-1 text-[11px] text-blue-600 dark:text-blue-400 hover:underline"
                              >
                                <span>Konten</span>
                                <ExternalLink className="w-3 h-3" />
                              </a>
                            ) : (
                              <span className="text-slate-400">-</span>
                            )}
                          </td>
                        </tr>
                      );
                    })}
                  </tbody>
                </table>
              </div>
            )}
          </div>
        </div>
      ) : (
        /* ══════════════════════════════════════════════════════════════
           TAB 2: RADAR & SENTIMEN
           ══════════════════════════════════════════════════════════════ */
        <div className="space-y-5">
          <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
            <div className="cyber-card p-4 rounded-xl">
              <span className="text-xs text-slate-500">Isu Aktif Terdeteksi</span>
              <div className="text-2xl font-bold font-mono text-slate-900 dark:text-white mt-1">
                {trendingStats?.active_issues_count || 0}
              </div>
            </div>
            <div className="cyber-card p-4 rounded-xl">
              <span className="text-xs text-slate-500">Menunggu Validasi</span>
              <div className="text-2xl font-bold font-mono text-amber-500 mt-1">
                {trendingStats?.pending_validations || 0}
              </div>
            </div>
            <div className="cyber-card p-4 rounded-xl">
              <span className="text-xs text-slate-500">Konten Risiko Tinggi</span>
              <div className="text-2xl font-bold font-mono text-rose-500 mt-1">
                {trendingStats?.high_risk_contents || 0}
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};
