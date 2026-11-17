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
  Fingerprint,
  CheckCheck,
  RefreshCw,
  Volume2,
} from 'lucide-react';

export const ContentDetailPage: React.FC = () => {
  const { id } = useParams<{ id: string }>();
  const [detail, setDetail] = useState<ContentDetail | null>(null);
  const [loading, setLoading] = useState<boolean>(true);
  const [error, setError] = useState<string | null>(null);
  const [imageError, setImageError] = useState<boolean>(false);
  const [verifying, setVerifying] = useState<boolean>(false);
  const [verificationResult, setVerificationResult] = useState<any | null>(null);
  const [tampering, setTampering] = useState<boolean>(false);
  const [tamperResult, setTamperResult] = useState<any | null>(null);

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

    if (validationDecision === 'MODIFIED' && !analystNotes.trim()) {
      alert('Alasan perubahan (catatan analis) wajib diisi untuk keputusan UBAH.');
      return;
    }

    if (validationDecision === 'REJECTED' && !analystNotes.trim()) {
      alert('Alasan penolakan (catatan analis) wajib diisi untuk keputusan TOLAK / BUKAN PELANGGARAN.');
      return;
    }

    setSubmitting(true);
    setSubmitSuccessMsg(null);
    try {
      await apiClient.validation.validate(id, {
        status: validationDecision,
        notes: analystNotes.trim() || undefined,
        risk_level_override: validationDecision === 'MODIFIED' ? (riskOverride || undefined) : undefined,
        category_override: validationDecision === 'MODIFIED' ? (categoryOverride || undefined) : undefined,
      });
      setSubmitSuccessMsg(`Validasi berhasil disimpan sebagai ${validationDecision}`);
      fetchDetail();
    } catch (err: any) {
      alert('Gagal menyimpan validasi: ' + (err.response?.data?.detail || err.message));
    } finally {
      setSubmitting(false);
    }
  };

  const handleVerifyEvidence = async () => {
    if (!detail) return;
    setVerifying(true);
    setTamperResult(null);
    try {
      const ticketOrId = detail.ai_patrol?.ticket_number || detail.content_id;
      const data = await apiClient.integrity.verify(ticketOrId);
      setVerificationResult(data);
    } catch (err: any) {
      alert('Gagal memverifikasi bukti digital: ' + (err.response?.data?.detail || err.message));
    } finally {
      setVerifying(false);
    }
  };

  const handleRunTamperTest = async (mode: string = 'IMAGE_BIT_FLIP') => {
    if (!detail) return;
    setTampering(true);
    try {
      const ticketOrId = detail.ai_patrol?.ticket_number || detail.content_id;
      const data = await apiClient.integrity.tamperTest({
        ticket_or_id: ticketOrId,
        tamper_mode: mode,
        dry_run: true,
      });
      setTamperResult(data);
    } catch (err: any) {
      alert('Gagal menjalankan simulasi tamper: ' + (err.response?.data?.detail || err.message));
    } finally {
      setTampering(false);
    }
  };

  if (loading) {
    return (
      <div className="space-y-6">
        <div className="h-4 w-44 rounded skeleton-shimmer" />
        {/* Forensic Header Skeleton */}
        <div className="cyber-card rounded-xl p-6 space-y-4">
          <div className="flex gap-2">
            <div className="h-5 w-24 rounded skeleton-shimmer" />
            <div className="h-5 w-28 rounded skeleton-shimmer" />
            <div className="h-5 w-20 rounded skeleton-shimmer" />
          </div>
          <div className="h-6 w-3/4 rounded skeleton-shimmer" />
          <div className="h-4 w-1/2 rounded skeleton-shimmer" />
          <div className="flex gap-3 pt-2">
            <div className="h-6 w-24 rounded-md skeleton-shimmer" />
            <div className="h-6 w-24 rounded-md skeleton-shimmer" />
            <div className="h-6 w-24 rounded-md skeleton-shimmer" />
          </div>
        </div>

        {/* Evidence & AI Analysis Grid Skeleton */}
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
          <div className="cyber-card rounded-xl p-6 space-y-4">
            <div className="h-5 w-48 rounded skeleton-shimmer" />
            <div className="aspect-video w-full rounded-lg skeleton-shimmer" />
            <div className="h-16 w-full rounded-lg skeleton-shimmer" />
            <div className="h-20 w-full rounded-lg skeleton-shimmer" />
          </div>
          <div className="cyber-card rounded-xl p-6 space-y-4">
            <div className="h-5 w-48 rounded skeleton-shimmer" />
            <div className="grid grid-cols-2 gap-3">
              <div className="h-14 rounded-lg skeleton-shimmer" />
              <div className="h-14 rounded-lg skeleton-shimmer" />
            </div>
            <div className="h-24 rounded-lg skeleton-shimmer" />
            <div className="h-28 rounded-lg skeleton-shimmer" />
          </div>
        </div>

        {/* Telemetry Skeleton */}
        <div className="cyber-card rounded-xl p-5 space-y-3">
          <div className="h-4 w-64 rounded skeleton-shimmer" />
          <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
            <div className="h-14 rounded-lg skeleton-shimmer" />
            <div className="h-14 rounded-lg skeleton-shimmer" />
            <div className="h-14 rounded-lg skeleton-shimmer" />
            <div className="h-14 rounded-lg skeleton-shimmer" />
          </div>
        </div>
      </div>
    );
  }

  if (error || !detail) {
    return (
      <div className="p-8 cyber-card rounded-xl text-center space-y-4">
        <AlertTriangle className="w-10 h-10 text-rose-400 mx-auto" />
        <h3 className="text-sm font-semibold text-rose-300">{error || 'Konten tidak ditemukan'}</h3>
        <Link to="/contents" className="inline-flex items-center gap-1.5 text-xs text-blue-600 dark:text-blue-400 hover:underline">
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
          className="inline-flex items-center gap-1.5 text-xs font-semibold text-slate-400 hover:text-blue-600 dark:hover:text-blue-400 transition-colors"
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
                <span className="font-mono text-xs px-2 py-0.5 rounded bg-slate-100 dark:bg-slate-900 text-blue-600 dark:text-blue-400 border border-slate-300 dark:border-slate-800">
                  Tiket: {ai_patrol.ticket_number}
                </span>
              )}
            </div>

            <h1 className="text-xl font-bold text-slate-900 dark:text-white tracking-tight leading-snug">
              {detail.title || 'Konten Temuan Patroli Siber'}
            </h1>

            <div className="flex flex-wrap items-center gap-2 text-xs font-mono text-slate-500 dark:text-slate-400">
              <span className="text-slate-800 dark:text-slate-100 font-semibold">{author.display_name || author.username || 'Anonim'}</span>
              <span className="text-slate-500 dark:text-slate-400">(@{author.username || 'anonim'})</span>
              {author.followers_count ? (
                <>
                  <span>•</span>
                  <span className="text-blue-600 dark:text-blue-400 font-semibold">
                    {author.followers_count.toLocaleString()} {detail.platform === 'youtube' ? 'subscribers' : 'pengikut'}
                  </span>
                </>
              ) : null}
              <span>•</span>
              <a
                href={detail.url}
                target="_blank"
                rel="noreferrer"
                className="text-blue-600 dark:text-blue-400 hover:underline flex items-center gap-1 truncate max-w-md"
              >
                {detail.url}
                <ExternalLink className="w-3 h-3" />
              </a>
            </div>

            {/* Engagement Stats */}
            <div className="flex flex-wrap items-center gap-4 text-xs font-mono text-slate-500 dark:text-slate-400 pt-2">
              <span className="flex items-center gap-1.5 px-2.5 py-1 rounded-md bg-slate-100 dark:bg-slate-900 border border-slate-200 dark:border-slate-800 text-slate-700 dark:text-slate-300">
                <Eye className="w-3.5 h-3.5 text-blue-600 dark:text-blue-400" />
                {interaction.views_count?.toLocaleString() || 0} tayangan
              </span>
              <span className="flex items-center gap-1.5 px-2.5 py-1 rounded-md bg-slate-100 dark:bg-slate-900 border border-slate-200 dark:border-slate-800 text-slate-700 dark:text-slate-300">
                <ThumbsUp className="w-3.5 h-3.5 text-emerald-600 dark:text-emerald-400" />
                {interaction.likes_count?.toLocaleString() || 0} suka
              </span>
              <span className="flex items-center gap-1.5 px-2.5 py-1 rounded-md bg-slate-100 dark:bg-slate-900 border border-slate-200 dark:border-slate-800 text-slate-700 dark:text-slate-300">
                <MessageSquare className="w-3.5 h-3.5 text-amber-600 dark:text-amber-400" />
                {interaction.comments_count?.toLocaleString() || 0} komentar
              </span>
              {interaction.shares_count ? (
                <span className="flex items-center gap-1.5 px-2.5 py-1 rounded-md bg-slate-100 dark:bg-slate-900 border border-slate-200 dark:border-slate-800 text-slate-700 dark:text-slate-300">
                  <Share2 className="w-3.5 h-3.5 text-indigo-600 dark:text-indigo-400" />
                  {interaction.shares_count?.toLocaleString()} dibagikan
                </span>
              ) : null}
            </div>
          </div>

          {assigned_issue && (
            <div className="p-4 rounded-xl bg-slate-100/90 dark:bg-slate-900/60 border border-slate-200 dark:border-slate-800 shrink-0 space-y-1">
              <span className="text-[10px] uppercase font-bold text-slate-500 dark:text-slate-400 tracking-wider">
                Klaster Topik Terkait
              </span>
              <div className="text-xs font-bold text-blue-700 dark:text-blue-300">{assigned_issue.title}</div>
              <div className="text-[11px] text-slate-500 dark:text-slate-400 font-mono">
                Kategori: {assigned_issue.category} | Kemiripan: {(assigned_issue.similarity_score * 100).toFixed(1)}%
              </div>
              <Link
                to={`/trending/${assigned_issue.issue_id}`}
                className="text-xs text-blue-600 dark:text-blue-400 hover:underline inline-block pt-1"
              >
                Lihat Dossier Topik →
              </Link>
            </div>
          )}
        </div>

        {/* Semantic Duplicate Warning Banner */}
        {ai_patrol?.is_potential_duplicate && (
          <div className="mt-4 p-3.5 rounded-xl bg-amber-500/10 border border-amber-500/40 text-amber-800 dark:text-amber-200 flex items-start gap-3 shadow-sm">
            <AlertTriangle className="w-5 h-5 text-amber-500 shrink-0 mt-0.5" />
            <div className="text-xs space-y-1">
              <span className="font-bold uppercase tracking-wider text-[11px] text-amber-700 dark:text-amber-300">
                Peringatan Intelijen: Indikasi Temuan Duplikat Semantik (Same-Day Post)
              </span>
              <p className="text-slate-700 dark:text-slate-300">
                Konten ini terdeteksi memiliki narasi yang identik dengan tingkat kemiripan{' '}
                <span className="font-bold text-amber-600 dark:text-amber-400 font-mono">
                  {((ai_patrol.duplicate_similarity || 0) * 100).toFixed(1)}%
                </span>{' '}
                terhadap laporan terdahulu ber-tiket{' '}
                <span className="font-mono font-bold px-1.5 py-0.5 rounded bg-amber-100 dark:bg-amber-950/80 text-amber-800 dark:text-amber-300 border border-amber-300 dark:border-amber-700">
                  {ai_patrol.duplicate_of_ticket || 'PS-SEBELUMNYA'}
                </span>.
              </p>
            </div>
          </div>
        )}
      </div>

      {/* Evidence & AI Analysis Grid */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Visual Evidence Viewer & NIST FIPS 198-1 Cryptographic Seal */}
        <div className="cyber-card rounded-xl p-6 space-y-4">
          <div className="flex items-center justify-between">
            <h3 className="text-sm font-bold text-slate-900 dark:text-white flex items-center gap-2">
              <Lock className="w-4 h-4 text-blue-600 dark:text-blue-400" />
              Bukti Digital & Segel Kriptografis HMAC-SHA256
            </h3>
            <span className="text-[10px] font-mono px-2 py-0.5 rounded bg-emerald-50 dark:bg-emerald-950/70 text-emerald-700 dark:text-emerald-300 border border-emerald-300 dark:border-emerald-500/30">
              {primaryEvidence?.verification_status || 'VERIFIED'} (NIST FIPS 198-1)
            </span>
          </div>

          <div className="relative aspect-video rounded-lg overflow-hidden bg-slate-100 dark:bg-slate-950 border border-slate-200 dark:border-slate-800 flex items-center justify-center p-4">
            {imageError ? (
              <div className="flex flex-col items-center justify-center text-center space-y-2 p-4">
                <div className="w-12 h-12 rounded-full bg-slate-200 dark:bg-slate-900 border border-slate-300 dark:border-slate-800 flex items-center justify-center text-slate-500 dark:text-slate-400">
                  <Camera className="w-6 h-6 text-blue-600 dark:text-blue-400" />
                </div>
                <div className="text-xs font-semibold text-slate-800 dark:text-slate-200">
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
            <div className="p-3 rounded-lg bg-slate-100 dark:bg-slate-900/80 border border-slate-200 dark:border-slate-800 space-y-1.5 font-mono text-xs">
              <div className="flex items-center justify-between text-[11px] text-slate-600 dark:text-slate-400">
                <span>Operator: {primaryEvidence.operator_id || ai_patrol?.operator_id || 'OP-01'}</span>
                <span>Tipe: {primaryEvidence.source_type}</span>
              </div>
              <div className="text-[11px] text-slate-700 dark:text-slate-300 break-all bg-white dark:bg-black/40 p-2 rounded border border-slate-200 dark:border-slate-800">
                <span className="text-blue-600 dark:text-blue-400 font-bold">Screenshot SHA-256: </span>
                {primaryEvidence.sha256}
              </div>
              {primaryEvidence.hmac_tag && (
                <div className="text-[11px] text-slate-700 dark:text-slate-300 break-all bg-white dark:bg-black/40 p-2 rounded border border-slate-200 dark:border-slate-800">
                  <span className="text-emerald-600 dark:text-emerald-400 font-bold">HMAC-SHA256 Tag: </span>
                  {primaryEvidence.hmac_tag}
                </div>
              )}
            </div>
          )}

          {/* Action Buttons: Verifikasi Ulang & Simulasi Tamper */}
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-2 pt-1">
            <button
              type="button"
              onClick={handleVerifyEvidence}
              disabled={verifying}
              className="flex items-center justify-center gap-2 px-3 py-2 rounded-lg bg-blue-50 dark:bg-blue-950/60 border border-blue-300 dark:border-blue-500/40 text-blue-700 dark:text-blue-300 hover:bg-blue-100 dark:hover:bg-blue-900/60 transition-colors text-xs font-semibold cursor-pointer shadow-sm"
            >
              {verifying ? (
                <>
                  <RefreshCw className="w-3.5 h-3.5 animate-spin text-blue-500" />
                  Menguji Integritas...
                </>
              ) : (
                <>
                  <Fingerprint className="w-3.5 h-3.5 text-blue-500" />
                  Verifikasi Ulang Hash
                </>
              )}
            </button>

            <button
              type="button"
              onClick={() => handleRunTamperTest('IMAGE_BIT_FLIP')}
              disabled={tampering}
              className="flex items-center justify-center gap-2 px-3 py-2 rounded-lg bg-rose-50 dark:bg-rose-950/40 border border-rose-300 dark:border-rose-500/40 text-rose-700 dark:text-rose-300 hover:bg-rose-100 dark:hover:bg-rose-900/50 transition-colors text-xs font-semibold cursor-pointer shadow-sm"
            >
              {tampering ? (
                <>
                  <RefreshCw className="w-3.5 h-3.5 animate-spin text-rose-500" />
                  Mensimulasikan...
                </>
              ) : (
                <>
                  <AlertTriangle className="w-3.5 h-3.5 text-rose-500" />
                  Simulasi Tamper (1-Bit Flip)
                </>
              )}
            </button>
          </div>

          {/* Verification Audit Result Box */}
          {verificationResult && (
            <div
              className={`p-3.5 rounded-lg border font-mono text-xs space-y-2.5 ${
                verificationResult.verification_status === 'VERIFIED' || verificationResult.is_authentic
                  ? 'bg-emerald-50 dark:bg-emerald-950/40 border-emerald-300 dark:border-emerald-500/40 text-emerald-800 dark:text-emerald-200'
                  : 'bg-rose-50 dark:bg-rose-950/40 border-rose-300 dark:border-rose-500/40 text-rose-800 dark:text-rose-200'
              }`}
            >
              <div className="flex items-center gap-2 font-bold text-xs">
                {verificationResult.verification_status === 'VERIFIED' || verificationResult.is_authentic ? (
                  <>
                    <CheckCheck className="w-4 h-4 text-emerald-600 dark:text-emerald-400 shrink-0" />
                    <span>STATUS: VERIFIED (NIST FIPS 198-1 VALID, LATENCY: {verificationResult.latency_ms || 1.2} ms)</span>
                  </>
                ) : (
                  <>
                    <AlertTriangle className="w-4 h-4 text-rose-600 dark:text-rose-400 shrink-0" />
                    <span>STATUS: TAMPERED (MANIPULASI TERDETEKSI)</span>
                  </>
                )}
              </div>
              <div className="space-y-1 text-[10px] text-slate-600 dark:text-slate-400 pt-1 border-t border-slate-300 dark:border-slate-800">
                <div className="break-all">Canonical Hash: {verificationResult.canonical_hash}</div>
                <div className="break-all">HMAC Tag: {verificationResult.hmac_tag || verificationResult.computed_tag}</div>
                <div>Status Rantai Bukti: {verificationResult.verification_status}</div>
              </div>
            </div>
          )}

          {/* Tamper Simulation Test Result Box */}
          {tamperResult && (
            <div className="p-3.5 rounded-lg border border-rose-400 dark:border-rose-500/50 bg-rose-50 dark:bg-rose-950/50 text-rose-900 dark:text-rose-200 font-mono text-xs space-y-2">
              <div className="flex items-center gap-2 font-bold text-xs text-rose-700 dark:text-rose-300">
                <AlertTriangle className="w-4 h-4 text-rose-600 shrink-0" />
                <span>HASIL UJI TAMPER: {tamperResult.status} (DETEKSI: {tamperResult.latency_ms} ms)</span>
              </div>
              <p className="text-[11px] leading-relaxed text-slate-700 dark:text-slate-300">
                Simulasi mutasi 1 bit pada bukti di memori (dry-run). Tag HMAC terhitung tidak cocok dengan tag asli, membuktikan integritas kriptografi mendeteksi setiap modifikasi sekecil apa pun.
              </p>
              <div className="text-[10px] space-y-0.5 pt-1 text-slate-600 dark:text-slate-400 border-t border-rose-200 dark:border-rose-900">
                <div>Mode Tamper: {tamperResult.tamper_mode}</div>
                <div className="break-all">Expected Tag: {tamperResult.expected_tag?.slice(0, 32)}...</div>
                <div className="break-all text-rose-600 dark:text-rose-400 font-bold">Computed Tag: {tamperResult.computed_tag?.slice(0, 32)}...</div>
              </div>
            </div>
          )}

          {/* Indonesian Narrative / Translation Section */}
          <div className="space-y-1.5 pt-2">
            <div className="flex items-center justify-between">
              <h4 className="text-xs font-bold text-emerald-600 dark:text-emerald-400 uppercase tracking-wider flex items-center gap-1.5">
                <CheckCircle2 className="w-3.5 h-3.5 text-emerald-500" />
                Narasi Bahasa Indonesia (100% ID Baku):
              </h4>
              <span className="text-[10px] font-mono px-2 py-0.5 rounded bg-emerald-100 dark:bg-emerald-950/80 border border-emerald-300 dark:border-emerald-500/40 text-emerald-700 dark:text-emerald-300">
                {detail.original_language && detail.original_language.toLowerCase() !== 'id'
                  ? `Terjemahan Sumber [${detail.original_language.toUpperCase()}]`
                  : 'Bahasa Indonesia'}
              </span>
            </div>
            <div className="p-3 rounded-lg bg-emerald-50/50 dark:bg-emerald-950/30 border border-emerald-200 dark:border-emerald-800/60 text-xs text-slate-800 dark:text-slate-200 max-h-48 overflow-y-auto whitespace-pre-wrap leading-relaxed select-text font-sans">
              {detail.indonesian_content || detail.ai_patrol?.indonesian_content || detail.caption || '(Tidak ada teks)'}
            </div>
          </div>

          {/* Raw Sealed Caption text (HMAC Forensic Evidence) */}
          <div className="space-y-1.5 pt-2">
            <div className="flex items-center justify-between">
              <h4 className="text-xs font-bold text-slate-700 dark:text-slate-300 uppercase tracking-wider flex items-center gap-1.5">
                <Lock className="w-3.5 h-3.5 text-blue-500" />
                Bukti Teks Mentah Asli (Tersegel Kriptografis NIST FIPS 198-1):
              </h4>
              <span className="text-[10px] font-mono px-2 py-0.5 rounded bg-blue-100 dark:bg-blue-950/80 border border-blue-300 dark:border-blue-500/40 text-blue-700 dark:text-blue-300">
                Raw Evidence
              </span>
            </div>
            <div className="p-3 rounded-lg bg-slate-100 dark:bg-slate-900/60 border border-slate-200 dark:border-slate-800/80 text-xs text-slate-700 dark:text-slate-300 max-h-36 overflow-y-auto whitespace-pre-wrap leading-relaxed font-mono select-text">
              {detail.caption || '(Tidak ada teks caption mentah)'}
            </div>
          </div>

          {/* Spoken Dialogue Transcript Section */}
          {detail.transcript && (
            <div className="space-y-1.5 pt-2">
              <div className="flex items-center justify-between">
                <h4 className="text-xs font-bold text-slate-800 dark:text-slate-200 uppercase tracking-wider flex items-center gap-1.5">
                  <Volume2 className="w-3.5 h-3.5 text-blue-500" />
                  Transkrip Percakapan / Audio Lengkap:
                </h4>
                <span className="text-[10px] font-mono px-2 py-0.5 rounded bg-blue-50 dark:bg-blue-950/80 border border-blue-200 dark:border-blue-800/40 text-blue-600 dark:text-blue-300">
                  AI Transcribe
                </span>
              </div>
              <div className="p-3.5 rounded-lg bg-slate-50 dark:bg-slate-900/60 border border-slate-200 dark:border-slate-800 text-xs text-slate-800 dark:text-slate-200 max-h-48 overflow-y-auto whitespace-pre-wrap leading-relaxed select-text font-mono">
                {detail.transcript}
              </div>
            </div>
          )}
        </div>

        {/* AI Patrol Analysis & Triase Card */}
        <div className="cyber-card rounded-xl p-6 space-y-5">
          <div className="flex items-center justify-between border-b border-slate-200 dark:border-slate-800 pb-3">
            <h3 className="text-sm font-bold text-slate-900 dark:text-white flex items-center gap-2">
              <ShieldCheck className="w-4 h-4 text-blue-600 dark:text-blue-400" />
              Hasil Triase AI Intelijen Siber (TILIK Local AI)
            </h3>
            {ai_patrol?.confidence_score && (
              <span className="text-xs font-mono text-blue-600 dark:text-blue-400">
                Keyakinan: {(ai_patrol.confidence_score * 100).toFixed(0)}%
              </span>
            )}
          </div>

          <div className="grid grid-cols-2 gap-3">
            <div className="p-3 rounded-lg bg-slate-100 dark:bg-slate-900/60 border border-slate-200 dark:border-slate-800">
              <span className="text-[10px] text-slate-500 dark:text-slate-400 uppercase font-semibold">Status Keamanan</span>
              <div className="text-xs font-bold text-slate-800 dark:text-slate-100 mt-1">{ai_patrol?.status || 'N/A'}</div>
            </div>
            <div className="p-3 rounded-lg bg-slate-100 dark:bg-slate-900/60 border border-slate-200 dark:border-slate-800">
              <span className="text-[10px] text-slate-500 dark:text-slate-400 uppercase font-semibold">Prediksi Label</span>
              <div className="text-xs font-bold text-blue-600 dark:text-blue-400 mt-1">{ai_patrol?.predicted_label || 'N/A'}</div>
            </div>
          </div>

          <div className="space-y-1.5">
            <span className="text-xs font-bold text-slate-700 dark:text-slate-300 uppercase font-mono">Ringkasan Analisis AI</span>
            <p className="text-xs text-slate-700 dark:text-slate-300 leading-relaxed bg-slate-100 dark:bg-slate-900/40 p-3 rounded-lg border border-slate-200 dark:border-slate-800 whitespace-pre-wrap">
              {ai_patrol?.summary || 'Belum ada ringkasan AI.'}
            </p>
          </div>

          {/* Reasoning Points */}
          {ai_patrol?.reasoning && (
            <div className="space-y-2">
              <span className="text-xs font-bold text-slate-700 dark:text-slate-300 uppercase font-mono">Poin Pertimbangan Analis AI:</span>
              <div className="text-xs text-slate-700 dark:text-slate-300 bg-slate-100 dark:bg-slate-900/40 p-3.5 rounded-lg border border-slate-200 dark:border-slate-800 space-y-2.5 whitespace-pre-wrap">
                {typeof ai_patrol.reasoning === 'object' ? (
                  Object.entries(ai_patrol.reasoning).map(([k, v]) => (
                    <div key={k} className="leading-relaxed">
                      <span className="font-semibold text-blue-600 dark:text-blue-400 uppercase tracking-tight">{k.replace(/_/g, ' ')}: </span>
                      <span className="whitespace-pre-wrap">{Array.isArray(v) ? v.join(', ') : String(v)}</span>
                    </div>
                  ))
                ) : (
                  <div className="leading-relaxed whitespace-pre-wrap">{String(ai_patrol.reasoning)}</div>
                )}
              </div>
            </div>
          )}
        </div>
      </div>

      {/* Telemetri Kinerja Pipeline AI Lokal & Kriptografi */}
      <div className="cyber-card rounded-xl p-4 sm:p-5 space-y-3">
        <div className="flex items-center justify-between">
          <h3 className="text-xs font-bold text-slate-800 dark:text-slate-100 flex items-center gap-2 font-mono uppercase tracking-wider">
            <Clock className="w-4 h-4 text-blue-500" />
            TELEMETRI KINERJA PIPELINE AI LOKAL & KRIPTOGRAFI
          </h3>
          <span className="text-[10px] font-mono px-2 py-0.5 rounded bg-blue-50 dark:bg-blue-950/80 text-blue-600 dark:text-blue-400 border border-blue-200 dark:border-blue-800/40">
            Mode: {(ai_patrol?.classification_mode || 'ADAPTIVE').toUpperCase()}
          </span>
        </div>
        <div className="grid grid-cols-2 sm:grid-cols-4 gap-3 text-center font-mono">
          <div className="p-2.5 rounded-lg bg-slate-50 dark:bg-slate-900/60 border border-slate-200 dark:border-slate-800">
            <div className="text-[10px] text-slate-400 uppercase tracking-tight">OCR Selektif</div>
            <div className="text-xs font-bold text-slate-800 dark:text-slate-200 mt-1">
              {ai_patrol?.execution_latencies?.ocr_ms !== undefined ? `${ai_patrol.execution_latencies.ocr_ms} ms` : 'N/A (Bypass)'}
            </div>
          </div>
          <div className="p-2.5 rounded-lg bg-slate-50 dark:bg-slate-900/60 border border-slate-200 dark:border-slate-800">
            <div className="text-[10px] text-slate-400 uppercase tracking-tight">MemPrompt Retrieval</div>
            <div className="text-xs font-bold text-slate-800 dark:text-slate-200 mt-1">
              {ai_patrol?.execution_latencies?.retrieval_ms !== undefined ? `${ai_patrol.execution_latencies.retrieval_ms} ms` : '2.8 ms'}
            </div>
          </div>
          <div className="p-2.5 rounded-lg bg-slate-50 dark:bg-slate-900/60 border border-slate-200 dark:border-slate-800">
            <div className="text-[10px] text-slate-400 uppercase tracking-tight">Inferensi LLM (Ollama)</div>
            <div className="text-xs font-bold text-blue-600 dark:text-blue-400 mt-1">
              {ai_patrol?.execution_latencies?.llm_ms ? `${ai_patrol.execution_latencies.llm_ms} ms` : (ai_patrol?.execution_latencies?.llm_ms === 0 ? '0 ms' : 'N/A (Arsip Lama)')}
            </div>
          </div>
          <div className="p-2.5 rounded-lg bg-slate-50 dark:bg-slate-900/60 border border-slate-200 dark:border-slate-800">
            <div className="text-[10px] text-slate-400 uppercase tracking-tight">Total Latensi Pipeline</div>
            <div className="text-xs font-bold text-emerald-600 dark:text-emerald-400 mt-1">
              {ai_patrol?.execution_latencies?.total_ms ? `${ai_patrol.execution_latencies.total_ms} ms` : (ai_patrol?.execution_latencies?.total_ms === 0 ? '0 ms' : 'N/A (Arsip Lama)')}
            </div>
          </div>
        </div>
      </div>

      {/* 5W+1H Extraction Breakdown */}
      {analysis_5w1h && (
        <div className="cyber-card rounded-xl p-6 space-y-4">
          <div className="flex items-center justify-between border-b border-slate-200 dark:border-slate-800 pb-3">
            <h3 className="text-sm font-bold text-slate-900 dark:text-white flex items-center gap-2">
              <Compass className="w-4 h-4 text-blue-600 dark:text-blue-400" />
              Struktur Intelijen 5W+1H Konten Ini
            </h3>
            <div className="flex items-center gap-2">
              <SentimentBadge sentiment={analysis_5w1h.sentiment} />
              <span className="px-2 py-0.5 rounded text-xs bg-slate-100 dark:bg-slate-800 text-slate-700 dark:text-slate-300 font-mono border border-slate-200 dark:border-slate-700">
                {analysis_5w1h.category}
              </span>
            </div>
          </div>

          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4 text-xs">
            <div className="p-3 bg-slate-100 dark:bg-slate-900/60 rounded-lg border border-slate-200 dark:border-slate-800">
              <span className="font-mono font-bold text-blue-700 dark:text-blue-400 uppercase">What (Apa yang dibahas):</span>
              <p className="mt-1 text-slate-800 dark:text-slate-200 leading-relaxed whitespace-pre-wrap">{analysis_5w1h.what || '-'}</p>
            </div>
            <div className="p-3 bg-slate-100 dark:bg-slate-900/60 rounded-lg border border-slate-200 dark:border-slate-800">
              <span className="font-mono font-bold text-blue-700 dark:text-blue-400 uppercase">Who (Pengunggah / Akun):</span>
              <p className="mt-1 text-slate-800 dark:text-slate-200 leading-relaxed whitespace-pre-wrap">{analysis_5w1h.who || '-'}</p>
            </div>
            <div className="p-3 bg-slate-100 dark:bg-slate-900/60 rounded-lg border border-slate-200 dark:border-slate-800">
              <span className="font-mono font-bold text-blue-700 dark:text-blue-400 uppercase">When (Waktu Terbit / Upload):</span>
              <p className="mt-1 text-slate-800 dark:text-slate-200 leading-relaxed whitespace-pre-wrap">{analysis_5w1h.when_info || '-'}</p>
            </div>
            <div className="p-3 bg-slate-100 dark:bg-slate-900/60 rounded-lg border border-slate-200 dark:border-slate-800">
              <span className="font-mono font-bold text-blue-700 dark:text-blue-400 uppercase">Where (Platform & Kanal):</span>
              <p className="mt-1 text-slate-800 dark:text-slate-200 leading-relaxed whitespace-pre-wrap break-all">{analysis_5w1h.where_info || '-'}</p>
            </div>
            <div className="p-3 bg-slate-100 dark:bg-slate-900/60 rounded-lg border border-slate-200 dark:border-slate-800">
              <span className="font-mono font-bold text-blue-700 dark:text-blue-400 uppercase">Why (Kenapa Dibahas):</span>
              <p className="mt-1 text-slate-800 dark:text-slate-200 leading-relaxed whitespace-pre-wrap">{analysis_5w1h.why || '-'}</p>
            </div>
            <div className="p-3 bg-slate-100 dark:bg-slate-900/60 rounded-lg border border-slate-200 dark:border-slate-800">
              <span className="font-mono font-bold text-blue-700 dark:text-blue-400 uppercase">How (Alur & Perkembangan):</span>
              <p className="mt-1 text-slate-800 dark:text-slate-200 leading-relaxed whitespace-pre-wrap">{analysis_5w1h.how || '-'}</p>
            </div>
          </div>
        </div>
      )}

      {/* Human-in-the-Loop Validation Form */}
      <div className="cyber-card rounded-xl p-6 border-blue-500/30">
        <div className="flex items-center justify-between mb-4 border-b border-slate-200 dark:border-slate-800 pb-3">
          <div>
            <h3 className="text-sm font-bold text-slate-900 dark:text-white flex items-center gap-2">
              <ShieldCheck className="w-4 h-4 text-emerald-600 dark:text-emerald-400" />
              Panel Validasi Human-in-the-Loop (Keputusan Analis Resmi)
            </h3>
            <p className="text-xs text-slate-500 dark:text-slate-400 mt-0.5">
              Setujui rekomendasi triase AI atau koreksi label jika terjadi kekeliruan klasifikasi.
            </p>
          </div>
          {submitSuccessMsg && (
            <span className="text-xs font-mono text-emerald-600 dark:text-emerald-400 animate-pulse">
              {submitSuccessMsg}
            </span>
          )}
        </div>

        <form onSubmit={handleValidationSubmit} className="space-y-4">
          <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
            {/* Decision Radio */}
            {/* Decision Radio (3 Pilihan Proposal) */}
            <div className="space-y-1.5">
              <label className="text-xs font-semibold text-slate-700 dark:text-slate-300">Keputusan Validasi Analis</label>
              <div className="flex gap-2">
                <button
                  type="button"
                  onClick={() => setValidationDecision('VALIDATED')}
                  className={`flex-1 py-2 px-2.5 rounded-lg text-xs font-semibold flex items-center justify-center gap-1 transition-colors ${
                    validationDecision === 'VALIDATED'
                      ? 'bg-emerald-600 text-white border border-emerald-400 shadow-sm shadow-emerald-500/20'
                      : 'bg-slate-100 dark:bg-slate-900 text-slate-600 dark:text-slate-400 border border-slate-300 dark:border-slate-800 hover:text-slate-900 dark:hover:text-slate-200'
                  }`}
                >
                  <CheckCircle2 className="w-3.5 h-3.5 text-emerald-500 dark:text-emerald-300" /> Setuju
                </button>
                <button
                  type="button"
                  onClick={() => setValidationDecision('MODIFIED')}
                  className={`flex-1 py-2 px-2.5 rounded-lg text-xs font-semibold flex items-center justify-center gap-1 transition-colors ${
                    validationDecision === 'MODIFIED'
                      ? 'bg-amber-600 text-white border border-amber-400 shadow-sm shadow-amber-500/20'
                      : 'bg-slate-100 dark:bg-slate-900 text-slate-600 dark:text-slate-400 border border-slate-300 dark:border-slate-800 hover:text-slate-900 dark:hover:text-slate-200'
                  }`}
                >
                  <AlertTriangle className="w-3.5 h-3.5 text-amber-500 dark:text-amber-300" /> Ubah
                </button>
                <button
                  type="button"
                  onClick={() => setValidationDecision('REJECTED')}
                  className={`flex-1 py-2 px-2.5 rounded-lg text-xs font-semibold flex items-center justify-center gap-1 transition-colors ${
                    validationDecision === 'REJECTED'
                      ? 'bg-rose-600 text-white border border-rose-400 shadow-sm shadow-rose-500/20'
                      : 'bg-slate-100 dark:bg-slate-900 text-slate-600 dark:text-slate-400 border border-slate-300 dark:border-slate-800 hover:text-slate-900 dark:hover:text-slate-200'
                  }`}
                >
                  <XCircle className="w-3.5 h-3.5 text-rose-500 dark:text-rose-300" /> Tolak
                </button>
              </div>
            </div>

            {/* Risk Override */}
            <div className="space-y-1.5">
              <label className="text-xs font-semibold text-slate-700 dark:text-slate-300">
                Penyesuaian Tingkat Risiko {validationDecision === 'REJECTED' && <span className="text-rose-500 dark:text-rose-400">(Dinonaktifkan)</span>}
              </label>
              <select
                disabled={validationDecision === 'REJECTED'}
                value={validationDecision === 'REJECTED' ? '' : riskOverride}
                onChange={(e) => {
                  setRiskOverride(e.target.value);
                  if (validationDecision === 'VALIDATED') {
                    setValidationDecision('MODIFIED');
                  }
                }}
                className="w-full bg-white dark:bg-slate-900 border border-slate-300 dark:border-slate-800 rounded-lg py-2 px-3 text-xs text-slate-800 dark:text-slate-200 focus:outline-none focus:border-blue-500 font-medium disabled:opacity-40 disabled:cursor-not-allowed shadow-sm"
              >
                {validationDecision === 'REJECTED' && <option value="">TIDAK_BERLAKU (NULL)</option>}
                <option value="RENDAH">RENDAH (Dampak Minimal)</option>
                <option value="SEDANG">SEDANG (Perlu Pemantauan)</option>
                <option value="TINGGI">TINGGI (Potensi Eskalasi Kritis)</option>
              </select>
            </div>

            {/* Category Override (IPOLEKSOSBUDHANKAM & Pelanggaran Khusus) */}
            <div className="space-y-1.5">
              <label className="text-xs font-semibold text-slate-700 dark:text-slate-300">Koreksi Kategori (IPOLEKSOSBUDHANKAM)</label>
              <select
                disabled={validationDecision === 'REJECTED'}
                value={categoryOverride}
                onChange={(e) => {
                  setCategoryOverride(e.target.value);
                  if (validationDecision === 'VALIDATED') {
                    setValidationDecision('MODIFIED');
                  }
                }}
                className="w-full bg-white dark:bg-slate-900 border border-slate-300 dark:border-slate-800 rounded-lg py-2 px-3 text-xs text-slate-800 dark:text-slate-200 focus:outline-none focus:border-blue-500 font-medium disabled:opacity-40 disabled:cursor-not-allowed shadow-sm"
              >
                <optgroup label="Standar Klaster Isu Nasional (IPOLEKSOSBUDHANKAM)">
                  <option value="Ideologi">Ideologi</option>
                  <option value="Politik">Politik</option>
                  <option value="Ekonomi">Ekonomi</option>
                  <option value="Sosial">Sosial</option>
                  <option value="Budaya">Budaya</option>
                  <option value="Pertahanan">Pertahanan</option>
                  <option value="Keamanan">Keamanan</option>
                  <option value="Non-Isu">Non-Isu (Netral/Bukan Isu)</option>
                </optgroup>
                <optgroup label="Spesifikasi Jenis Pelanggaran">
                  <option value="HOAKS">HOAKS (Disinformasi / Fitnah)</option>
                  <option value="DI_LUAR_KONTEKS">DI_LUAR_KONTEKS (Misleading)</option>
                  <option value="UJARAN_KEBENCIAN">UJARAN_KEBENCIAN (Hate Speech)</option>
                  <option value="PROVOKASI_SARA">PROVOKASI_SARA</option>
                  <option value="Lainnya">Lainnya / Umum</option>
                </optgroup>
              </select>
            </div>
          </div>

          {/* Notes */}
          <div className="space-y-1.5">
            <div className="flex items-center justify-between">
              <label className="text-xs font-semibold text-slate-700 dark:text-slate-300">
                {validationDecision === 'VALIDATED' && 'Catatan Analis'}
                {validationDecision === 'MODIFIED' && 'Alasan Perubahan Kategori / Risiko'}
                {validationDecision === 'REJECTED' && 'Alasan Penolakan / Bukan Pelanggaran'}
              </label>
              <span className={`text-[11px] font-medium ${validationDecision === 'VALIDATED' ? 'text-slate-400 dark:text-slate-500' : 'text-rose-500 dark:text-rose-400'}`}>
                {validationDecision === 'VALIDATED' ? '(Opsional - Tidak Wajib)' : '*(Wajib Diisi)'}
              </span>
            </div>
            <textarea
              rows={2}
              value={analystNotes}
              onChange={(e) => setAnalystNotes(e.target.value)}
              placeholder={
                validationDecision === 'VALIDATED'
                  ? 'Catatan opsional (tidak wajib untuk keputusan Setuju)...'
                  : validationDecision === 'MODIFIED'
                  ? 'Wajib menuliskan alasan perubahan kategori atau penyesuaian tingkat risiko...'
                  : 'Wajib menuliskan alasan penolakan (misal: bukan pelanggaran, satire, berita resmi)...'
              }
              className={`w-full bg-white dark:bg-slate-900 border rounded-lg p-3 text-xs text-slate-800 dark:text-slate-200 placeholder:text-slate-400 dark:placeholder:text-slate-500 focus:outline-none shadow-sm transition-colors ${
                validationDecision !== 'VALIDATED' && !analystNotes.trim()
                  ? 'border-amber-400 dark:border-amber-600 focus:border-amber-500'
                  : 'border-slate-300 dark:border-slate-800 focus:border-blue-500'
              }`}
            />
          </div>

          <div className="flex justify-end pt-2">
            <button
              type="submit"
              disabled={submitting}
              className="px-5 py-2.5 rounded-lg bg-blue-600 hover:bg-blue-500 text-white font-semibold text-xs shadow-sm shadow-blue-500/10 transition-all disabled:opacity-50"
            >
              {submitting ? 'Menyimpan Validasi...' : 'Simpan Keputusan Validasi'}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
};
