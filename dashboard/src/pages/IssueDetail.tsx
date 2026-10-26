import React, { useEffect, useState } from 'react';
import { useParams, Link } from 'react-router-dom';
import { apiClient } from '../api/client';
import { TrendingDetail } from '../types';
import { ScoreGauge, TrendTimelineChart, DonutChart } from '../components/common/Charts';
import { PlatformBadge } from '../components/common/Badge';
import {
  ArrowLeft,
  Calendar,
  Layers,
  Users,
  Compass,
  FileQuestion,
  HelpCircle,
  Hash,
  ExternalLink,
  AlertTriangle,
  FileText,
} from 'lucide-react';

export const IssueDetailPage: React.FC = () => {
  const { id } = useParams<{ id: string }>();
  const [detail, setDetail] = useState<TrendingDetail | null>(null);
  const [loading, setLoading] = useState<boolean>(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const fetchDetail = async () => {
      if (!id) return;
      try {
        setLoading(true);
        const data = await apiClient.trending.get(id);
        setDetail(data);
      } catch (err) {
        setError('Gagal memuat dossier topik intelijen');
      } finally {
        setLoading(false);
      }
    };
    fetchDetail();
  }, [id]);

  if (loading) {
    return (
      <div className="flex flex-col items-center justify-center min-h-[60vh] gap-3">
        <div className="w-10 h-10 border-2 border-cyan-400 border-t-transparent rounded-full animate-spin" />
        <span className="text-xs font-mono text-cyan-400">MENYUSUN DOSSIER 5W+1H & GRAFIK TREN...</span>
      </div>
    );
  }

  if (error || !detail) {
    return (
      <div className="p-8 cyber-card rounded-xl text-center space-y-4">
        <AlertTriangle className="w-10 h-10 text-rose-400 mx-auto" />
        <h3 className="text-sm font-semibold text-rose-300">{error || 'Topik tidak ditemukan'}</h3>
        <Link to="/trending" className="inline-flex items-center gap-1.5 text-xs text-cyan-400 hover:underline">
          <ArrowLeft className="w-3.5 h-3.5" /> Kembali ke Radar Trending
        </Link>
      </div>
    );
  }

  const { issue, w5h1_summary, timeline, keywords, sources, platform_breakdown, sentiment_breakdown } = detail;

  // Platform items for Donut
  const platformColors: Record<string, string> = {
    youtube: '#ef4444',
    tiktok: '#06b6d4',
    instagram: '#ec4899',
    other: '#64748b',
  };
  const platformDonut = Object.entries(platform_breakdown).map(([plat, cnt]) => ({
    label: plat.toUpperCase(),
    count: cnt,
    color: platformColors[plat.toLowerCase()] || '#3b82f6',
  }));

  return (
    <div className="space-y-8">
      {/* Back button */}
      <div>
        <Link
          to="/trending"
          className="inline-flex items-center gap-1.5 text-xs font-semibold text-slate-400 hover:text-cyan-400 transition-colors"
        >
          <ArrowLeft className="w-4 h-4" />
          Kembali ke Radar Trending
        </Link>
      </div>

      {/* Header Banner */}
      <div className="cyber-card rounded-xl p-6 relative overflow-hidden">
        <div className="flex flex-col lg:flex-row lg:items-center justify-between gap-6">
          <div className="space-y-2">
            <div className="flex flex-wrap items-center gap-2">
              <span className="px-2.5 py-0.5 rounded text-xs font-semibold bg-cyan-950/80 text-cyan-400 border border-cyan-800/40 uppercase">
                {issue.category}
              </span>
              <span className="text-xs font-mono text-slate-400 px-2 py-0.5 rounded bg-slate-900 border border-slate-800">
                slug: {issue.canonical_name}
              </span>
              <span className="px-2 py-0.5 rounded-full text-[11px] font-semibold bg-emerald-500/10 text-emerald-400 border border-emerald-500/30">
                {issue.status}
              </span>
            </div>

            <h1 className="text-2xl font-bold text-white tracking-tight leading-snug">
              {issue.title}
            </h1>

            <p className="text-xs text-slate-300 max-w-3xl leading-relaxed">
              {detail.description || 'Tidak ada deskripsi tambahan.'}
            </p>

            <div className="flex flex-wrap items-center gap-4 text-xs font-mono text-slate-400 pt-2">
              <span className="flex items-center gap-1.5">
                <Calendar className="w-3.5 h-3.5 text-slate-500" />
                Pertama: {issue.first_seen_at ? new Date(issue.first_seen_at).toLocaleDateString('id-ID') : '-'}
              </span>
              <span className="flex items-center gap-1.5">
                <Calendar className="w-3.5 h-3.5 text-slate-500" />
                Terakhir: {issue.last_seen_at ? new Date(issue.last_seen_at).toLocaleDateString('id-ID') : '-'}
              </span>
              <span className="text-cyan-400 font-semibold">
                {issue.content_count} temuan konten
              </span>
            </div>
          </div>

          <div className="flex items-center gap-6 bg-slate-900/60 p-4 rounded-xl border border-slate-800 shrink-0">
            <div className="text-right">
              <div className="text-[10px] uppercase font-bold text-slate-400 tracking-wider">
                Trending Score
              </div>
              <div className="text-xs text-slate-400 font-mono mt-0.5">
                Pertumbuhan: <span className="text-emerald-400">+{issue.growth_rate}%</span>
              </div>
              <div className="text-xs text-slate-400 font-mono">
                Kecepatan: <span className="text-cyan-300">{issue.velocity}/jam</span>
              </div>
            </div>
            <ScoreGauge score={issue.trending_score} size={80} />
          </div>
        </div>
      </div>

      {/* 5W+1H Structured Dossier */}
      <div className="cyber-card rounded-xl p-6">
        <div className="flex items-center justify-between mb-4 border-b border-slate-800 pb-3">
          <div>
            <h3 className="text-sm font-bold text-white flex items-center gap-2">
              <Compass className="w-4 h-4 text-cyan-400" />
              Sintesis Ekstraksi 5W+1H (Gemini AI Multimodal)
            </h3>
            <p className="text-xs text-slate-400 mt-0.5">
              Ekstraksi berbasis bukti visual dan kontekstual. Informasi diverifikasi tanpa manipulasi fakta.
            </p>
          </div>
          <span className="text-[10px] font-mono px-2 py-1 rounded bg-slate-900 text-slate-400 border border-slate-800">
            BASIS: EKSPLISIT & INFERENSI
          </span>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
          <div className="p-4 rounded-lg bg-slate-900/60 border border-slate-800/80 space-y-1.5">
            <div className="text-xs font-bold text-cyan-400 flex items-center gap-1.5 uppercase font-mono">
              <HelpCircle className="w-3.5 h-3.5" /> WHAT (Apa Peristiwanya?)
            </div>
            <p className="text-xs text-slate-200 leading-relaxed">
              {w5h1_summary.what || 'Tidak disebutkan spesifik dalam data temuan.'}
            </p>
          </div>

          <div className="p-4 rounded-lg bg-slate-900/60 border border-slate-800/80 space-y-1.5">
            <div className="text-xs font-bold text-cyan-400 flex items-center gap-1.5 uppercase font-mono">
              <Users className="w-3.5 h-3.5" /> WHO (Siapa Pihak Terlibat?)
            </div>
            <p className="text-xs text-slate-200 leading-relaxed">
              {w5h1_summary.who || 'Tidak disebutkan spesifik dalam data temuan.'}
            </p>
          </div>

          <div className="p-4 rounded-lg bg-slate-900/60 border border-slate-800/80 space-y-1.5">
            <div className="text-xs font-bold text-cyan-400 flex items-center gap-1.5 uppercase font-mono">
              <Calendar className="w-3.5 h-3.5" /> WHEN (Kapan Terjadi?)
            </div>
            <p className="text-xs text-slate-200 leading-relaxed">
              {w5h1_summary.when_info || 'Tidak tertera eksplisit pada konten.'}
            </p>
          </div>

          <div className="p-4 rounded-lg bg-slate-900/60 border border-slate-800/80 space-y-1.5">
            <div className="text-xs font-bold text-cyan-400 flex items-center gap-1.5 uppercase font-mono">
              <Compass className="w-3.5 h-3.5" /> WHERE (Di Mana Lokasinya?)
            </div>
            <p className="text-xs text-slate-200 leading-relaxed">
              {w5h1_summary.where_info || 'Tidak tertera eksplisit pada konten.'}
            </p>
          </div>

          <div className="p-4 rounded-lg bg-slate-900/60 border border-slate-800/80 space-y-1.5">
            <div className="text-xs font-bold text-cyan-400 flex items-center gap-1.5 uppercase font-mono">
              <FileQuestion className="w-3.5 h-3.5" /> WHY (Mengapa Terjadi?)
            </div>
            <p className="text-xs text-slate-200 leading-relaxed">
              {w5h1_summary.why || 'Tidak dijelaskan penyebabnya secara eksplisit.'}
            </p>
          </div>

          <div className="p-4 rounded-lg bg-slate-900/60 border border-slate-800/80 space-y-1.5">
            <div className="text-xs font-bold text-cyan-400 flex items-center gap-1.5 uppercase font-mono">
              <Layers className="w-3.5 h-3.5" /> HOW (Bagaimana Perkembangannya?)
            </div>
            <p className="text-xs text-slate-200 leading-relaxed">
              {w5h1_summary.how || 'Kronologi narasi masih dalam proses pemantauan patroli.'}
            </p>
          </div>
        </div>
      </div>

      {/* Historical Timeline & Platform Breakdown Row */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Timeline Chart */}
        <div className="lg:col-span-2 cyber-card rounded-xl p-6 space-y-3">
          <div className="flex items-center justify-between">
            <h3 className="text-sm font-bold text-white">Grafik Perkembangan Skor Trending</h3>
            <span className="text-[11px] font-mono text-cyan-400">Snapshot Berkala</span>
          </div>
          <p className="text-xs text-slate-400">
            Pergerakan skor trending isu dari waktu ke waktu berdasarkan pembobotan otomatis engine.
          </p>
          <div className="pt-2">
            <TrendTimelineChart data={timeline} height={190} metric="trending_score" color="#00f0ff" />
          </div>
        </div>

        {/* Platform Breakdown */}
        <div className="cyber-card rounded-xl p-6 flex flex-col justify-between">
          <div>
            <h3 className="text-sm font-bold text-white mb-2">Sebaran Platform</h3>
            <p className="text-xs text-slate-400 mb-4">
              Komposisi kanal media sosial yang menyebarkan topik ini.
            </p>
          </div>
          <DonutChart items={platformDonut} centerLabel="Temuan" centerValue={issue.content_count} />
        </div>
      </div>

      {/* Keywords & Top Sources Row */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Keyword Cloud */}
        <div className="cyber-card rounded-xl p-6 space-y-4">
          <h3 className="text-sm font-bold text-white flex items-center gap-2">
            <Hash className="w-4 h-4 text-cyan-400" />
            Awan Kata Kunci & Tagar Relevan
          </h3>
          <div className="flex flex-wrap gap-2 pt-1">
            {keywords.length > 0 ? (
              keywords.map((kw, i) => (
                <span
                  key={i}
                  className="px-2.5 py-1 rounded-lg text-xs font-mono bg-slate-900 border border-slate-800 text-slate-300 hover:border-cyan-500/40 hover:text-cyan-300 transition-colors"
                >
                  #{kw.text} <span className="text-cyan-400 font-bold ml-1">({kw.value})</span>
                </span>
              ))
            ) : (
              <span className="text-xs text-slate-500 font-mono">Belum ada kata kunci terekstraksi</span>
            )}
          </div>
        </div>

        {/* Top Sources / Accounts */}
        <div className="cyber-card rounded-xl p-6 space-y-4">
          <h3 className="text-sm font-bold text-white flex items-center gap-2">
            <Users className="w-4 h-4 text-cyan-400" />
            Akun & Sumber Paling Aktif
          </h3>
          {sources.length > 0 ? (
            <div className="space-y-2">
              {sources.map((s, idx) => (
                <div
                  key={idx}
                  className="flex items-center justify-between p-2.5 rounded-lg bg-slate-900/60 border border-slate-800/80 text-xs"
                >
                  <div className="flex items-center gap-2">
                    <PlatformBadge platform={s.platform} />
                    <span className="font-semibold text-slate-200">@{s.source_name}</span>
                  </div>
                  <span className="font-mono text-cyan-400 font-semibold">{s.content_count} postingan</span>
                </div>
              ))}
            </div>
          ) : (
            <span className="text-xs text-slate-500 font-mono">Belum ada data sumber terindeks</span>
          )}
        </div>
      </div>
    </div>
  );
};
