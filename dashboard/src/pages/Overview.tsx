import React, { useEffect, useState, useMemo } from 'react';
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
  UserCheck,
  ShieldCheck,
  FileDown,
  Download,
  Filter,
  RotateCcw,
  Layers,
  Tag,
  XCircle,
  X,
  RefreshCw,
} from 'lucide-react';

export const OverviewPage: React.FC = () => {
  const { user } = useAuth();
  const navigate = useNavigate();

  // Filter Bar State
  const [dateFrom, setDateFrom] = useState<string>('');
  const [dateTo, setDateTo] = useState<string>('');
  const [selectedPlatform, setSelectedPlatform] = useState<string>('Semua');
  const [selectedCategory, setSelectedCategory] = useState<string>('Semua');
  const [selectedRisk, setSelectedRisk] = useState<string>('Semua');
  const [selectedStatus, setSelectedStatus] = useState<string>('Semua');

  // Analytical PDF Modal State
  const [showPdfModal, setShowPdfModal] = useState<boolean>(false);
  const [pdfPeriod, setPdfPeriod] = useState<'daily' | 'weekly' | 'custom'>('daily');
  const [pdfDate, setPdfDate] = useState<string>(new Date().toISOString().slice(0, 10));
  const [pdfStartDate, setPdfStartDate] = useState<string>('');
  const [pdfEndDate, setPdfEndDate] = useState<string>('');
  const [pdfCategory, setPdfCategory] = useState<string>('Semua Kategori');
  const [isGeneratingPdf, setIsGeneratingPdf] = useState<boolean>(false);
  const [pdfError, setPdfError] = useState<string | null>(null);

  // Data states
  const [summary, setSummary] = useState<any>(null);
  const [timeseries, setTimeseries] = useState<DualLinePoint[]>([]);
  const [topTopics, setTopTopics] = useState<any[]>([]);
  const [topActors, setTopActors] = useState<any[]>([]);
  const [reports, setReports] = useState<any[]>([]);
  const [trendingStats, setTrendingStats] = useState<any>(null);

  const [loading, setLoading] = useState<boolean>(true);
  const [error, setError] = useState<string | null>(null);

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

      const [sumRes, tsRes, topTRes, topARes, repRes, trendRes] = await Promise.all([
        apiClient.v1.getSummary(filterParams).catch(() => null),
        apiClient.v1.getTimeseries({
          date_from: dateFrom || undefined,
          date_to: dateTo || undefined,
          interval: 'day',
        }).catch(() => ({ series: [] })),
        apiClient.v1.getTop('topics', 8).catch(() => ({ items: [] })),
        apiClient.v1.getTop('actors', 8).catch(() => ({ items: [] })),
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
    Boolean(dateFrom) ||
    Boolean(dateTo) ||
    selectedPlatform !== 'Semua' ||
    selectedCategory !== 'Semua' ||
    selectedRisk !== 'Semua' ||
    selectedStatus !== 'Semua';

  const handleDownloadAnalyticalPdf = async () => {
    try {
      setIsGeneratingPdf(true);
      setPdfError(null);
      await apiClient.reports.downloadAnalyticalPdf({
        period: pdfPeriod,
        date: pdfPeriod === 'daily' ? (pdfDate || undefined) : undefined,
        start_date: pdfPeriod === 'custom' ? (pdfStartDate || undefined) : undefined,
        end_date: pdfPeriod === 'custom' ? (pdfEndDate || undefined) : undefined,
        category: pdfCategory !== 'Semua Kategori' ? pdfCategory : undefined,
      });
      setShowPdfModal(false);
    } catch (err: any) {
      console.error('Failed to generate PDF:', err);
      setPdfError(err?.message || 'Gagal membuat laporan PDF. Silakan coba lagi.');
    } finally {
      setIsGeneratingPdf(false);
    }
  };

  // Visual: Vertical Bar Distribusi Platform
  const platformBarItems: VerticalBarItem[] = useMemo(() => {
    if (!summary?.distribusi_platform) return [];
    const colorMap: Record<string, string> = {
      instagram: '#e1306c',
      youtube: '#ef4444',
      tiktok: '#06b6d4',
      threads: '#8b5cf6',
      twitter: '#1d9bf0',
      x: '#1d9bf0',
      facebook: '#1877f2',
      web: '#3b82f6',
    };
    return Object.entries(summary.distribusi_platform).map(([plat, cnt]) => {
      const pLower = plat.toLowerCase();
      const displayLabel = pLower === 'x' ? 'X (Twitter)' : plat.charAt(0).toUpperCase() + plat.slice(1).toLowerCase();
      return {
        label: displayLabel,
        count: Number(cnt) || 0,
        color: colorMap[pLower] || '#3b82f6',
        key: plat,
      };
    });
  }, [summary]);

  // Visual: Horizontal Bar Distribusi Kategori (IPOLEKSOSBUDHANKAM)
  const categoryBarItems = useMemo(() => {
    if (!summary?.distribusi_kategori) return [];
    const colorMap: Record<string, string> = {
      Ideologi: '#ef4444',
      Politik: '#f97316',
      Ekonomi: '#eab308',
      Sosial: '#3b82f6',
      Budaya: '#8b5cf6',
      Pertahanan: '#06b6d4',
      Keamanan: '#10b981',
      'Non-Isu': '#64748b',
    };
    const standardCategories = ['Ideologi', 'Politik', 'Ekonomi', 'Sosial', 'Budaya', 'Pertahanan', 'Keamanan', 'Non-Isu'];
    const allKeys = Array.from(new Set([...standardCategories, ...Object.keys(summary.distribusi_kategori)]));
    return allKeys
      .map((cat) => ({
        label: cat,
        count: summary.distribusi_kategori[cat] || 0,
        color: colorMap[cat] || '#3b82f6',
        key: cat,
      }))
      .filter((item) => item.count > 0 || standardCategories.slice(0, 5).includes(item.label));
  }, [summary]);

  // Visual: Donut Distribusi Risiko
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

  return (
    <div className="space-y-5">
      {/* ── Page Header & Minimalist PDF Export Icon ── */}
      <div className="flex items-center justify-between gap-3 border-b border-slate-200 dark:border-white/[0.06] pb-3">
        <div>
          <div className="flex items-center gap-2 mb-1">
            <span className="font-mono text-[10px] tracking-widest text-blue-600 dark:text-blue-400 font-bold uppercase">
              KONSOL OPERASIONAL // TILIK
            </span>
            <span className="text-[10px] text-slate-300 dark:text-slate-700 font-mono">•</span>
            <span className="font-mono text-[10px] text-slate-400 dark:text-slate-500 uppercase">
              RINGKASAN METRIK & SASARAN
            </span>
          </div>
          <h1 className="text-lg sm:text-xl font-bold tracking-tight text-slate-900 dark:text-white font-mono">
            Ringkasan Operasi Ruang Siber
          </h1>
          <p className="text-xs text-slate-500 dark:text-slate-400 mt-0.5">
            Pantauan metrik patroli real-time, tren eskalasi narasi, dan pemantauan sasaran strategis terpadu
          </p>
        </div>

        {/* Minimalist Icon Export Button */}
        <button
          type="button"
          onClick={() => setShowPdfModal(true)}
          className="p-2.5 rounded-lg border border-slate-200 dark:border-white/[0.08] bg-white dark:bg-[#0E131F] hover:bg-slate-50 dark:hover:bg-white/[0.06] text-slate-700 dark:text-slate-300 hover:text-blue-600 dark:hover:text-blue-400 active:scale-[0.98] transition-all shadow-xs group relative shrink-0"
          title="Unduh Laporan PDF"
          aria-label="Unduh Laporan PDF"
        >
          <FileDown className="w-4 h-4" />
        </button>
      </div>

      {/* ── 1. BAR FILTER COMPACT & CLEAN ── */}
      <div className="cyber-card p-3 rounded-xl border border-slate-200 dark:border-white/[0.06] space-y-2">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-1.5 text-xs font-semibold text-slate-700 dark:text-slate-300 font-mono">
            <Filter className="w-3.5 h-3.5 text-blue-500" />
            <span>PARAMETER OPERASI</span>
          </div>
          {hasActiveFilters && (
            <button
              onClick={handleResetFilters}
              className="text-[11px] font-mono text-blue-600 dark:text-blue-400 hover:underline flex items-center gap-1 transition-colors"
            >
              <RotateCcw className="w-3 h-3" />
              Atur Ulang Filter
            </button>
          )}
        </div>

        <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-5 gap-2.5">
          <div>
            <label className="block text-[10px] font-mono font-semibold uppercase text-slate-500 dark:text-slate-400 mb-1">
              Dari Tanggal
            </label>
            <input
              type="date"
              value={dateFrom}
              onChange={(e) => setDateFrom(e.target.value)}
              className="w-full bg-white dark:bg-[#0A0D14] border border-slate-200 dark:border-white/[0.08] rounded-lg px-2.5 py-1 text-xs text-slate-800 dark:text-slate-200 focus:outline-none focus:ring-2 focus:ring-blue-500/20 focus:border-blue-500 font-mono transition-colors"
            />
          </div>

          <div>
            <label className="block text-[10px] font-mono font-semibold uppercase text-slate-500 dark:text-slate-400 mb-1">
              Sampai Tanggal
            </label>
            <input
              type="date"
              value={dateTo}
              onChange={(e) => setDateTo(e.target.value)}
              className="w-full bg-white dark:bg-[#0A0D14] border border-slate-200 dark:border-white/[0.08] rounded-lg px-2.5 py-1 text-xs text-slate-800 dark:text-slate-200 focus:outline-none focus:ring-2 focus:ring-blue-500/20 focus:border-blue-500 font-mono transition-colors"
            />
          </div>

          <div>
            <label className="block text-[10px] font-mono font-semibold uppercase text-slate-500 dark:text-slate-400 mb-1">
              Platform
            </label>
            <select
              value={selectedPlatform}
              onChange={(e) => setSelectedPlatform(e.target.value)}
              className="w-full bg-white dark:bg-[#0A0D14] border border-slate-200 dark:border-white/[0.08] rounded-lg px-2.5 py-1 text-xs text-slate-800 dark:text-slate-200 focus:outline-none focus:ring-2 focus:ring-blue-500/20 focus:border-blue-500 transition-colors"
            >
              <option value="Semua">Semua Platform</option>
              <option value="Instagram">Instagram</option>
              <option value="YouTube">YouTube</option>
              <option value="TikTok">TikTok</option>
              <option value="Threads">Threads</option>
              <option value="X">X (Twitter)</option>
              <option value="Facebook">Facebook</option>
            </select>
          </div>

          <div>
            <label className="block text-[10px] font-mono font-semibold uppercase text-slate-500 dark:text-slate-400 mb-1">
              Kategori
            </label>
            <select
              value={selectedCategory}
              onChange={(e) => setSelectedCategory(e.target.value)}
              className="w-full bg-white dark:bg-[#0A0D14] border border-slate-200 dark:border-white/[0.08] rounded-lg px-2.5 py-1 text-xs text-slate-800 dark:text-slate-200 focus:outline-none focus:ring-2 focus:ring-blue-500/20 focus:border-blue-500 transition-colors"
            >
              <option value="Semua">Semua Kategori</option>
              <option value="Ideologi">Ideologi</option>
              <option value="Politik">Politik</option>
              <option value="Ekonomi">Ekonomi</option>
              <option value="Sosial">Sosial</option>
              <option value="Budaya">Budaya</option>
              <option value="Pertahanan">Pertahanan</option>
              <option value="Keamanan">Keamanan</option>
              <option value="Non-Isu">Non-Isu</option>
            </select>
          </div>

          <div className="col-span-2 sm:col-span-1">
            <label className="block text-[10px] font-mono font-semibold uppercase text-slate-500 dark:text-slate-400 mb-1">
              Risiko
            </label>
            <select
              value={selectedRisk}
              onChange={(e) => setSelectedRisk(e.target.value)}
              className="w-full bg-white dark:bg-[#0A0D14] border border-slate-200 dark:border-white/[0.08] rounded-lg px-2.5 py-1 text-xs text-slate-800 dark:text-slate-200 focus:outline-none focus:ring-2 focus:ring-blue-500/20 focus:border-blue-500 transition-colors"
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
                <button onClick={() => setSelectedPlatform('Semua')}>
                  <XCircle className="w-3 h-3 hover:opacity-75" />
                </button>
              </span>
            )}
            {selectedCategory !== 'Semua' && (
              <span className="inline-flex items-center gap-1 text-[11px] bg-amber-500/10 text-amber-600 dark:text-amber-400 border border-amber-500/20 px-2 py-0.5 rounded font-mono font-medium">
                Kategori: {selectedCategory}
                <button onClick={() => setSelectedCategory('Semua')}>
                  <XCircle className="w-3 h-3 hover:opacity-75" />
                </button>
              </span>
            )}
            {selectedRisk !== 'Semua' && (
              <span className="inline-flex items-center gap-1 text-[11px] bg-rose-500/10 text-rose-600 dark:text-rose-400 border border-rose-500/20 px-2 py-0.5 rounded font-mono font-medium">
                Risiko: {selectedRisk}
                <button onClick={() => setSelectedRisk('Semua')}>
                  <XCircle className="w-3 h-3 hover:opacity-75" />
                </button>
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
      ) : (
        <div className="space-y-5">
          {/* Zero-Data Fresh Install Banner */}
          {summary?.total_laporan === 0 && !hasActiveFilters && (
            <div className="cyber-card rounded-xl p-4 sm:p-5 border border-blue-500/25 bg-blue-500/5 dark:bg-blue-500/[0.03] space-y-2">
              <div className="flex items-start gap-3">
                <div className="w-8 h-8 rounded-lg bg-blue-500/10 border border-blue-500/20 text-blue-500 flex items-center justify-center shrink-0 mt-0.5">
                  <ShieldCheck className="w-4 h-4" />
                </div>
                <div className="space-y-1">
                  <h4 className="text-xs font-bold font-mono text-slate-900 dark:text-white uppercase tracking-wider">
                    Sistem Pemantauan Siap Operasi — 100% On-Premise & Rantai Bukti Digital
                  </h4>
                  <p className="text-xs text-slate-600 dark:text-slate-400 leading-relaxed">
                    Belum ada rekaman temuan yang terakuisisi. Gunakan <strong>Ekstensi Peramban TILIK</strong> pada browser Anda untuk menangkap bukti postingan media sosial secara instan dan menyegelnya dengan kriptografi <strong>NIST FIPS 198-1 HMAC-SHA256</strong>.
                  </p>
                </div>
              </div>
            </div>
          )}

          {/* ── 2. KARTU KPI RINGKAS (4 KPI STRIP) ── */}
          <div className="grid grid-cols-2 lg:grid-cols-4 gap-3">
            <KPICard
              title="Total Temuan"
              value={summary?.total_laporan ?? 0}
              subtitle="Seluruh laporan tersimpan"
              icon={<FileText className="w-4 h-4 text-blue-500" />}
              accentColor="blue"
              onClick={() => setSelectedStatus('Semua')}
            />

            <KPICard
              title="Isu Aktif"
              value={trendingStats?.active_issues_count ?? 0}
              subtitle="Klaster terpantau aktif"
              icon={<Flame className="w-4 h-4 text-amber-500" />}
              accentColor="amber"
              onClick={() => navigate('/trending')}
            />

            <KPICard
              title="Urgensi Tinggi"
              value={summary?.distribusi_risiko?.TINGGI ?? trendingStats?.high_risk_contents ?? 0}
              subtitle="Konten risiko tinggi"
              icon={<AlertTriangle className="w-4 h-4 text-rose-500" />}
              accentColor="rose"
              onClick={() => setSelectedRisk('TINGGI')}
            />

            <KPICard
              title="Status Validasi"
              value={summary?.temuan_tervalidasi ?? 0}
              subtitle={`${
                summary?.total_laporan
                  ? Math.round((summary.temuan_tervalidasi / summary.total_laporan) * 100)
                  : 0
              }% terverifikasi analis`}
              icon={<CheckCircle className="w-4 h-4 text-emerald-500" />}
              trend={{ value: 'TERVERIFIKASI', isPositive: true }}
              accentColor="emerald"
              onClick={() => setSelectedStatus('VALIDATED')}
            />
          </div>

          {/* ── 3. VISUALISASI GRAFIK UTAMA ── */}
          {/* Grid Asimetris 8:4 (Tren Aktivitas & Distribusi Risiko) */}
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
                <span className="text-emerald-500 font-semibold">
                  Tervalidasi: {summary?.temuan_tervalidasi ?? 0}
                </span>
              </div>
            </div>
          </div>

          {/* Baris Grafis: Distribusi Platform & Kategori */}
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

          {/* ── 4. RINGKASAN ISU MENONJOL & TOKOH/SASARAN (2 KOLOM BERDAMPINGAN) ── */}
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
            {/* Kolom Kiri: Topik Isu Teratas */}
            <div className="cyber-card p-4 sm:p-5 rounded-xl space-y-3">
              <div className="flex items-center justify-between border-b border-slate-100 dark:border-white/[0.06] pb-2.5">
                <h3 className="text-xs font-bold text-slate-800 dark:text-slate-100 flex items-center gap-2 uppercase tracking-wider font-mono">
                  <Flame className="w-4 h-4 text-blue-500" />
                  Topik Isu Teratas ({topTopics.length})
                </h3>
                <Link
                  to="/trending"
                  className="text-xs font-semibold text-blue-600 dark:text-blue-400 hover:underline flex items-center gap-1 font-mono"
                >
                  <span>Buka Radar Isu</span>
                  <ArrowRight className="w-3.5 h-3.5" />
                </Link>
              </div>
              <div className="pt-1">
                {topTopics.length === 0 ? (
                  <div className="text-center py-6 text-slate-400 text-xs font-mono">
                    Belum ada data topik terpantau.
                  </div>
                ) : (
                  <HorizontalBarList
                    items={topTopics.map((t) => ({
                      label: t.name,
                      count: t.count,
                      color: '#3b82f6',
                      subtitle: t.category,
                    }))}
                    onBarClick={(item) => navigate(`/trending?q=${encodeURIComponent(item.label)}`)}
                  />
                )}
              </div>
            </div>

            {/* Kolom Kanan: Tokoh & Entitas Sasaran */}
            <div className="cyber-card p-4 sm:p-5 rounded-xl space-y-3">
              <div className="flex items-center justify-between border-b border-slate-100 dark:border-white/[0.06] pb-2.5">
                <h3 className="text-xs font-bold text-slate-800 dark:text-slate-100 flex items-center gap-2 uppercase tracking-wider font-mono">
                  <UserCheck className="w-4 h-4 text-emerald-500" />
                  Tokoh & Entitas Sasaran ({topActors.length})
                </h3>
                <Link
                  to="/trending"
                  className="text-xs font-semibold text-emerald-600 dark:text-emerald-400 hover:underline flex items-center gap-1 font-mono"
                >
                  <span>Buka Radar Isu</span>
                  <ArrowRight className="w-3.5 h-3.5" />
                </Link>
              </div>
              <div className="pt-1">
                {topActors.length === 0 ? (
                  <div className="text-center py-6 text-slate-400 text-xs font-mono">
                    Belum ada data tokoh/entitas terpantau.
                  </div>
                ) : (
                  <HorizontalBarList
                    items={topActors.map((a) => ({
                      label: a.name,
                      count: a.count,
                      color: '#10b981',
                      subtitle: a.category,
                    }))}
                    onBarClick={(item) => navigate(`/trending?actor=${encodeURIComponent(item.label)}`)}
                  />
                )}
              </div>
            </div>
          </div>

          {/* ── 5. TABEL TEMUAN PRIORITAS TERBARU (LINEAR STYLE) ── */}
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
                {hasActiveFilters
                  ? 'Tidak ada temuan yang sesuai dengan kriteria filter saat ini.'
                  : 'Belum ada temuan prioritas yang terekam dalam sistem.'}
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

                      const statusLabel =
                        r.status === 'VALIDATED'
                          ? 'TERVALIDASI'
                          : r.status === 'MODIFIED'
                          ? 'KOREKSI'
                          : r.status === 'REJECTED'
                          ? 'BUKAN PELANGGARAN'
                          : 'MENUNGGU';

                      return (
                        <tr
                          key={r.report_id}
                          onClick={() => navigate(`/contents/${contentId}`)}
                          className="hover:bg-slate-50 dark:hover:bg-white/[0.02] cursor-pointer transition-colors"
                        >
                          <td className="py-2.5 px-3">
                            <div className="font-bold text-slate-800 dark:text-slate-200">
                              {r.ticket_number}
                            </div>
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
                                  ? 'text-emerald-500 bg-emerald-500/10 border border-emerald-500/20'
                                  : r.status === 'MODIFIED'
                                  ? 'text-amber-500 bg-amber-500/10 border border-amber-500/20'
                                  : r.status === 'REJECTED'
                                  ? 'text-rose-500 bg-rose-500/10 border border-rose-500/20'
                                  : 'text-slate-500 bg-slate-500/10 border border-slate-500/20'
                              }`}
                            >
                              {statusLabel}
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
      )}

      {/* ── Modal Filter Laporan PDF Analitis ── */}
      {showPdfModal && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/60 backdrop-blur-sm animate-fade-in">
          <div className="w-full max-w-md max-h-[90dvh] rounded-2xl bg-white dark:bg-[#0E131F] border border-slate-200 dark:border-white/[0.1] shadow-2xl overflow-hidden overflow-y-auto font-sans">
            {/* Header */}
            <div className="flex items-center justify-between p-4 border-b border-slate-100 dark:border-white/[0.08]">
              <div className="flex items-center gap-2">
                <div className="w-7 h-7 rounded-lg bg-blue-500/10 flex items-center justify-center text-blue-500">
                  <Download className="w-4 h-4" />
                </div>
                <div>
                  <h3 className="text-sm font-bold text-slate-900 dark:text-white font-mono">
                    Unduh Laporan PDF
                  </h3>
                  <p className="text-[10px] text-slate-500 dark:text-slate-400">
                    Laporan analitis, visualisasi grafik & narasi AI
                  </p>
                </div>
              </div>
              <button
                type="button"
                onClick={() => setShowPdfModal(false)}
                className="text-slate-400 hover:text-slate-600 dark:hover:text-slate-200 transition-colors"
              >
                <X className="w-4 h-4" />
              </button>
            </div>

            {/* Body */}
            <div className="p-4 space-y-4 text-xs">
              {pdfError && (
                <div className="p-2.5 rounded-lg bg-rose-500/10 border border-rose-500/20 text-rose-500 text-[11px] font-mono">
                  {pdfError}
                </div>
              )}

              {/* Periode Selector */}
              <div className="space-y-1.5">
                <label className="text-[11px] font-mono font-semibold uppercase tracking-wider text-slate-700 dark:text-slate-300">
                  Periode Pemantauan
                </label>
                <div className="grid grid-cols-3 gap-1.5 p-1 rounded-lg bg-slate-100 dark:bg-white/[0.04] border border-slate-200 dark:border-white/[0.06] text-center">
                  <button
                    type="button"
                    onClick={() => setPdfPeriod('daily')}
                    className={`py-1.5 rounded-md font-mono text-[11px] font-semibold transition-colors ${
                      pdfPeriod === 'daily'
                        ? 'bg-blue-600 text-white shadow-sm'
                        : 'text-slate-600 dark:text-slate-400 hover:text-slate-900 dark:hover:text-white'
                    }`}
                  >
                    Harian
                  </button>
                  <button
                    type="button"
                    onClick={() => setPdfPeriod('weekly')}
                    className={`py-1.5 rounded-md font-mono text-[11px] font-semibold transition-colors ${
                      pdfPeriod === 'weekly'
                        ? 'bg-blue-600 text-white shadow-sm'
                        : 'text-slate-600 dark:text-slate-400 hover:text-slate-900 dark:hover:text-white'
                    }`}
                  >
                    Mingguan
                  </button>
                  <button
                    type="button"
                    onClick={() => setPdfPeriod('custom')}
                    className={`py-1.5 rounded-md font-mono text-[11px] font-semibold transition-colors ${
                      pdfPeriod === 'custom'
                        ? 'bg-blue-600 text-white shadow-sm'
                        : 'text-slate-600 dark:text-slate-400 hover:text-slate-900 dark:hover:text-white'
                    }`}
                  >
                    Kustom
                  </button>
                </div>
              </div>

              {/* Conditional Inputs */}
              {pdfPeriod === 'daily' && (
                <div className="space-y-1">
                  <label className="text-[10px] font-mono uppercase text-slate-500 dark:text-slate-400">
                    Pilih Tanggal
                  </label>
                  <input
                    type="date"
                    value={pdfDate}
                    onChange={(e) => setPdfDate(e.target.value)}
                    className="w-full bg-slate-50 dark:bg-[#070A11] border border-slate-200 dark:border-white/[0.08] rounded-lg px-3 py-1.5 text-xs text-slate-800 dark:text-slate-200 focus:outline-none focus:border-blue-500 font-mono"
                  />
                </div>
              )}

              {pdfPeriod === 'weekly' && (
                <div className="p-2.5 rounded-lg bg-blue-500/10 border border-blue-500/20 text-[11px] text-blue-600 dark:text-blue-400 font-mono">
                  Mencakup akumulasi seluruh temuan 7 hari terakhir hingga hari ini.
                </div>
              )}

              {pdfPeriod === 'custom' && (
                <div className="grid grid-cols-2 gap-2">
                  <div className="space-y-1">
                    <label className="text-[10px] font-mono uppercase text-slate-500 dark:text-slate-400">
                      Dari Tanggal
                    </label>
                    <input
                      type="date"
                      value={pdfStartDate}
                      onChange={(e) => setPdfStartDate(e.target.value)}
                      className="w-full bg-slate-50 dark:bg-[#070A11] border border-slate-200 dark:border-white/[0.08] rounded-lg px-2.5 py-1.5 text-xs text-slate-800 dark:text-slate-200 focus:outline-none focus:border-blue-500 font-mono"
                    />
                  </div>
                  <div className="space-y-1">
                    <label className="text-[10px] font-mono uppercase text-slate-500 dark:text-slate-400">
                      Sampai Tanggal
                    </label>
                    <input
                      type="date"
                      value={pdfEndDate}
                      onChange={(e) => setPdfEndDate(e.target.value)}
                      className="w-full bg-slate-50 dark:bg-[#070A11] border border-slate-200 dark:border-white/[0.08] rounded-lg px-2.5 py-1.5 text-xs text-slate-800 dark:text-slate-200 focus:outline-none focus:border-blue-500 font-mono"
                    />
                  </div>
                </div>
              )}

              {/* Kategori Selector */}
              <div className="space-y-1">
                <label className="text-[11px] font-mono font-semibold uppercase tracking-wider text-slate-700 dark:text-slate-300">
                  Filter Kategori Kasus
                </label>
                <select
                  value={pdfCategory}
                  onChange={(e) => setPdfCategory(e.target.value)}
                  className="w-full bg-slate-50 dark:bg-[#070A11] border border-slate-200 dark:border-white/[0.08] rounded-lg px-3 py-1.5 text-xs text-slate-800 dark:text-slate-200 focus:outline-none focus:border-blue-500 font-mono"
                >
                  <option value="Semua Kategori">Semua Kategori</option>
                  <option value="Politik">Politik</option>
                  <option value="Keamanan">Keamanan</option>
                  <option value="Sosial">Sosial</option>
                  <option value="Ekonomi">Ekonomi</option>
                  <option value="Ideologi">Ideologi</option>
                  <option value="Pertahanan">Pertahanan</option>
                  <option value="Budaya">Budaya</option>
                  <option value="Non-Isu">Non-Isu</option>
                </select>
              </div>
            </div>

            {/* Footer Buttons */}
            <div className="flex items-center justify-end gap-2 p-3.5 bg-slate-50 dark:bg-white/[0.02] border-t border-slate-100 dark:border-white/[0.08]">
              <button
                type="button"
                onClick={() => setShowPdfModal(false)}
                disabled={isGeneratingPdf}
                className="px-3 py-1.5 rounded-lg text-xs font-mono font-semibold text-slate-600 dark:text-slate-400 hover:text-slate-900 dark:hover:text-white transition-colors"
              >
                Batal
              </button>
              <button
                type="button"
                onClick={handleDownloadAnalyticalPdf}
                disabled={isGeneratingPdf}
                className="flex items-center gap-1.5 px-3.5 py-1.5 rounded-lg text-xs font-mono font-semibold bg-blue-600 hover:bg-blue-500 text-white shadow-sm transition-colors disabled:opacity-50"
              >
                {isGeneratingPdf ? (
                  <>
                    <RefreshCw className="w-3.5 h-3.5 animate-spin" />
                    <span>Mengenerate PDF...</span>
                  </>
                ) : (
                  <>
                    <Download className="w-3.5 h-3.5" />
                    <span>Generate & Unduh PDF</span>
                  </>
                )}
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};
