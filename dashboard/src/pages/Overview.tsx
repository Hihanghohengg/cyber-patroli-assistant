import React, { useEffect, useState, useMemo, useRef } from 'react';
import { Link, useNavigate } from 'react-router-dom';
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
  const navigate = useNavigate();

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

  const handleExport = async (fmt: 'pdf' | 'csv' | 'daily_md' | 'daily_pdf') => {
    setShowExportMenu(false);
    try {
      setExportingFormat(fmt);
      if (fmt === 'daily_pdf') {
        await apiClient.reports.dailyExportBlob(undefined, 'pdf');
      } else if (fmt === 'daily_md') {
        await apiClient.reports.dailyExportBlob(undefined, 'md');
      } else {
        await apiClient.v1.exportBlob(fmt, {
          platform: selectedPlatform !== 'Semua' ? selectedPlatform.toLowerCase() : undefined,
          category: selectedCategory !== 'Semua' ? selectedCategory : undefined,
          risk_level: selectedRisk !== 'Semua' ? selectedRisk : undefined,
          status: selectedStatus !== 'Semua' ? selectedStatus : undefined,
        });
      }
    } catch (err) {
      console.error('Failed to export:', err);
    } finally {
      setExportingFormat(null);
    }
  };

  // Visual 2: Vertical Bar Distribusi Platform
  const platformBarItems: VerticalBarItem[] = useMemo(() => {
    if (!summary?.distribusi_platform) return [];
    const colorMap: Record<string, string> = {
      instagram: '#e1306c',
      youtube: '#ef4444',
      tiktok: '#06b6d4',
      threads: '#8b5cf6',
      web: '#3b82f6',
    };
    return Object.entries(summary.distribusi_platform).map(([plat, cnt]) => ({
      label: plat.charAt(0).toUpperCase() + plat.slice(1),
      count: Number(cnt) || 0,
      color: colorMap[plat.toLowerCase()] || '#3b82f6',
      key: plat,
    }));
  }, [summary]);

  // Visual 3: Horizontal Bar Distribusi Kategori
  const categoryBarItems = useMemo(() => {
    if (!summary?.distribusi_kategori) return [];
    const colorMap: Record<string, string> = {
      HOAKS: '#ef4444',
      DI_LUAR_KONTEKS: '#f59e0b',
      UJARAN_KEBENCIAN: '#a855f7',
      PROVOKASI_SARA: '#ec4899',
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
      TINGGI: '#f43f5e',
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
      {/* ── Page Header & Single Export Dropdown ── */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 border-b border-slate-200 dark:border-white/[0.06] pb-3">
        <div>
          <h1 className="text-lg font-semibold tracking-tight text-slate-900 dark:text-white flex items-center gap-2">
            Ringkasan Operasi
          </h1>
        </div>

        {/* Tab Selector & Sleek Download Dropdown Button */}
        <div className="flex items-center gap-2.5">
          <div className="bg-slate-100 dark:bg-white/[0.04] p-0.5 rounded-lg border border-slate-200 dark:border-white/[0.06] flex items-center text-xs">
            <button
              onClick={() => setActiveTab('proposal')}
              className={`px-3 py-1 rounded-md font-medium transition-colors flex items-center gap-1.5 ${
                activeTab === 'proposal'
                  ? 'bg-white dark:bg-white/[0.08] text-slate-900 dark:text-white shadow-sm font-semibold'
                  : 'text-slate-600 dark:text-slate-400 hover:text-slate-900 dark:hover:text-slate-200'
              }`}
            >
              <BarChart2 className="w-3.5 h-3.5" />
              <span>Metrik Operasi</span>
            </button>
            <button
              onClick={() => setActiveTab('intel')}
              className={`px-3 py-1 rounded-md font-medium transition-colors flex items-center gap-1.5 ${
                activeTab === 'intel'
                  ? 'bg-white dark:bg-white/[0.08] text-slate-900 dark:text-white shadow-sm font-semibold'
                  : 'text-slate-600 dark:text-slate-400 hover:text-slate-900 dark:hover:text-slate-200'
              }`}
            >
              <Flame className="w-3.5 h-3.5" />
              <span>Radar & Sasaran</span>
            </button>
          </div>

          {/* Export Dropdown Button */}
          <div className="relative" ref={exportMenuRef}>
            <button
              onClick={() => setShowExportMenu(!showExportMenu)}
              disabled={exportingFormat !== null}
              className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-semibold bg-white dark:bg-[#12151E] text-slate-800 dark:text-slate-200 border border-slate-200 dark:border-white/[0.08] hover:border-blue-500 shadow-sm transition-colors disabled:opacity-50"
              title="Ekspor data patroli"
            >
              <Download className={`w-3.5 h-3.5 text-blue-500 ${exportingFormat ? 'animate-bounce' : ''}`} />
              <span>{exportingFormat ? `Mengunduh...` : 'Ekspor'}</span>
              <ChevronDown className="w-3 h-3 text-slate-400" />
            </button>

            {showExportMenu && (
              <div className="absolute right-0 mt-1.5 w-60 rounded-xl bg-white dark:bg-[#0F1117] border border-slate-200 dark:border-white/[0.08] shadow-2xl py-1.5 z-50 text-xs">
                <button
                  onClick={() => handleExport('daily_pdf')}
                  className="w-full px-3.5 py-2 text-left flex items-start gap-2.5 hover:bg-slate-50 dark:hover:bg-white/[0.04] transition-colors"
                >
                  <FileText className="w-4 h-4 text-rose-500 shrink-0 mt-0.5" />
                  <div>
                    <div className="font-semibold text-slate-800 dark:text-slate-200">Laporan Harian (PDF)</div>
                    <div className="text-[10px] text-slate-500 font-mono">Dossier Resmi & Segel HMAC</div>
                  </div>
                </button>
                <button
                  onClick={() => handleExport('daily_md')}
                  className="w-full px-3.5 py-2 text-left flex items-start gap-2.5 hover:bg-slate-50 dark:hover:bg-white/[0.04] transition-colors"
                >
                  <FileText className="w-4 h-4 text-blue-500 shrink-0 mt-0.5" />
                  <div>
                    <div className="font-semibold text-slate-800 dark:text-slate-200">Laporan Harian (Markdown)</div>
                    <div className="text-[10px] text-slate-500 font-mono">Matriks 5W+1H & Rantai Bukti</div>
                  </div>
                </button>
                <div className="border-t border-slate-100 dark:border-white/[0.06] my-1" />
                <button
                  onClick={() => handleExport('pdf')}
                  className="w-full px-3.5 py-2 text-left flex items-start gap-2.5 hover:bg-slate-50 dark:hover:bg-white/[0.04] transition-colors"
                >
                  <FileText className="w-4 h-4 text-slate-400 shrink-0 mt-0.5" />
                  <div>
                    <div className="font-semibold text-slate-800 dark:text-slate-200">Dossier Lengkap (PDF)</div>
                    <div className="text-[10px] text-slate-500 font-mono">Seluruh temuan terfilter</div>
                  </div>
                </button>
                <button
                  onClick={() => handleExport('csv')}
                  className="w-full px-3.5 py-2 text-left flex items-start gap-2.5 hover:bg-slate-50 dark:hover:bg-white/[0.04] transition-colors"
                >
                  <FileDown className="w-4 h-4 text-emerald-500 shrink-0 mt-0.5" />
                  <div>
                    <div className="font-semibold text-slate-800 dark:text-slate-200">Metadata Temuan (CSV)</div>
                    <div className="text-[10px] text-slate-500 font-mono">Rekap tabular data olahan</div>
                  </div>
                </button>
              </div>
            )}
          </div>
        </div>
      </div>

      {/* ── 1. BAR FILTER COMPACT & CLEAN ── */}
      <div className="cyber-card p-3 rounded-xl border border-slate-200 dark:border-white/[0.06] space-y-2">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-1.5 text-xs font-semibold text-slate-700 dark:text-slate-300">
            <Filter className="w-3.5 h-3.5 text-blue-500" />
            <span>Filter Operasi</span>
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
              className="w-full bg-white dark:bg-[#0A0D14] border border-slate-200 dark:border-white/[0.08] rounded-lg px-2.5 py-1 text-xs text-slate-800 dark:text-slate-200 focus:outline-none focus:border-blue-500 font-mono transition-colors"
            />
          </div>

          <div>
            <label className="block text-[10px] font-mono font-semibold uppercase text-slate-500 dark:text-slate-400 mb-1">Sampai Tanggal</label>
            <input
              type="date"
              value={dateTo}
              onChange={(e) => setDateTo(e.target.value)}
              className="w-full bg-white dark:bg-[#0A0D14] border border-slate-200 dark:border-white/[0.08] rounded-lg px-2.5 py-1 text-xs text-slate-800 dark:text-slate-200 focus:outline-none focus:border-blue-500 font-mono transition-colors"
            />
          </div>

          <div>
            <label className="block text-[10px] font-mono font-semibold uppercase text-slate-500 dark:text-slate-400 mb-1">Platform</label>
            <select
              value={selectedPlatform}
              onChange={(e) => setSelectedPlatform(e.target.value)}
              className="w-full bg-white dark:bg-[#0A0D14] border border-slate-200 dark:border-white/[0.08] rounded-lg px-2.5 py-1 text-xs text-slate-800 dark:text-slate-200 focus:outline-none focus:border-blue-500 transition-colors"
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
              className="w-full bg-white dark:bg-[#0A0D14] border border-slate-200 dark:border-white/[0.08] rounded-lg px-2.5 py-1 text-xs text-slate-800 dark:text-slate-200 focus:outline-none focus:border-blue-500 transition-colors"
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
              className="w-full bg-white dark:bg-[#0A0D14] border border-slate-200 dark:border-white/[0.08] rounded-lg px-2.5 py-1 text-xs text-slate-800 dark:text-slate-200 focus:outline-none focus:border-blue-500 transition-colors"
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
          <div className="pt-2 border-t border-slate-200 dark:border-white/[0.06] flex flex-wrap items-center gap-1.5">
            {selectedPlatform !== 'Semua' && (
              <span className="inline-flex items-center gap-1 text-[11px] bg-blue-500/10 text-blue-600 dark:text-blue-400 border border-blue-500/20 px-2 py-0.5 rounded font-mono font-medium">
                Platform: {selectedPlatform}
                <button onClick={() => setSelectedPlatform('Semua')}><XCircle className="w-3 h-3 hover:opacity-75" /></button>
              </span>
            )}
            {selectedCategory !== 'Semua' && (
              <span className="inline-flex items-center gap-1 text-[11px] bg-amber-500/10 text-amber-600 dark:text-amber-400 border border-amber-500/20 px-2 py-0.5 rounded font-mono font-medium">
                Kategori: {selectedCategory}
                <button onClick={() => setSelectedCategory('Semua')}><XCircle className="w-3 h-3 hover:opacity-75" /></button>
              </span>
            )}
            {selectedRisk !== 'Semua' && (
              <span className="inline-flex items-center gap-1 text-[11px] bg-rose-500/10 text-rose-600 dark:text-rose-400 border border-rose-500/20 px-2 py-0.5 rounded font-mono font-medium">
                Risiko: {selectedRisk}
                <button onClick={() => setSelectedRisk('Semua')}><XCircle className="w-3 h-3 hover:opacity-75" /></button>
              </span>
            )}
          </div>
        )}
      </div>

      {loading && !summary ? (
        <div className="space-y-4">
          <div className="grid grid-cols-2 lg:grid-cols-4 gap-3">
            {[1, 2, 3, 4].map((i) => (
              <div key={i} className="cyber-card p-4 rounded-xl space-y-2">
                <div className="h-3 w-20 rounded skeleton-shimmer" />
                <div className="h-7 w-24 rounded skeleton-shimmer" />
              </div>
            ))}
          </div>
          <div className="grid grid-cols-1 lg:grid-cols-12 gap-4">
            <div className="lg:col-span-8 cyber-card p-5 rounded-xl space-y-4">
              <div className="h-4 w-40 rounded skeleton-shimmer" />
              <div className="h-48 w-full rounded-lg skeleton-shimmer" />
            </div>
            <div className="lg:col-span-4 cyber-card p-5 rounded-xl space-y-4">
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
           TAB 1: METRIK OPERASI (ASYMMETRIC BENTO COMMAND CENTER)
           ══════════════════════════════════════════════════════════════ */
        <div className="space-y-5">
          {/* Baris 1: 4 KPI Strip Kompak */}
          <div className="grid grid-cols-2 lg:grid-cols-4 gap-3">
            <KPICard
              title="Total Temuan"
              value={summary?.total_laporan ?? 0}
              subtitle="Seluruh laporan tersimpan"
              icon={<FileText className="w-4 h-4 text-blue-500" />}
              onClick={() => setSelectedStatus('Semua')}
            />

            <KPICard
              title="Temuan Tervalidasi"
              value={summary?.temuan_tervalidasi ?? 0}
              subtitle="Verifikasi analis resmi"
              icon={<CheckCircle className="w-4 h-4 text-emerald-500" />}
              trend={{ value: 'HITL OK', isPositive: true }}
              onClick={() => setSelectedStatus('VALIDATED')}
            />

            <KPICard
              title="Koreksi Analis"
              value={summary?.koreksi_analis ?? 0}
              subtitle="Label / risiko dimodifikasi"
              icon={<Edit3 className="w-4 h-4 text-amber-500" />}
              onClick={() => setSelectedStatus('MODIFIED')}
            />

            <KPICard
              title="Bukan Pelanggaran"
              value={summary?.bukan_pelanggaran ?? 0}
              subtitle="Ditolak / konten aman"
              icon={<AlertTriangle className="w-4 h-4 text-rose-500" />}
              onClick={() => setSelectedStatus('REJECTED')}
            />
          </div>

          {/* Baris 2: Grid Asimetris 8:4 */}
          <div className="grid grid-cols-1 lg:grid-cols-12 gap-4">
            {/* Kiri (8 kolom): Tren Aktivitas Temuan (Line Chart) */}
            <div className="lg:col-span-8 cyber-card p-4 sm:p-5 rounded-xl space-y-3">
              <div className="flex items-center justify-between">
                <h3 className="text-xs font-bold text-slate-800 dark:text-slate-100 flex items-center gap-2 uppercase tracking-wider font-mono">
                  <TrendingUp className="w-4 h-4 text-blue-500" />
                  Tren Aktivitas Temuan
                </h3>
                <span className="text-[10px] font-mono text-slate-400">Harian</span>
              </div>
              <div className="pt-1">
                <DualLineChart
                  data={timeseries}
                  height={190}
                  onPointClick={(pt) => {
                    if (pt.timestamp) {
                      setDateFrom(pt.timestamp.slice(0, 10));
                      setDateTo(pt.timestamp.slice(0, 10));
                    }
                  }}
                />
              </div>
            </div>

            {/* Kanan (4 kolom): Distribusi Risiko (Donut) */}
            <div className="lg:col-span-4 cyber-card p-4 sm:p-5 rounded-xl space-y-3 flex flex-col justify-between">
              <div>
                <div className="flex items-center justify-between mb-2">
                  <h3 className="text-xs font-bold text-slate-800 dark:text-slate-100 flex items-center gap-2 uppercase tracking-wider font-mono">
                    <AlertTriangle className="w-4 h-4 text-rose-500" />
                    Tingkat Risiko
                  </h3>
                  <span className="text-[10px] font-mono text-slate-400">Proporsi</span>
                </div>
                <div className="pt-2 flex items-center justify-center">
                  <DonutChart
                    items={riskDonutItems}
                    centerLabel="Tervalidasi"
                    centerValue={summary?.temuan_tervalidasi ?? 0}
                    onItemClick={(item) => setSelectedRisk(item.label)}
                  />
                </div>
              </div>

              <div className="pt-3 border-t border-slate-100 dark:border-white/[0.06] flex items-center justify-between text-[10.5px] font-mono text-slate-400">
                <span>Klik irisan untuk filter</span>
                <span className="text-emerald-500 font-semibold">Tervalidasi: {summary?.temuan_tervalidasi ?? 0}</span>
              </div>
            </div>
          </div>

          {/* Baris Tambahan: Distribusi Platform & Kategori */}
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
            {/* Visual: Distribusi Platform */}
            <div className="cyber-card p-4 sm:p-5 rounded-xl space-y-2">
              <div className="flex items-center justify-between">
                <h3 className="text-xs font-bold text-slate-800 dark:text-slate-100 flex items-center gap-2 uppercase tracking-wider font-mono">
                  <Layers className="w-4 h-4 text-blue-500" />
                  Kanal Platform
                </h3>
              </div>
              <div className="pt-1">
                <VerticalBarChart
                  items={platformBarItems}
                  height={170}
                  onBarClick={(item) => setSelectedPlatform(item.label)}
                />
              </div>
            </div>

            {/* Visual: Kategori Isu */}
            <div className="cyber-card p-4 sm:p-5 rounded-xl space-y-2">
              <div className="flex items-center justify-between">
                <h3 className="text-xs font-bold text-slate-800 dark:text-slate-100 flex items-center gap-2 uppercase tracking-wider font-mono">
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
          </div>

          {/* Baris 3: Tabel Temuan Prioritas Terbaru (Linear Style) */}
          <div className="cyber-card rounded-xl p-4 sm:p-5 space-y-3">
            <div className="flex items-center justify-between border-b border-slate-100 dark:border-white/[0.06] pb-3">
              <div className="flex items-center gap-2">
                <FileText className="w-4 h-4 text-blue-500" />
                <h3 className="text-xs font-bold text-slate-800 dark:text-slate-100 uppercase tracking-wider font-mono">
                  Temuan Prioritas Terbaru ({reports.length})
                </h3>
              </div>
              <Link
                to="/contents"
                className="text-xs font-semibold text-blue-600 dark:text-blue-400 hover:underline flex items-center gap-1 font-mono"
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
                  <thead className="bg-slate-50 dark:bg-[#0A0D14] text-slate-500 dark:text-slate-400 uppercase text-[10px] font-semibold tracking-wider border-b border-slate-200 dark:border-white/[0.06]">
                    <tr>
                      <th className="py-2.5 px-3">Tiket & Waktu</th>
                      <th className="py-2.5 px-3">Kanal</th>
                      <th className="py-2.5 px-3">Ringkasan Isu</th>
                      <th className="py-2.5 px-3">Kategori</th>
                      <th className="py-2.5 px-3">Risiko</th>
                      <th className="py-2.5 px-3">Status</th>
                      <th className="py-2.5 px-3 text-right">Aksi</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-slate-100 dark:divide-white/[0.04] font-mono">
                    {reports.slice(0, 8).map((r: any) => {
                      const isHighRisk = r.final_risk === 'TINGGI';
                      const isMediumRisk = r.final_risk === 'SEDANG';
                      const contentId = r.content_id || r.ticket_number;

                      return (
                        <tr
                          key={r.report_id}
                          onClick={() => navigate(`/contents/${contentId}`)}
                          className="hover:bg-slate-50 dark:hover:bg-white/[0.02] cursor-pointer transition-colors"
                        >
                          <td className="py-2.5 px-3">
                            <div className="font-bold text-slate-800 dark:text-slate-200">{r.ticket_number}</div>
                            <div className="text-[10px] text-slate-400 font-mono">
                              {r.created_at ? r.created_at.slice(0, 16).replace('T', ' ') : '-'}
                            </div>
                          </td>
                          <td className="py-2.5 px-3">
                            <span className="text-[10px] font-bold text-blue-600 dark:text-blue-400 uppercase px-1.5 py-0.5 rounded bg-blue-500/10 border border-blue-500/20">
                              {r.platform}
                            </span>
                            <div className="text-[10px] text-slate-500 dark:text-slate-400 mt-0.5 truncate max-w-[90px]">
                              @{r.account?.username || 'anonim'}
                            </div>
                          </td>
                          <td className="py-2.5 px-3 font-sans">
                            <div className="text-slate-800 dark:text-slate-200 text-xs font-medium line-clamp-1 max-w-[280px]">
                              {r.topic || r.summary_text || r.final_label || 'Temuan Patroli'}
                            </div>
                            {r.actors && r.actors.length > 0 && (
                              <div className="text-[10px] text-slate-400 font-mono line-clamp-1">
                                Tokoh: {r.actors.slice(0, 2).join(', ')}
                              </div>
                            )}
                          </td>
                          <td className="py-2.5 px-3 font-sans">
                            <span className="text-xs font-semibold text-slate-700 dark:text-slate-300">
                              {r.final_label || r.ai_predicted_label || '-'}
                            </span>
                          </td>
                          <td className="py-2.5 px-3">
                            <span
                              className={`text-[10px] font-bold px-1.5 py-0.5 rounded border ${
                                isHighRisk
                                  ? 'bg-rose-500/10 text-rose-500 border-rose-500/20'
                                  : isMediumRisk
                                  ? 'bg-amber-500/10 text-amber-500 border-amber-500/20'
                                  : 'bg-emerald-500/10 text-emerald-500 border-emerald-500/20'
                              }`}
                            >
                              {r.final_risk || 'NIHIL'}
                            </span>
                          </td>
                          <td className="py-2.5 px-3">
                            <span
                              className={`text-[10px] px-1.5 py-0.5 rounded font-mono font-medium ${
                                r.status === 'VALIDATED'
                                  ? 'text-emerald-400 bg-emerald-500/10 border border-emerald-500/20'
                                  : r.status === 'MODIFIED'
                                  ? 'text-amber-400 bg-amber-500/10 border border-amber-500/20'
                                  : r.status === 'REJECTED'
                                  ? 'text-rose-400 bg-rose-500/10 border border-rose-500/20'
                                  : 'text-slate-400 bg-slate-500/10 border border-slate-500/20'
                              }`}
                            >
                              {r.status}
                            </span>
                          </td>
                          <td className="py-2.5 px-3 text-right">
                            <span className="text-slate-400 hover:text-blue-400 font-mono text-[11px] inline-flex items-center gap-1">
                              Buka <ArrowRight className="w-3 h-3" />
                            </span>
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
           TAB 2: RADAR & SASARAN
           ══════════════════════════════════════════════════════════════ */
        <div className="space-y-5">
          <div className="grid grid-cols-1 md:grid-cols-3 gap-3">
            <div className="cyber-card p-4 rounded-xl">
              <span className="text-[11px] font-mono text-slate-400 uppercase tracking-wider">Isu Aktif</span>
              <div className="text-2xl font-bold font-mono text-slate-900 dark:text-white mt-1">
                {trendingStats?.active_issues_count || 0}
              </div>
            </div>
            <div className="cyber-card p-4 rounded-xl">
              <span className="text-[11px] font-mono text-slate-400 uppercase tracking-wider">Menunggu Validasi</span>
              <div className="text-2xl font-bold font-mono text-amber-500 mt-1">
                {trendingStats?.pending_validations || 0}
              </div>
            </div>
            <div className="cyber-card p-4 rounded-xl">
              <span className="text-[11px] font-mono text-slate-400 uppercase tracking-wider">Konten Risiko Tinggi</span>
              <div className="text-2xl font-bold font-mono text-rose-500 mt-1">
                {trendingStats?.high_risk_contents || 0}
              </div>
            </div>
          </div>

          <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
            {/* Topik Teratas */}
            <div className="cyber-card p-4 sm:p-5 rounded-xl space-y-2">
              <h3 className="text-xs font-bold text-slate-800 dark:text-slate-100 flex items-center gap-2 uppercase tracking-wider font-mono">
                <TrendingUp className="w-4 h-4 text-blue-500" />
                Topik Teratas
              </h3>
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

            {/* Aktor Sasaran Teratas */}
            <div className="cyber-card p-4 sm:p-5 rounded-xl space-y-2">
              <h3 className="text-xs font-bold text-slate-800 dark:text-slate-100 flex items-center gap-2 uppercase tracking-wider font-mono">
                <UserCheck className="w-4 h-4 text-emerald-500" />
                Tokoh & Entitas Sasaran
              </h3>
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
          </div>
        </div>
      )}
    </div>
  );
};
