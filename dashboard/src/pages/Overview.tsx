import React, { useEffect, useState, useMemo } from 'react';
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
  Clock,
  Flame,
  CheckCircle,
  AlertTriangle,
  ArrowRight,
  TrendingUp,
  ShieldCheck,
  UserCheck,
  Radio,
  FileDown,
  Info,
  Filter,
  RotateCcw,
  ExternalLink,
  Layers,
  Sparkles,
  BarChart2,
  Calendar,
  XCircle,
  Tag,
  Check,
  Edit3,
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

  // Data states
  const [summary, setSummary] = useState<any>(null);
  const [timeseries, setTimeseries] = useState<DualLinePoint[]>([]);
  const [topTopics, setTopTopics] = useState<any[]>([]);
  const [topActors, setTopActors] = useState<any[]>([]);
  const [topSources, setTopSources] = useState<any[]>([]);
  const [reports, setReports] = useState<any[]>([]);
  const [trendingStats, setTrendingStats] = useState<any>(null);

  const [loading, setLoading] = useState<boolean>(true);
  const [exporting, setExporting] = useState<boolean>(false);
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

  // Check if any filter is active
  const hasActiveFilters =
    dateFrom ||
    dateTo ||
    selectedPlatform !== 'Semua' ||
    selectedCategory !== 'Semua' ||
    selectedRisk !== 'Semua' ||
    selectedStatus !== 'Semua';

  // Secure Blob Export CSV
  const handleExportCSV = async () => {
    try {
      setExporting(true);
      await apiClient.v1.exportBlob('csv', {
        date_from: dateFrom || undefined,
        date_to: dateTo || undefined,
        category: selectedCategory !== 'Semua' ? selectedCategory : undefined,
        risk_level: selectedRisk !== 'Semua' ? selectedRisk : undefined,
      });
    } catch (err) {
      alert('Gagal mengekspor berkas CSV.');
    } finally {
      setExporting(false);
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
      color: colorMap[cat] || '#00f0ff',
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
    <div className="space-y-6">
      {/* ── Page Header & Tabs ── */}
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4">
        <div>
          <div className="flex items-center gap-2">
            <h1 className="text-xl font-bold tracking-tight text-white flex items-center gap-2">
              <ShieldCheck className="w-6 h-6 text-cyan-400" />
              Dashboard Analitik Patroli Siber & Profiling Akun
            </h1>
            <span className="text-[10px] font-mono px-2 py-0.5 rounded bg-cyan-950/80 text-cyan-400 border border-cyan-500/30">
              v2.2 Enterprise Edition
            </span>
          </div>
          <p className="text-xs text-slate-400 mt-1">
            Visualisasi operasional patroli siber terintegrasi (FR-01 s.d. FR-12, DFD Level 0–2, ERD 11 Tabel Fisik).
          </p>
        </div>

        {/* Tab Selector & Export Button */}
        <div className="flex items-center gap-3">
          <div className="bg-slate-900 p-1 rounded-lg border border-slate-800 flex items-center text-xs">
            <button
              onClick={() => setActiveTab('proposal')}
              className={`px-3 py-1.5 rounded-md font-medium transition-all flex items-center gap-1.5 ${
                activeTab === 'proposal'
                  ? 'bg-cyan-500/20 text-cyan-300 border border-cyan-500/40 shadow-sm'
                  : 'text-slate-400 hover:text-slate-200'
              }`}
            >
              <BarChart2 className="w-3.5 h-3.5" />
              <span>Analitik Proposal (8 Visual)</span>
            </button>
            <button
              onClick={() => setActiveTab('intel')}
              className={`px-3 py-1.5 rounded-md font-medium transition-all flex items-center gap-1.5 ${
                activeTab === 'intel'
                  ? 'bg-cyan-500/20 text-cyan-300 border border-cyan-500/40 shadow-sm'
                  : 'text-slate-400 hover:text-slate-200'
              }`}
            >
              <Flame className="w-3.5 h-3.5" />
              <span>Radar 5W+1H & Topik Tren</span>
            </button>
          </div>

          <button
            onClick={handleExportCSV}
            disabled={exporting}
            className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-semibold bg-emerald-600/20 text-emerald-300 border border-emerald-500/40 hover:bg-emerald-600/30 transition-all disabled:opacity-50"
            title="Ekspor data hasil filter ke CSV aman (Bearer Token)"
          >
            <FileDown className="w-3.5 h-3.5" />
            <span>{exporting ? 'Mengunduh...' : 'Ekspor CSV'}</span>
          </button>
        </div>
      </div>

      {/* ── 1. BAR FILTER UTAMA (Proposal FR-11) ── */}
      <div className="cyber-card p-4 rounded-xl border border-slate-800 space-y-3">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-2 text-xs font-semibold text-slate-300">
            <Filter className="w-4 h-4 text-cyan-400" />
            <span>Bar Filter Utama (Drill-Down Multi-Dimensi)</span>
          </div>
          {hasActiveFilters && (
            <button
              onClick={handleResetFilters}
              className="text-[11px] font-mono text-cyan-400 hover:text-cyan-300 flex items-center gap-1 bg-cyan-950/40 px-2 py-0.5 rounded border border-cyan-500/20 transition-colors"
            >
              <RotateCcw className="w-3 h-3" />
              Reset Filter
            </button>
          )}
        </div>

        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-5 gap-3">
          {/* Rentang Tanggal Mulai */}
          <div>
            <label className="block text-[10px] font-mono uppercase text-slate-400 mb-1">Dari Tanggal</label>
            <input
              type="date"
              value={dateFrom}
              onChange={(e) => setDateFrom(e.target.value)}
              className="w-full bg-slate-900 border border-slate-700 rounded-lg px-2.5 py-1.5 text-xs text-slate-200 focus:outline-none focus:border-cyan-500"
            />
          </div>

          {/* Rentang Tanggal Selesai */}
          <div>
            <label className="block text-[10px] font-mono uppercase text-slate-400 mb-1">Sampai Tanggal</label>
            <input
              type="date"
              value={dateTo}
              onChange={(e) => setDateTo(e.target.value)}
              className="w-full bg-slate-900 border border-slate-700 rounded-lg px-2.5 py-1.5 text-xs text-slate-200 focus:outline-none focus:border-cyan-500"
            />
          </div>

          {/* Platform */}
          <div>
            <label className="block text-[10px] font-mono uppercase text-slate-400 mb-1">Platform</label>
            <select
              value={selectedPlatform}
              onChange={(e) => setSelectedPlatform(e.target.value)}
              className="w-full bg-slate-900 border border-slate-700 rounded-lg px-2.5 py-1.5 text-xs text-slate-200 focus:outline-none focus:border-cyan-500"
            >
              <option value="Semua">Semua Platform</option>
              <option value="Instagram">Instagram</option>
              <option value="YouTube">YouTube</option>
              <option value="TikTok">TikTok</option>
            </select>
          </div>

          {/* Kategori Isu */}
          <div>
            <label className="block text-[10px] font-mono uppercase text-slate-400 mb-1">Kategori Isu</label>
            <select
              value={selectedCategory}
              onChange={(e) => setSelectedCategory(e.target.value)}
              className="w-full bg-slate-900 border border-slate-700 rounded-lg px-2.5 py-1.5 text-xs text-slate-200 focus:outline-none focus:border-cyan-500"
            >
              <option value="Semua">Semua Kategori</option>
              <option value="HOAKS">HOAKS</option>
              <option value="DI_LUAR_KONTEKS">DI LUAR KONTEKS</option>
              <option value="UJARAN_KEBENCIAN">UJARAN KEBENCIAN</option>
              <option value="PROVOKASI_SARA">PROVOKASI SARA</option>
            </select>
          </div>

          {/* Tingkat Risiko */}
          <div>
            <label className="block text-[10px] font-mono uppercase text-slate-400 mb-1">Tingkat Risiko</label>
            <select
              value={selectedRisk}
              onChange={(e) => setSelectedRisk(e.target.value)}
              className="w-full bg-slate-900 border border-slate-700 rounded-lg px-2.5 py-1.5 text-xs text-slate-200 focus:outline-none focus:border-cyan-500"
            >
              <option value="Semua">Semua Risiko</option>
              <option value="TINGGI">TINGGI</option>
              <option value="SEDANG">SEDANG</option>
              <option value="RENDAH">RENDAH</option>
            </select>
          </div>
        </div>

        {/* Active Filter Chips */}
        {hasActiveFilters && (
          <div className="pt-2 border-t border-slate-800/80 flex flex-wrap items-center gap-2">
            <span className="text-[10px] font-mono text-slate-500 uppercase">Filter Aktif:</span>
            {selectedPlatform !== 'Semua' && (
              <span className="inline-flex items-center gap-1 text-[11px] bg-cyan-950 text-cyan-300 border border-cyan-800 px-2 py-0.5 rounded-full">
                Platform: {selectedPlatform}
                <button onClick={() => setSelectedPlatform('Semua')}><XCircle className="w-3 h-3 hover:text-white" /></button>
              </span>
            )}
            {selectedCategory !== 'Semua' && (
              <span className="inline-flex items-center gap-1 text-[11px] bg-amber-950 text-amber-300 border border-amber-800 px-2 py-0.5 rounded-full">
                Kategori: {selectedCategory}
                <button onClick={() => setSelectedCategory('Semua')}><XCircle className="w-3 h-3 hover:text-white" /></button>
              </span>
            )}
            {selectedRisk !== 'Semua' && (
              <span className="inline-flex items-center gap-1 text-[11px] bg-rose-950 text-rose-300 border border-rose-800 px-2 py-0.5 rounded-full">
                Risiko: {selectedRisk}
                <button onClick={() => setSelectedRisk('Semua')}><XCircle className="w-3 h-3 hover:text-white" /></button>
              </span>
            )}
            {selectedStatus !== 'Semua' && (
              <span className="inline-flex items-center gap-1 text-[11px] bg-purple-950 text-purple-300 border border-purple-800 px-2 py-0.5 rounded-full">
                Status: {selectedStatus}
                <button onClick={() => setSelectedStatus('Semua')}><XCircle className="w-3 h-3 hover:text-white" /></button>
              </span>
            )}
          </div>
        )}
      </div>

      {loading && !summary ? (
        <div className="flex flex-col items-center justify-center min-h-[50vh] gap-3">
          <div className="w-10 h-10 border-2 border-cyan-400 border-t-transparent rounded-full animate-spin" />
          <span className="text-xs font-mono text-cyan-400">MENYINKRONKAN 8 GRAFIK PROPOSAL...</span>
        </div>
      ) : error ? (
        <div className="p-8 cyber-card rounded-xl text-center">
          <AlertTriangle className="w-8 h-8 text-rose-400 mx-auto mb-2" />
          <p className="text-rose-300 text-sm font-semibold">{error}</p>
        </div>
      ) : activeTab === 'proposal' ? (
        /* ══════════════════════════════════════════════════════════════
           TAB 1: RINGKASAN ANALITIK PROPOSAL (4 KPI + 8 VISUAL)
           ══════════════════════════════════════════════════════════════ */
        <div className="space-y-6">
          {/* ── 2. 4 KARTU KPI RINGKASAN (Sesuai Gambar L3.18) ── */}
          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
            {/* Kartu 1: Total laporan */}
            <div
              className="cursor-pointer transition-transform hover:-translate-y-0.5"
              onClick={() => setSelectedStatus('Semua')}
            >
              <KPICard
                title="Total Laporan"
                value={summary?.total_laporan ?? 0}
                icon={<FileText className="w-5 h-5 text-cyan-400" />}
                subtitle="Seluruh temuan masuk"
                accentColor="cyan"
              />
            </div>

            {/* Kartu 2: Temuan tervalidasi */}
            <div
              className="cursor-pointer transition-transform hover:-translate-y-0.5"
              onClick={() => setSelectedStatus('VALIDATED')}
            >
              <KPICard
                title="Temuan Tervalidasi"
                value={summary?.temuan_tervalidasi ?? 0}
                icon={<CheckCircle className="w-5 h-5 text-emerald-400" />}
                subtitle="Status VALIDATED + MODIFIED"
                accentColor="emerald"
              />
            </div>

            {/* Kartu 3: Koreksi analis */}
            <div
              className="cursor-pointer transition-transform hover:-translate-y-0.5"
              onClick={() => setSelectedStatus('MODIFIED')}
            >
              <KPICard
                title="Koreksi Analis"
                value={summary?.koreksi_analis ?? 0}
                icon={<Edit3 className="w-5 h-5 text-amber-400" />}
                subtitle="Putusan MODIFIED"
                accentColor="amber"
              />
            </div>

            {/* Kartu 4: Bukan pelanggaran */}
            <div
              className="cursor-pointer transition-transform hover:-translate-y-0.5"
              onClick={() => setSelectedStatus('REJECTED')}
            >
              <KPICard
                title="Bukan Pelanggaran"
                value={summary?.bukan_pelanggaran ?? 0}
                icon={<XCircle className="w-5 h-5 text-rose-400" />}
                subtitle="Putusan REJECTED (False Pos)"
                accentColor="rose"
              />
            </div>
          </div>

          {/* ── 3. 8 GRAFIK VISUAL WAJIB PROPOSAL ── */}
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
            {/* Visual 1 (Tren Waktu): Line Chart Ganda Laporan vs Tervalidasi */}
            <div className="cyber-card p-5 rounded-xl space-y-3">
              <div className="flex items-center justify-between">
                <div>
                  <h3 className="text-sm font-bold text-white flex items-center gap-2">
                    <TrendingUp className="w-4 h-4 text-cyan-400" />
                    Visual 1: Tren Waktu Temuan Harian
                  </h3>
                  <p className="text-[11px] text-slate-400 mt-0.5">
                    Perbandingan garis Laporan Masuk vs Temuan Tervalidasi per hari.
                  </p>
                </div>
              </div>
              <div className="pt-2">
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

            {/* Visual 2 (Per Platform): Vertical Bar Chart Platform */}
            <div className="cyber-card p-5 rounded-xl space-y-3">
              <div className="flex items-center justify-between">
                <div>
                  <h3 className="text-sm font-bold text-white flex items-center gap-2">
                    <Layers className="w-4 h-4 text-cyan-400" />
                    Visual 2: Distribusi Temuan Per Platform
                  </h3>
                  <p className="text-[11px] text-slate-400 mt-0.5">
                    Jumlah temuan tervalidasi pada Instagram, TikTok, dan YouTube.
                  </p>
                </div>
              </div>
              <div className="pt-2">
                <VerticalBarChart
                  items={platformBarItems}
                  height={190}
                  onBarClick={(item) => setSelectedPlatform(item.label)}
                />
              </div>
            </div>

            {/* Visual 3 (Per Kategori): Horizontal Bar Chart final_label */}
            <div className="cyber-card p-5 rounded-xl space-y-3">
              <div className="flex items-center justify-between">
                <div>
                  <h3 className="text-sm font-bold text-white flex items-center gap-2">
                    <Tag className="w-4 h-4 text-amber-400" />
                    Visual 3: Distribusi Kategori Isu Final
                  </h3>
                  <p className="text-[11px] text-slate-400 mt-0.5">
                    Jumlah temuan berdasarkan final_label putusan analis.
                  </p>
                </div>
              </div>
              <div className="pt-2">
                <HorizontalBarList
                  items={categoryBarItems}
                  onBarClick={(item) => setSelectedCategory(item.key)}
                />
              </div>
            </div>

            {/* Visual 4 (Distribusi Risiko): Donut Chart final_risk */}
            <div className="cyber-card p-5 rounded-xl space-y-3">
              <div className="flex items-center justify-between">
                <div>
                  <h3 className="text-sm font-bold text-white flex items-center gap-2">
                    <AlertTriangle className="w-4 h-4 text-rose-400" />
                    Visual 4: Proporsi Tingkat Risiko Final
                  </h3>
                  <p className="text-[11px] text-slate-400 mt-0.5">
                    Persentase tingkat risiko final (Sedang, Tinggi, Rendah).
                  </p>
                </div>
              </div>
              <div className="pt-2">
                <DonutChart
                  items={riskDonutItems}
                  centerLabel="Temuan"
                  centerValue={summary?.temuan_tervalidasi ?? 0}
                  onItemClick={(item) => setSelectedRisk(item.label)}
                />
              </div>
            </div>

            {/* Visual 5 (Topik Teratas): Horizontal Bar Chart TOPIC */}
            <div className="cyber-card p-5 rounded-xl space-y-3">
              <div className="flex items-center justify-between">
                <div>
                  <h3 className="text-sm font-bold text-white flex items-center gap-2">
                    <TrendingUp className="w-4 h-4 text-cyan-400" />
                    Visual 5: Topik Hangat Teratas (TOPIC)
                  </h3>
                  <p className="text-[11px] text-slate-400 mt-0.5">
                    Entitas kanonikal bertipe TOPIC paling sering muncul dalam temuan.
                  </p>
                </div>
              </div>
              <div className="pt-2">
                <HorizontalBarList
                  items={topTopics.map((t) => ({
                    label: t.name,
                    count: t.count,
                    color: '#00f0ff',
                    subtitle: t.category,
                  }))}
                  onBarClick={(item) => {}}
                />
              </div>
            </div>

            {/* Visual 6 (Aktor Target Teratas): Horizontal Bar Chart ACTOR (via report_actors) */}
            <div className="cyber-card p-5 rounded-xl space-y-3">
              <div className="flex items-center justify-between">
                <div>
                  <h3 className="text-sm font-bold text-white flex items-center gap-2">
                    <UserCheck className="w-4 h-4 text-emerald-400" />
                    Visual 6: Aktor / Figur Sasaran Teratas (ACTOR)
                  </h3>
                  <p className="text-[11px] text-slate-400 mt-0.5">
                    Entitas bertipe ACTOR yang dihubungkan melalui tabel relasi report_actors.
                  </p>
                </div>
              </div>
              <div className="pt-2">
                <HorizontalBarList
                  items={topActors.map((a) => ({
                    label: a.name,
                    count: a.count,
                    color: '#10b981',
                    subtitle: a.category,
                  }))}
                  onBarClick={(item) => {}}
                />
              </div>
            </div>

            {/* Visual 7 (Sumber Konten Teratas): Horizontal Bar Chart SOURCE */}
            <div className="cyber-card p-5 rounded-xl space-y-3">
              <div className="flex items-center justify-between">
                <div>
                  <h3 className="text-sm font-bold text-white flex items-center gap-2">
                    <Radio className="w-4 h-4 text-violet-400" />
                    Visual 7: Sumber Konten Dominan (SOURCE)
                  </h3>
                  <p className="text-[11px] text-slate-400 mt-0.5">
                    Kanal penyebar disinformasi / konten yang paling sering dipantau.
                  </p>
                </div>
              </div>
              <div className="pt-2">
                <HorizontalBarList
                  items={topSources.map((s) => ({
                    label: s.name,
                    count: s.count,
                    color: '#a855f7',
                    subtitle: s.category,
                  }))}
                  onBarClick={(item) => {}}
                />
              </div>
            </div>

            {/* Visual 8 (Kesepakatan AI vs Analis): Vertical Bar Chart */}
            <div className="cyber-card p-5 rounded-xl space-y-3">
              <div className="flex items-center justify-between">
                <div>
                  <h3 className="text-sm font-bold text-white flex items-center gap-2">
                    <CheckCircle className="w-4 h-4 text-emerald-400" />
                    Visual 8: Kesepakatan AI vs Putusan Analis
                  </h3>
                  <p className="text-[11px] text-slate-400 mt-0.5">
                    Perbandingan jumlah putusan VALIDATED, MODIFIED, dan REJECTED.
                  </p>
                </div>
              </div>
              <div className="pt-2">
                <VerticalBarChart
                  items={agreementBarItems}
                  height={190}
                  onBarClick={(item) => setSelectedStatus(item.key || 'Semua')}
                />
              </div>
            </div>
          </div>

          {/* ── 4. BANNER DISCLAIMER NETRALITAS WAJIB (Proposal NFR-06) ── */}
          <div className="p-4 rounded-xl bg-slate-900/90 border border-cyan-500/30 flex items-start gap-3 shadow-md">
            <Info className="w-5 h-5 text-cyan-400 shrink-0 mt-0.5" />
            <div className="text-xs text-slate-300 leading-relaxed font-sans">
              <span className="font-bold text-cyan-300">Disclaimer Netralitas Data (NFR-06): </span>
              Frekuensi kemunculan topik, aktor, dan sumber tidak menunjukkan kesalahan pihak mana pun. Status tiket dan
              keputusan analis merupakan hasil simulasi triase teknis operasional, bukan penetapan hukum otomatis.
            </div>
          </div>

          {/* ── 5. TABEL LAPORAN HASIL DRILL-DOWN ── */}
          <div className="cyber-card rounded-xl p-5 space-y-4">
            <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3">
              <div>
                <h3 className="text-sm font-bold text-white flex items-center gap-2">
                  <FileText className="w-4 h-4 text-cyan-400" />
                  Daftar Tiket Temuan Patroli ({reports.length} Data Ditampilkan)
                </h3>
                <p className="text-[11px] text-slate-400 mt-0.5">
                  Daftar laporan yang tersinkronisasi sesuai filter dan interaksi drill-down di atas.
                </p>
              </div>
              <Link
                to="/contents"
                className="text-xs font-semibold text-cyan-400 hover:text-cyan-300 flex items-center gap-1 transition-colors"
              >
                <span>Buka Content Explorer Lengkap</span>
                <ArrowRight className="w-3.5 h-3.5" />
              </Link>
            </div>

            {reports.length === 0 ? (
              <div className="text-center py-12 text-slate-500 text-xs font-mono">
                Tidak ada laporan yang sesuai dengan kriteria filter saat ini.
              </div>
            ) : (
              <div className="overflow-x-auto">
                <table className="w-full text-left text-xs">
                  <thead className="bg-slate-900/90 text-slate-400 uppercase text-[10px] font-semibold tracking-wider border-b border-slate-800">
                    <tr>
                      <th className="py-2.5 px-3">Tiket & Waktu</th>
                      <th className="py-2.5 px-3">Platform & Akun</th>
                      <th className="py-2.5 px-3">Kategori Final</th>
                      <th className="py-2.5 px-3">Risiko</th>
                      <th className="py-2.5 px-3">Topik / Sasaran</th>
                      <th className="py-2.5 px-3">Status</th>
                      <th className="py-2.5 px-3">Catatan Analis</th>
                      <th className="py-2.5 px-3 text-right">Aksi</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-slate-800/60 font-mono">
                    {reports.map((r: any) => {
                      const statusColor =
                        r.status === 'VALIDATED'
                          ? 'text-emerald-400 bg-emerald-950/60 border-emerald-800/40'
                          : r.status === 'MODIFIED'
                          ? 'text-amber-400 bg-amber-950/60 border-amber-800/40'
                          : r.status === 'REJECTED'
                          ? 'text-rose-400 bg-rose-950/60 border-rose-800/40'
                          : 'text-cyan-400 bg-cyan-950/60 border-cyan-800/40';

                      const riskColor =
                        r.final_risk === 'TINGGI'
                          ? 'text-rose-400'
                          : r.final_risk === 'SEDANG'
                          ? 'text-amber-400'
                          : r.final_risk === 'RENDAH'
                          ? 'text-emerald-400'
                          : 'text-slate-400';

                      return (
                        <tr key={r.report_id} className="hover:bg-slate-800/40 transition-colors">
                          <td className="py-2.5 px-3">
                            <div className="font-bold text-slate-200">{r.ticket_number}</div>
                            <div className="text-[10px] text-slate-500">
                              {r.created_at ? r.created_at.slice(0, 16).replace('T', ' ') : '-'}
                            </div>
                          </td>
                          <td className="py-2.5 px-3">
                            <span className="text-[11px] font-bold text-cyan-300 uppercase">{r.platform}</span>
                            <div className="text-[10px] text-slate-400">@{r.account?.username || 'anonim'}</div>
                          </td>
                          <td className="py-2.5 px-3">
                            <span className="font-sans font-semibold text-slate-200">
                              {r.final_label || r.ai_predicted_label || '-'}
                            </span>
                          </td>
                          <td className="py-2.5 px-3">
                            <span className={`font-bold ${riskColor}`}>{r.final_risk || 'NIHIL'}</span>
                          </td>
                          <td className="py-2.5 px-3 font-sans">
                            <div className="text-slate-300 text-[11px] font-medium">{r.topic || '-'}</div>
                            {r.actors && r.actors.length > 0 && (
                              <div className="text-[10px] text-slate-400">Sasaran: {r.actors.join(', ')}</div>
                            )}
                          </td>
                          <td className="py-2.5 px-3">
                            <span className={`text-[10px] px-2 py-0.5 rounded border font-semibold ${statusColor}`}>
                              {r.status}
                            </span>
                          </td>
                          <td className="py-2.5 px-3 font-sans text-slate-400 text-[11px] max-w-xs truncate">
                            {r.analyst_notes || '-'}
                          </td>
                          <td className="py-2.5 px-3 text-right">
                            {r.url ? (
                              <a
                                href={r.url}
                                target="_blank"
                                rel="noreferrer"
                                className="inline-flex items-center gap-1 text-[11px] text-cyan-400 hover:text-cyan-300"
                              >
                                <span>Konten</span>
                                <ExternalLink className="w-3 h-3" />
                              </a>
                            ) : (
                              <span className="text-slate-600">-</span>
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
           TAB 2: RADAR 5W+1H & TOPIK TREN (FITUR SEKUNDER)
           ══════════════════════════════════════════════════════════════ */
        <div className="space-y-6">
          {/* Trending & Sentiments Row */}
          <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
            {/* Sentiment Gauge */}
            <div className="cyber-card p-5 rounded-xl space-y-3">
              <h3 className="text-sm font-bold text-white flex items-center justify-between">
                <span>Sentimen Opini Publik</span>
                <span className="text-[11px] font-mono text-cyan-400">Analisis Multimodal</span>
              </h3>
              {trendingStats?.sentiments && (
                <DonutChart
                  items={trendingStats.sentiments.map((s: any) => ({
                    label: s.sentiment,
                    count: s.count,
                    color:
                      s.sentiment === 'POSITIF'
                        ? '#10b981'
                        : s.sentiment === 'NEGATIF'
                        ? '#ef4444'
                        : '#0284c7',
                  }))}
                  centerLabel="Sentimen"
                />
              )}
            </div>

            {/* Score Gauge */}
            <div className="cyber-card p-5 rounded-xl space-y-3 flex flex-col items-center justify-center text-center">
              <h3 className="text-sm font-bold text-white mb-2">Indeks Keparahan Narasi Siber</h3>
              <ScoreGauge score={68} size={110} />
              <p className="text-[11px] text-slate-400 max-w-xs mt-2">
                Agregasi indikasi disinformasi berbasis percepatan persebaran akun dan potensi provokasi SARA.
              </p>
            </div>

            {/* 5W+1H Quick Extraction */}
            <div className="cyber-card p-5 rounded-xl space-y-3">
              <h3 className="text-sm font-bold text-white flex items-center gap-2">
                <Sparkles className="w-4 h-4 text-cyan-400" />
                Ekstraksi Intelijen 5W+1H
              </h3>
              <div className="space-y-2 text-xs">
                <div className="bg-slate-900/60 p-2 rounded border border-slate-800">
                  <span className="font-bold text-cyan-400">WHAT: </span>
                  <span className="text-slate-300">Disinformasi kebijakan & video daur ulang peristiwa lama.</span>
                </div>
                <div className="bg-slate-900/60 p-2 rounded border border-slate-800">
                  <span className="font-bold text-emerald-400">WHO: </span>
                  <span className="text-slate-300">Unit Pelayanan A, Lembaga Kesehatan B, Komunitas F.</span>
                </div>
                <div className="bg-slate-900/60 p-2 rounded border border-slate-800">
                  <span className="font-bold text-amber-400">WHERE: </span>
                  <span className="text-slate-300">Platform Instagram, TikTok, dan YouTube Shorts.</span>
                </div>
                <div className="bg-slate-900/60 p-2 rounded border border-slate-800">
                  <span className="font-bold text-violet-400">WHY & HOW: </span>
                  <span className="text-slate-300">Clickbait monetisasi engagement & fabrikasi narasi krisis.</span>
                </div>
              </div>
            </div>
          </div>

          {/* Trending Topics Table */}
          <div className="cyber-card rounded-xl p-5 space-y-4">
            <div className="flex items-center justify-between">
              <div>
                <h3 className="text-sm font-bold text-white flex items-center gap-2">
                  <Flame className="w-4 h-4 text-amber-400" />
                  Klaster Topik Paling Hangat Saat Ini
                </h3>
                <p className="text-[11px] text-slate-400 mt-0.5">
                  Topik dikelompokkan dengan cosine similarity & pembobotan kecepatan pertumbuhan.
                </p>
              </div>
              <Link
                to="/trending"
                className="text-xs font-semibold text-cyan-400 hover:text-cyan-300 flex items-center gap-1 transition-colors"
              >
                <span>Lihat Semua Topik</span>
                <ArrowRight className="w-3.5 h-3.5" />
              </Link>
            </div>

            {trendingStats?.latest_trending && trendingStats.latest_trending.length > 0 ? (
              <div className="overflow-x-auto">
                <table className="w-full text-left text-xs">
                  <thead className="bg-slate-900/80 text-slate-400 uppercase text-[10px] font-semibold tracking-wider border-b border-slate-800">
                    <tr>
                      <th className="py-2 px-3">Topik Isu</th>
                      <th className="py-2 px-3">Kategori Utama</th>
                      <th className="py-2 px-3">Konten Terdeteksi</th>
                      <th className="py-2 px-3">Skor Trending</th>
                      <th className="py-2 px-3 text-right">Detail</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-slate-800/60 font-mono">
                    {trendingStats.latest_trending.map((item: any) => (
                      <tr key={item.issue_id} className="hover:bg-slate-800/40 transition-colors">
                        <td className="py-2.5 px-3 font-sans font-bold text-slate-200">{item.title}</td>
                        <td className="py-2.5 px-3">
                          <span className="text-[10px] px-2 py-0.5 rounded bg-cyan-950 text-cyan-400 border border-cyan-800">
                            {item.main_category || 'UMUM'}
                          </span>
                        </td>
                        <td className="py-2.5 px-3 text-slate-300">{item.content_count} konten</td>
                        <td className="py-2.5 px-3 font-bold text-amber-400">{item.trending_score?.toFixed(1) || 0}</td>
                        <td className="py-2.5 px-3 text-right">
                          <Link
                            to={`/trending/${item.issue_id}`}
                            className="text-cyan-400 hover:text-cyan-300 text-xs font-sans font-semibold"
                          >
                            Buka Radar →
                          </Link>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            ) : (
              <div className="text-center py-8 text-slate-500 text-xs font-mono">
                Belum ada klaster topik trending.
              </div>
            )}
          </div>
        </div>
      )}
    </div>
  );
};
