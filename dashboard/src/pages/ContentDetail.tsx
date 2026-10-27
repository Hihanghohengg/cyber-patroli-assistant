import React, { useEffect, useState } from 'react';
import { useParams, Link } from 'react-router-dom';
import { apiClient } from '../api/client';
import { ContentDetail } from '../types';
import { PlatformBadge, RiskBadge, SentimentBadge, StatusBadge } from '../components/common/Badge';
import {
  ArrowLeft,
  ExternalLink,
  ShieldCheck,
  CheckCircle2,
  XCircle,
  Clock,
  Compass,
  AlertTriangle,
  Lock,
  Eye,
  ThumbsUp,
  MessageSquare,
  Share2,
  Camera,
} from 'lucide-react';

export const ContentDetailPage: React.FC = () => {
  const { id } = useParams<{ id: string }>();
  const [detail, setDetail] = useState<ContentDetail | null>(null);
  const [loading, setLoading] = useState<boolean>(true);
  const [error, setError] = useState<string | null>(null);
  const [imageError, setImageError] = useState<boolean>(false);

  // Form State for Human-in-the-Loop Validation
  const [validationDecision, setValidationDecision] = useState<'VALIDATED' | 'MODIFIED' | 'REJECTED'>('VALIDATED');
  const [riskOverride, setRiskOverride] = useState<string>('');
  const [categoryOverride, setCategoryOverride] = useState<string>('');
  const [analystNotes, setAnalystNotes] = useState<string>('');
  const [submitting, setSubmitting] = useState<boolean>(false);
  const [submitSuccessMsg, setSubmitSuccessMsg] = useState<string | null>(null);

  const fetchDetail = async () => {
    if (!id) return;
    try {
      setLoading(true);
      const data = await apiClient.contents.get(id);
      setDetail(data);
      if (data.ai_patrol?.risk_level) {
        setRiskOverride(data.ai_patrol.risk_level);
      }
      if (data.analysis_5w1h?.category) {
        setCategoryOverride(data.analysis_5w1h.category);
      }
    } catch (err) {
      setError('Gagal memuat detail forensik konten');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchDetail();
  }, [id]);

  const handleValidationSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!id) return;

    if ((validationDecision === 'MODIFIED' || validationDecision === 'REJECTED') && !analystNotes.trim()) {
      alert('Catatan analis wajib diisi untuk keputusan UBAH (MODIFIED) atau BUKAN PELANGGARAN (REJECTED).');
      return;
    }

    setSubmitting(true);
    setSubmitSuccessMsg(null);
    try {
      await apiClient.validation.validate(id, {
        status: validationDecision,
        notes: analystNotes.trim() || undefined,
        risk_level_override: validationDecision === 'REJECTED' ? undefined : (riskOverride || undefined),
        category_override: categoryOverride || undefined,
      });
      setSubmitSuccessMsg(`Validasi berhasil disimpan sebagai ${validationDecision}`);
      fetchDetail();
    } catch (err: any) {
      alert('Gagal menyimpan validasi: ' + (err.response?.data?.detail || err.message));
    } finally {
      setSubmitting(false);
    }
  };

  if (loading) {
    return (
      <div className="flex flex-col items-center justify-center min-h-[60vh] gap-3">
        <div className="w-10 h-10 border-2 border-cyan-400 border-t-transparent rounded-full animate-spin" />
        <span className="text-xs font-mono text-cyan-400">MEMUAT BUKTI DIGITAL & ANALISIS 5W+1H...</span>
      </div>
    );
  }

  if (error || !detail) {
    return (
      <div className="p-8 cyber-card rounded-xl text-center space-y-4">
        <AlertTriangle className="w-10 h-10 text-rose-400 mx-auto" />
        <h3 className="text-sm font-semibold text-rose-300">{error || 'Konten tidak ditemukan'}</h3>
        <Link to="/contents" className="inline-flex items-center gap-1.5 text-xs text-cyan-400 hover:underline">
          <ArrowLeft className="w-3.5 h-3.5" /> Kembali ke Penjelajah Konten
        </Link>
      </div>
    );
  }

  const { author, interaction, ai_patrol, analysis_5w1h, evidences, assigned_issue } = detail;
  const primaryEvidence = evidences.find((e) => e.source_type === 'POST_SCREENSHOT') || evidences[0];

  return (
    <div className="space-y-8">
      {/* Top Bar */}
      <div>
        <Link
          to="/contents"
          className="inline-flex items-center gap-1.5 text-xs font-semibold text-slate-400 hover:text-cyan-400 transition-colors"
        >
          <ArrowLeft className="w-4 h-4" />
          Kembali ke Penjelajah Konten
        </Link>
      </div>

      {/* Forensic Header */}
      <div className="cyber-card rounded-xl p-6">
        <div className="flex flex-col lg:flex-row lg:items-center justify-between gap-6">
          <div className="space-y-2">
            <div className="flex flex-wrap items-center gap-2">
              <PlatformBadge platform={detail.platform} />
              <StatusBadge status={detail.status} />
              {ai_patrol?.risk_level && <RiskBadge level={ai_patrol.risk_level} />}
              {ai_patrol?.ticket_number && (
                <span className="font-mono text-xs px-2 py-0.5 rounded bg-slate-900 text-cyan-400 border border-slate-800">
                  Tiket: {ai_patrol.ticket_number}
                </span>
              )}
            </div>

            <h1 className="text-xl font-bold text-white tracking-tight leading-snug">
              {detail.title || 'Konten Temuan Patroli Siber'}
            </h1>

            <div className="flex items-center gap-2 text-xs font-mono text-slate-400">
              <span className="text-slate-200">@{author.username || 'Anonim'}</span>
              <span>•</span>
              <a
                href={detail.url}
                target="_blank"
                rel="noreferrer"
                className="text-cyan-400 hover:underline flex items-center gap-1 truncate max-w-md"
              >
                {detail.url}
                <ExternalLink className="w-3 h-3" />
              </a>
            </div>

            {/* Engagement Stats */}
            <div className="flex items-center gap-4 text-xs font-mono text-slate-400 pt-2">
              <span className="flex items-center gap-1">
                <Eye className="w-3.5 h-3.5 text-slate-500" />
                {interaction.views_count?.toLocaleString() || 0} tayangan
              </span>
              <span className="flex items-center gap-1">
                <ThumbsUp className="w-3.5 h-3.5 text-slate-500" />
                {interaction.likes_count?.toLocaleString() || 0} suka
              </span>
              <span className="flex items-center gap-1">
                <MessageSquare className="w-3.5 h-3.5 text-slate-500" />
                {interaction.comments_count?.toLocaleString() || 0} komentar
              </span>
            </div>
          </div>

          {assigned_issue && (
            <div className="p-4 rounded-xl bg-slate-900/60 border border-slate-800 shrink-0 space-y-1">
              <span className="text-[10px] uppercase font-bold text-slate-400 tracking-wider">
                Klaster Topik Terkait
              </span>
              <div className="text-xs font-bold text-cyan-300">{assigned_issue.title}</div>
              <div className="text-[11px] text-slate-400 font-mono">
                Kategori: {assigned_issue.category} | Kemiripan: {(assigned_issue.similarity_score * 100).toFixed(1)}%
              </div>
              <Link
                to={`/trending/${assigned_issue.issue_id}`}
                className="text-xs text-cyan-400 hover:underline inline-block pt-1"
              >
                Lihat Dossier Topik →
              </Link>
            </div>
          )}
        </div>
      </div>

      {/* Evidence & AI Analysis Grid */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Visual Evidence Viewer */}
        <div className="cyber-card rounded-xl p-6 space-y-4">
          <div className="flex items-center justify-between">
            <h3 className="text-sm font-bold text-white flex items-center gap-2">
              <Lock className="w-4 h-4 text-cyan-400" />
              Tangkapan Layar Bukti Digital & Verifikasi SHA-256
            </h3>
            <span className="text-[10px] font-mono px-2 py-0.5 rounded bg-emerald-950/70 text-emerald-300 border border-emerald-500/30">
              INTEGRITAS TERVERIFIKASI
            </span>
          </div>

          <div className="relative aspect-video rounded-lg overflow-hidden bg-slate-950 border border-slate-800 flex items-center justify-center p-4">
            {imageError ? (
              <div className="flex flex-col items-center justify-center text-center space-y-2 p-4">
                <div className="w-12 h-12 rounded-full bg-slate-900 border border-slate-800 flex items-center justify-center text-slate-400">
                  <Camera className="w-6 h-6 text-cyan-400" />
                </div>
                <div className="text-xs font-semibold text-slate-200">
                  Tangkapan Layar Belum Ada di Disk
                </div>
                <p className="text-[11px] text-slate-500 font-mono max-w-sm">
                  URL postingan tercatat di antrean triase. Gunakan Ekstensi Browser atau jalankan worker scraping untuk menyimpan tangkapan visual.
                </p>
              </div>
            ) : (
              <img
                src={`/api/dashboard/contents/${detail.content_id}/screenshot`}
                alt="Bukti Visual Postingan"
                className="w-full h-full object-contain"
                onError={() => setImageError(true)}
              />
            )}
          </div>

          {primaryEvidence && (
            <div className="p-3 rounded-lg bg-slate-900/80 border border-slate-800 space-y-1.5 font-mono text-xs">
              <div className="flex items-center justify-between text-[11px] text-slate-400">
                <span>Tipe Bukti: {primaryEvidence.source_type}</span>
                <span>Format: {primaryEvidence.mime_type}</span>
              </div>
              <div className="text-[11px] text-slate-300 break-all bg-black/40 p-2 rounded border border-slate-800">
                <span className="text-cyan-400 font-bold">SHA-256: </span>
                {primaryEvidence.sha256}
              </div>
            </div>
          )}

          {/* Caption text */}
          <div className="space-y-1.5 pt-2">
            <h4 className="text-xs font-bold text-slate-300 uppercase tracking-wider">
              Teks Narasi / Caption Postingan:
            </h4>
            <div className="p-3 rounded-lg bg-slate-900/50 border border-slate-800/80 text-xs text-slate-300 max-h-36 overflow-y-auto whitespace-pre-wrap leading-relaxed">
              {detail.caption || '(Tidak ada teks caption)'}
            </div>
          </div>
        </div>

        {/* AI Patrol Analysis & Triase Card */}
        <div className="cyber-card rounded-xl p-6 space-y-5">
          <div className="flex items-center justify-between border-b border-slate-800 pb-3">
            <h3 className="text-sm font-bold text-white flex items-center gap-2">
              <ShieldCheck className="w-4 h-4 text-cyan-400" />
              Hasil Triase AI Intelijen Siber (Gemini)
            </h3>
            {ai_patrol?.confidence_score && (
              <span className="text-xs font-mono text-cyan-300">
                Keyakinan: {(ai_patrol.confidence_score * 100).toFixed(0)}%
              </span>
            )}
          </div>

          <div className="grid grid-cols-2 gap-3">
            <div className="p-3 rounded-lg bg-slate-900/60 border border-slate-800">
              <span className="text-[10px] text-slate-400 uppercase font-semibold">Status Keamanan</span>
              <div className="text-xs font-bold text-slate-100 mt-1">{ai_patrol?.status || 'N/A'}</div>
            </div>
            <div className="p-3 rounded-lg bg-slate-900/60 border border-slate-800">
              <span className="text-[10px] text-slate-400 uppercase font-semibold">Prediksi Label</span>
              <div className="text-xs font-bold text-cyan-300 mt-1">{ai_patrol?.predicted_label || 'N/A'}</div>
            </div>
          </div>

          <div className="space-y-1.5">
            <span className="text-xs font-bold text-slate-300 uppercase font-mono">Ringkasan Analisis AI</span>
            <p className="text-xs text-slate-300 leading-relaxed bg-slate-900/40 p-3 rounded-lg border border-slate-800">
              {ai_patrol?.summary || 'Belum ada ringkasan AI.'}
            </p>
          </div>

          {/* Reasoning Points */}
          {ai_patrol?.reasoning && (
            <div className="space-y-2">
              <span className="text-xs font-bold text-slate-300 uppercase font-mono">Poin Pertimbangan Analis AI:</span>
              <div className="text-xs text-slate-300 bg-slate-900/40 p-3 rounded-lg border border-slate-800 space-y-1.5 max-h-40 overflow-y-auto">
                {typeof ai_patrol.reasoning === 'object' ? (
                  Object.entries(ai_patrol.reasoning).map(([k, v]) => (
                    <div key={k} className="leading-relaxed">
                      <span className="font-semibold text-cyan-400">{k.replace(/_/g, ' ')}: </span>
                      <span>{Array.isArray(v) ? v.join(', ') : String(v)}</span>
                    </div>
                  ))
                ) : (
                  <div>{String(ai_patrol.reasoning)}</div>
                )}
              </div>
            </div>
          )}
        </div>
      </div>

      {/* 5W+1H Extraction Breakdown */}
      {analysis_5w1h && (
        <div className="cyber-card rounded-xl p-6 space-y-4">
          <div className="flex items-center justify-between border-b border-slate-800 pb-3">
            <h3 className="text-sm font-bold text-white flex items-center gap-2">
              <Compass className="w-4 h-4 text-cyan-400" />
              Struktur Intelijen 5W+1H Konten Ini
            </h3>
            <div className="flex items-center gap-2">
              <SentimentBadge sentiment={analysis_5w1h.sentiment} />
              <span className="px-2 py-0.5 rounded text-xs bg-slate-800 text-slate-300 font-mono">
                {analysis_5w1h.category}
              </span>
            </div>
          </div>

          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4 text-xs">
            <div className="p-3 bg-slate-900/60 rounded-lg border border-slate-800">
              <span className="font-mono font-bold text-cyan-400 uppercase">What (Isu):</span>
              <p className="mt-1 text-slate-200">{analysis_5w1h.what || '-'}</p>
            </div>
            <div className="p-3 bg-slate-900/60 rounded-lg border border-slate-800">
              <span className="font-mono font-bold text-cyan-400 uppercase">Who (Pihak):</span>
              <p className="mt-1 text-slate-200">{analysis_5w1h.who || '-'}</p>
            </div>
            <div className="p-3 bg-slate-900/60 rounded-lg border border-slate-800">
              <span className="font-mono font-bold text-cyan-400 uppercase">When (Waktu):</span>
              <p className="mt-1 text-slate-200">{analysis_5w1h.when_info || '-'}</p>
            </div>
            <div className="p-3 bg-slate-900/60 rounded-lg border border-slate-800">
              <span className="font-mono font-bold text-cyan-400 uppercase">Where (Tempat):</span>
              <p className="mt-1 text-slate-200">{analysis_5w1h.where_info || '-'}</p>
            </div>
            <div className="p-3 bg-slate-900/60 rounded-lg border border-slate-800">
              <span className="font-mono font-bold text-cyan-400 uppercase">Why (Penyebab):</span>
              <p className="mt-1 text-slate-200">{analysis_5w1h.why || '-'}</p>
            </div>
            <div className="p-3 bg-slate-900/60 rounded-lg border border-slate-800">
              <span className="font-mono font-bold text-cyan-400 uppercase">How (Perkembangan):</span>
              <p className="mt-1 text-slate-200">{analysis_5w1h.how || '-'}</p>
            </div>
          </div>
        </div>
      )}

      {/* Human-in-the-Loop Validation Form */}
      <div className="cyber-card rounded-xl p-6 border-cyan-500/30">
        <div className="flex items-center justify-between mb-4 border-b border-slate-800 pb-3">
          <div>
            <h3 className="text-sm font-bold text-white flex items-center gap-2">
              <ShieldCheck className="w-4 h-4 text-emerald-400" />
              Panel Validasi Human-in-the-Loop (Keputusan Analis Resmi)
            </h3>
            <p className="text-xs text-slate-400 mt-0.5">
              Setujui rekomendasi triase AI atau koreksi label jika terjadi kekeliruan klasifikasi.
            </p>
          </div>
          {submitSuccessMsg && (
            <span className="text-xs font-mono text-emerald-400 animate-pulse">
              {submitSuccessMsg}
            </span>
          )}
        </div>

        <form onSubmit={handleValidationSubmit} className="space-y-4">
          <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
            {/* Decision Radio */}
            {/* Decision Radio (3 Pilihan Proposal) */}
            <div className="space-y-1.5">
              <label className="text-xs font-semibold text-slate-300">Keputusan Validasi Analis</label>
              <div className="flex gap-2">
                <button
                  type="button"
                  onClick={() => setValidationDecision('VALIDATED')}
                  className={`flex-1 py-2 px-2.5 rounded-lg text-xs font-semibold flex items-center justify-center gap-1 transition-colors ${
                    validationDecision === 'VALIDATED'
                      ? 'bg-emerald-600 text-white border border-emerald-400 shadow-sm shadow-emerald-500/20'
                      : 'bg-slate-900 text-slate-400 border border-slate-800 hover:text-slate-200'
                  }`}
                >
                  <CheckCircle2 className="w-3.5 h-3.5 text-emerald-300" /> Setuju
                </button>
                <button
                  type="button"
                  onClick={() => setValidationDecision('MODIFIED')}
                  className={`flex-1 py-2 px-2.5 rounded-lg text-xs font-semibold flex items-center justify-center gap-1 transition-colors ${
                    validationDecision === 'MODIFIED'
                      ? 'bg-amber-600 text-white border border-amber-400 shadow-sm shadow-amber-500/20'
                      : 'bg-slate-900 text-slate-400 border border-slate-800 hover:text-slate-200'
                  }`}
                >
                  <AlertTriangle className="w-3.5 h-3.5 text-amber-300" /> Ubah
                </button>
                <button
                  type="button"
                  onClick={() => setValidationDecision('REJECTED')}
                  className={`flex-1 py-2 px-2.5 rounded-lg text-xs font-semibold flex items-center justify-center gap-1 transition-colors ${
                    validationDecision === 'REJECTED'
                      ? 'bg-rose-600 text-white border border-rose-400 shadow-sm shadow-rose-500/20'
                      : 'bg-slate-900 text-slate-400 border border-slate-800 hover:text-slate-200'
                  }`}
                >
                  <XCircle className="w-3.5 h-3.5 text-rose-300" /> Tolak
                </button>
              </div>
            </div>

            {/* Risk Override */}
            <div className="space-y-1.5">
              <label className="text-xs font-semibold text-slate-300">
                Penyesuaian Tingkat Risiko {validationDecision === 'REJECTED' && <span className="text-rose-400">(Dinonaktifkan)</span>}
              </label>
              <select
                disabled={validationDecision === 'REJECTED'}
                value={validationDecision === 'REJECTED' ? '' : riskOverride}
                onChange={(e) => setRiskOverride(e.target.value)}
                className="w-full bg-slate-900 border border-slate-800 rounded-lg py-2 px-3 text-xs text-slate-200 focus:outline-none focus:border-cyan-500 font-medium disabled:opacity-40 disabled:cursor-not-allowed"
              >
                {validationDecision === 'REJECTED' && <option value="">TIDAK_BERLAKU (NULL)</option>}
                <option value="RENDAH">RENDAH (Dampak Minimal)</option>
                <option value="SEDANG">SEDANG (Perlu Pemantauan)</option>
                <option value="TINGGI">TINGGI (Potensi Eskalasi Kritis)</option>
              </select>
            </div>

            {/* Category Override (Kategori Standar Proposal) */}
            <div className="space-y-1.5">
              <label className="text-xs font-semibold text-slate-300">Koreksi Kategori Pelanggaran</label>
              <select
                value={categoryOverride}
                onChange={(e) => setCategoryOverride(e.target.value)}
                className="w-full bg-slate-900 border border-slate-800 rounded-lg py-2 px-3 text-xs text-slate-200 focus:outline-none focus:border-cyan-500 font-medium"
              >
                <option value="HOAKS">HOAKS</option>
                <option value="DI_LUAR_KONTEKS">DI_LUAR_KONTEKS</option>
                <option value="UJARAN_KEBENCIAN">UJARAN_KEBENCIAN</option>
                <option value="PROVOKASI_SARA">PROVOKASI_SARA</option>
                <option value="Lainnya">Lainnya / Umum</option>
              </select>
            </div>
          </div>

          {/* Notes */}
          <div className="space-y-1.5">
            <label className="text-xs font-semibold text-slate-300">Catatan Koreksi Analis</label>
            <textarea
              rows={2}
              value={analystNotes}
              onChange={(e) => setAnalystNotes(e.target.value)}
              placeholder="Tambahkan catatan resmi analisis atau alasan penolakan jika diperlukan..."
              className="w-full bg-slate-900 border border-slate-800 rounded-lg p-3 text-xs text-slate-200 placeholder:text-slate-500 focus:outline-none focus:border-cyan-500"
            />
          </div>

          <div className="flex justify-end pt-2">
            <button
              type="submit"
              disabled={submitting}
              className="px-5 py-2.5 rounded-lg bg-gradient-to-r from-cyan-600 to-blue-600 hover:from-cyan-500 hover:to-blue-500 text-white font-bold text-xs shadow-lg shadow-cyan-500/20 transition-all disabled:opacity-50"
            >
              {submitting ? 'Menyimpan Validasi...' : 'Simpan Keputusan Validasi'}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
};
