import React, { useEffect, useState } from 'react';
import { useParams, Link } from 'react-router-dom';
import { apiClient } from '../api/client';
import { ContentDetail } from '../types';
import { PlatformBadge, RiskBadge, StatusBadge, DalkontenBadge } from '../components/common/Badge';
import {
  ArrowLeft,
  ExternalLink,
  ShieldCheck,
  ShieldAlert,
  CheckCircle2,
  XCircle,
  AlertTriangle,
  Lock,
  Eye,
  Send,
  ThumbsUp,
  MessageSquare,
  Share2,
  Camera,
  Fingerprint,
  CheckCheck,
  Copy,
  Check,
  ChevronDown,
  ChevronUp,
  Volume2,
  Sparkles,
} from 'lucide-react';

interface ReasoningSection {
  title: string;
  content: string;
}

const parseAIReasoningString = (text: string): ReasoningSection[] => {
  if (!text || !text.trim()) return [];

  const sectionHeaders = [
    'Fakta vs Dugaan Tertulis:',
    'Penalaran Kausal (Karena-Maka):',
    'Penalaran Kausal:',
    'Alasan Penilaian:',
    'Analisis Dampak & Kerawanan:',
    'Analisis Dampak:',
    'Rekomendasi Verifikasi & Tindak Lanjut:',
    'Rekomendasi Tindak Lanjut:',
    'Indikasi Pelanggaran:',
  ];

  const pattern = new RegExp(
    `(?=(?:${sectionHeaders.map((h) => h.replace(/[.*+?^${}()|[\]\\]/g, '\\$&')).join('|')}))`,
    'i'
  );

  const rawBlocks = text.split(pattern).map((b) => b.trim()).filter(Boolean);
  const sections: ReasoningSection[] = [];

  for (const block of rawBlocks) {
    let matchedHeader = '';
    for (const h of sectionHeaders) {
      if (block.toLowerCase().startsWith(h.toLowerCase())) {
        matchedHeader = h;
        break;
      }
    }

    if (matchedHeader) {
      const title = matchedHeader.replace(/:$/, '').trim();
      const content = block.slice(matchedHeader.length).trim();
      if (content) {
        sections.push({ title, content });
      }
    } else if (sections.length > 0) {
      sections[sections.length - 1].content += ' ' + block;
    } else {
      sections.push({ title: 'Alasan Penilaian', content: block });
    }
  }

  // Deduplicate recommendations if both "Rekomendasi Verifikasi & Tindak Lanjut" and "Rekomendasi Tindak Lanjut" exist
  const uniqueSections: ReasoningSection[] = [];
  const seenTitles = new Set<string>();
  for (const sec of sections) {
    const normalizedKey = sec.title.toLowerCase().replace(/verifikasi\s*&\s*/, '');
    if (!seenTitles.has(normalizedKey)) {
      seenTitles.add(normalizedKey);
      uniqueSections.push(sec);
    }
  }

  return uniqueSections.length > 0 ? uniqueSections : [{ title: 'Alasan Penilaian', content: text }];
};

const parseAIReasoning = (rawReasoning: any): ReasoningSection[] => {
  if (!rawReasoning) return [];

  if (typeof rawReasoning === 'object' && !Array.isArray(rawReasoning)) {
    const values = Object.values(rawReasoning);
    for (const val of values) {
      if (typeof val === 'string' && (val.includes('Fakta vs Dugaan') || val.includes('Penalaran Kausal'))) {
        return parseAIReasoningString(val);
      }
    }

    const sections: ReasoningSection[] = [];
    for (const [k, v] of Object.entries(rawReasoning)) {
      if (!v) continue;
      const formattedTitle = k
        .replace(/_/g, ' ')
        .replace(/\b\w/g, (c) => c.toUpperCase());
      const formattedContent = Array.isArray(v) ? v.join(', ') : String(v);
      sections.push({
        title: formattedTitle,
        content: formattedContent,
      });
    }
    return sections;
  }

  return parseAIReasoningString(String(rawReasoning));
};

const formatNarrativeParagraphs = (rawText: string): string[] => {
  if (!rawText || !rawText.trim()) return [];
  let clean = rawText.trim();

  // 1. Bersihkan pemisah artefak OCR & audio dari tampilan narasi editorial utama
  if (clean.includes('[HASIL OCR')) {
    clean = clean.split(/\[HASIL OCR/i)[0].trim();
  }
  if (clean.includes('[TRANSKRIP AUDIO')) {
    clean = clean.split(/\[TRANSKRIP AUDIO/i)[0].trim();
  }

  // 2. Bersihkan non-breaking spaces dan zero-width artifacts
  clean = clean.replace(/[\u00a0\u200b]/g, ' ');

  // 3. Bersihkan tombol aksi di ekor naskah (Translate, Terjemahkan, Suka, dll.)
  for (let i = 0; i < 3; i++) {
    clean = clean
      .replace(
        /[\s·•\-_|/]*\b(?:Translate|Terjemahkan|Lihat terjemahan|See translation|View translation|Suka|Like|Balas|Reply|Bagikan|Share|Komentar|Comment|Quotes|Top View activity|New thread|Lihat lainnya)\b[\s]*$/gi,
        ''
      )
      .trim();
  }

  if (clean.includes('\n\n')) {
    return clean.split(/\n\s*\n/).map((p) => p.trim()).filter(Boolean);
  }
  if (clean.includes('\n')) {
    const lines = clean.split('\n').map((p) => p.trim()).filter(Boolean);
    if (lines.length > 1) return lines;
  }
  const sentences = clean.match(/[^.!?]+[.!?]+(?:\s+|$)|[^.!?]+$/g) || [clean];
  if (sentences.length <= 3) return [clean];
  const chunks: string[] = [];
  for (let i = 0; i < sentences.length; i += 3) {
    chunks.push(sentences.slice(i, i + 3).join(' ').trim());
  }
  return chunks.filter(Boolean);
};

export const ContentDetailPage: React.FC = () => {
  const { id } = useParams<{ id: string }>();
  const [detail, setDetail] = useState<ContentDetail | null>(null);
  const [loading, setLoading] = useState<boolean>(true);
  const [error, setError] = useState<string | null>(null);
  const [imageError, setImageError] = useState<boolean>(false);

  // Progressive Disclosure: Raw evidence accordion
  const [showRawText, setShowRawText] = useState<boolean>(false);
  const [copiedHash, setCopiedHash] = useState<string | null>(null);

  // Form State for Human-in-the-Loop Validation
  const [validationDecision, setValidationDecision] = useState<'VALIDATED' | 'MODIFIED' | 'REJECTED'>('VALIDATED');
  const [riskOverride, setRiskOverride] = useState<string>('');
  const [categoryOverride, setCategoryOverride] = useState<string>('');
  const [analystNotes, setAnalystNotes] = useState<string>('');
  const [submitting, setSubmitting] = useState<boolean>(false);
  const [submitSuccessMsg, setSubmitSuccessMsg] = useState<string | null>(null);

  // Tim Dalkonten Forwarding State
  const [updatingDalkonten, setUpdatingDalkonten] = useState<boolean>(false);
  const [dalkontenMsg, setDalkontenMsg] = useState<string | null>(null);

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

  const copyToClipboard = (text: string, fieldId: string) => {
    navigator.clipboard.writeText(text);
    setCopiedHash(fieldId);
    setTimeout(() => setCopiedHash(null), 2000);
  };

  const handleValidationSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!id) return;

    if (validationDecision === 'MODIFIED' && !analystNotes.trim()) {
      alert('Alasan perubahan (catatan analis) wajib diisi untuk keputusan UBAH.');
      return;
    }

    if (validationDecision === 'REJECTED' && !analystNotes.trim()) {
      alert('Alasan penolakan (catatan analis) wajib diisi untuk keputusan TOLAK.');
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
      setSubmitSuccessMsg(`Validasi berhasil disimpan (${validationDecision})`);
      fetchDetail();
    } catch (err: any) {
      alert('Gagal menyimpan validasi: ' + (err.response?.data?.detail || err.message));
    } finally {
      setSubmitting(false);
    }
  };

  const handleDalkontenStatus = async (targetStatus: string) => {
    const reportIdentifier = detail?.report_id || detail?.content_id || id;
    if (!reportIdentifier) return;

    setUpdatingDalkonten(true);
    setDalkontenMsg(null);
    try {
      await apiClient.reports.updateDalkontenStatus(reportIdentifier, targetStatus);
      setDalkontenMsg(`Status Dalkonten berhasil diubah: ${targetStatus}`);
      fetchDetail();
    } catch (err: any) {
      alert('Gagal memperbarui status Dalkonten: ' + (err.response?.data?.detail || err.message));
    } finally {
      setUpdatingDalkonten(false);
    }
  };

  if (loading) {
    return (
      <div className="space-y-5">
        <div className="h-4 w-32 rounded skeleton-shimmer" />
        <div className="cyber-card rounded-xl p-5 space-y-3">
          <div className="h-5 w-48 rounded skeleton-shimmer" />
          <div className="h-4 w-72 rounded skeleton-shimmer" />
        </div>
        <div className="grid grid-cols-1 lg:grid-cols-12 gap-5">
          <div className="lg:col-span-7 cyber-card rounded-xl p-5 space-y-3">
            <div className="aspect-video w-full rounded-lg skeleton-shimmer" />
            <div className="h-16 rounded skeleton-shimmer" />
          </div>
          <div className="lg:col-span-5 cyber-card rounded-xl p-5 space-y-3">
            <div className="h-24 rounded skeleton-shimmer" />
            <div className="h-32 rounded skeleton-shimmer" />
          </div>
        </div>
      </div>
    );
  }

  if (error || !detail) {
    return (
      <div className="p-8 cyber-card rounded-xl text-center space-y-3">
        <AlertTriangle className="w-8 h-8 text-rose-500 mx-auto" />
        <h3 className="text-sm font-semibold text-rose-400 font-mono">{error || 'Konten tidak ditemukan'}</h3>
        <Link to="/contents" className="inline-flex items-center gap-1.5 text-xs text-blue-500 hover:underline font-mono">
          <ArrowLeft className="w-3.5 h-3.5" /> Kembali ke Arsip
        </Link>
      </div>
    );
  }

  const { author, interaction, ai_patrol, analysis_5w1h, evidences, assigned_issue } = detail;
  const bluf = (ai_patrol as any)?.bluf_dossier ||
    (typeof ai_patrol?.reasoning === 'object' ? (ai_patrol?.reasoning as any)?.bluf_dossier : null);
  const primaryEvidence = evidences.find((e) => e.source_type === 'POST_SCREENSHOT') || evidences[0];

  const sha256Short = primaryEvidence?.sha256
    ? `${primaryEvidence.sha256.slice(0, 10)}...${primaryEvidence.sha256.slice(-8)}`
    : null;

  const hmacShort = primaryEvidence?.hmac_tag
    ? `${primaryEvidence.hmac_tag.slice(0, 10)}...${primaryEvidence.hmac_tag.slice(-8)}`
    : null;

  return (
    <div className="space-y-5 pb-12">
      {/* ── 1. TOP NAV BREADCRUMB & KICKER ── */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2 border-b border-slate-200 dark:border-white/[0.06] pb-3">
        <div className="flex items-center gap-2.5">
          <Link
            to="/contents"
            className="inline-flex items-center gap-1.5 text-xs font-semibold text-slate-500 hover:text-slate-900 dark:hover:text-white transition-colors font-mono"
          >
            <ArrowLeft className="w-3.5 h-3.5" />
            Kembali ke Arsip
          </Link>
          <span className="text-slate-300 dark:text-slate-700 font-mono text-xs">•</span>
          <span className="font-mono text-[10px] tracking-widest text-blue-600 dark:text-blue-400 font-bold uppercase">
            DOSSIER ANALISIS // TILIK
          </span>
        </div>

        {ai_patrol?.ticket_number && (
          <span className="font-mono text-xs px-2.5 py-0.5 rounded bg-slate-100 dark:bg-white/[0.04] text-slate-700 dark:text-slate-300 border border-slate-200 dark:border-white/[0.08] self-start sm:self-auto">
            Tiket: <strong>{ai_patrol.ticket_number}</strong>
          </span>
        )}
      </div>

      {/* ── 2. METADATA HEADER COMPACT ── */}
      <div className="cyber-card rounded-xl p-4 sm:p-5 space-y-3">
        <div className="flex flex-col lg:flex-row lg:items-center justify-between gap-4">
          <div className="space-y-1.5 flex-1 min-w-0">
            <div className="flex items-center gap-2 flex-wrap">
              <PlatformBadge platform={detail.platform} />
              <StatusBadge status={detail.status} />
              {ai_patrol?.risk_level && <RiskBadge level={ai_patrol.risk_level} />}
            </div>

            <h1 className="text-base sm:text-lg font-bold text-slate-900 dark:text-white tracking-tight leading-snug">
              {detail.title || 'Konten Temuan Patroli Siber'}
            </h1>

            <div className="flex items-center gap-2 text-xs font-mono text-slate-500 dark:text-slate-400 flex-wrap">
              <span className="text-slate-800 dark:text-slate-200 font-medium">
                @{author.username || 'anonim'}
              </span>
              <span>•</span>
              <a
                href={detail.url}
                target="_blank"
                rel="noreferrer"
                className="text-blue-500 hover:underline inline-flex items-center gap-1 truncate max-w-xs sm:max-w-md"
              >
                {detail.url}
                <ExternalLink className="w-3 h-3 shrink-0" />
              </a>
            </div>
          </div>

          {/* Social Stats Strip */}
          <div className="flex items-center gap-3 text-xs font-mono text-slate-500 dark:text-slate-400 shrink-0">
            <span className="flex items-center gap-1">
              <Eye className="w-3.5 h-3.5 text-blue-500" />
              {interaction.views_count?.toLocaleString() || 0}
            </span>
            <span className="flex items-center gap-1">
              <ThumbsUp className="w-3.5 h-3.5 text-emerald-500" />
              {interaction.likes_count?.toLocaleString() || 0}
            </span>
            <span className="flex items-center gap-1">
              <MessageSquare className="w-3.5 h-3.5 text-amber-500" />
              {interaction.comments_count?.toLocaleString() || 0}
            </span>
            {interaction.shares_count ? (
              <span className="flex items-center gap-1">
                <Share2 className="w-3.5 h-3.5 text-indigo-400" />
                {interaction.shares_count.toLocaleString()}
              </span>
            ) : null}
          </div>
        </div>

        {/* Semantic Duplicate Warning */}
        {ai_patrol?.is_potential_duplicate && (
          <div className="p-3 rounded-lg bg-amber-500/10 border border-amber-500/30 text-amber-500 text-xs flex items-center justify-between font-mono">
            <div className="flex items-center gap-2">
              <AlertTriangle className="w-4 h-4 shrink-0" />
              <span>
                Indikasi Duplikat Semantik ({((ai_patrol.duplicate_similarity || 0) * 100).toFixed(0)}% mirip tiket {ai_patrol.duplicate_of_ticket || 'sebelumnya'})
              </span>
            </div>
          </div>
        )}
      </div>

      {/* ── 3. ASYMMETRIC GRID (7:5) DOSSIER ── */}
      <div className="grid grid-cols-1 lg:grid-cols-12 gap-5 items-start">
        {/* ══════════════════════════════════════════════════════════════
           KOLOM KIRI (7 Kolom) — BUKTI DIGITAL & NARASI
           ══════════════════════════════════════════════════════════════ */}
        <div className="lg:col-span-7 space-y-4">
          {/* Card: Bukti Visual & Segel Kriptografi */}
          <div className="cyber-card rounded-xl p-4 sm:p-5 space-y-3.5">
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-2">
                <Lock className="w-4 h-4 text-blue-500" />
                <h3 className="text-xs font-bold text-slate-800 dark:text-slate-100 uppercase tracking-wider font-mono">
                  Bukti Visual & Segel Kriptografi
                </h3>
              </div>
              <span className="text-[10px] font-mono px-2 py-0.5 rounded bg-emerald-500/10 text-emerald-500 border border-emerald-500/20 font-semibold">
                {primaryEvidence?.verification_status || 'VERIFIED'} (NIST FIPS 198-1)
              </span>
            </div>

            {/* Screenshot Frame */}
            <div className="relative aspect-video rounded-lg overflow-hidden bg-slate-900 border border-slate-200 dark:border-white/[0.08] flex items-center justify-center p-2">
              {imageError ? (
                <div className="text-center p-4 text-slate-400 font-mono text-xs space-y-1">
                  <Camera className="w-6 h-6 mx-auto opacity-50" />
                  <div>Tangkapan Layar Belum Ada</div>
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

            {/* Metadata Segel Kriptografi (Tracking & Hash Verification) */}
            {primaryEvidence && (
              <div className="p-3 rounded-lg bg-slate-50 dark:bg-[#0A0D14] border border-slate-200 dark:border-white/[0.06] space-y-2 font-mono text-xs">
                {/* Status Segel */}
                <div className="flex items-center justify-between text-slate-600 dark:text-slate-300 pb-1.5 border-b border-slate-200/60 dark:border-white/[0.04]">
                  <span className="text-[10.5px] text-slate-400 uppercase tracking-wider">Status Integritas:</span>
                  <span className="text-[11px] font-semibold text-emerald-500 dark:text-emerald-400 flex items-center gap-1.5">
                    <CheckCheck className="w-3.5 h-3.5" />
                    <span>NIST FIPS 198-1 ({primaryEvidence.verification_status || 'VERIFIED'})</span>
                  </span>
                </div>

                {/* SHA-256 Pill */}
                <div className="flex items-center justify-between text-slate-600 dark:text-slate-300">
                  <span className="text-[10.5px] text-slate-400 uppercase tracking-wider">SHA-256:</span>
                  <div className="flex items-center gap-1.5">
                    <span className="text-[11px] font-semibold text-blue-500 dark:text-blue-400">{sha256Short}</span>
                    <button
                      type="button"
                      onClick={() => copyToClipboard(primaryEvidence.sha256, 'sha256')}
                      className="p-1 rounded hover:bg-slate-100 dark:hover:bg-white/[0.08] text-slate-400 hover:text-slate-800 dark:hover:text-white transition-colors"
                      title="Salin SHA-256 Lengkap"
                    >
                      {copiedHash === 'sha256' ? <Check className="w-3 h-3 text-emerald-500" /> : <Copy className="w-3 h-3" />}
                    </button>
                  </div>
                </div>

                {/* HMAC Tag Pill */}
                {primaryEvidence.hmac_tag && (
                  <div className="flex items-center justify-between text-slate-600 dark:text-slate-300">
                    <span className="text-[10.5px] text-slate-400 uppercase tracking-wider">HMAC Tag:</span>
                    <div className="flex items-center gap-1.5">
                      <span className="text-[11px] font-semibold text-emerald-500 dark:text-emerald-400">{hmacShort}</span>
                      <button
                        type="button"
                        onClick={() => copyToClipboard(primaryEvidence.hmac_tag!, 'hmac')}
                        className="p-1 rounded hover:bg-slate-100 dark:hover:bg-white/[0.08] text-slate-400 hover:text-slate-800 dark:hover:text-white transition-colors"
                        title="Salin HMAC Tag Lengkap"
                      >
                        {copiedHash === 'hmac' ? <Check className="w-3 h-3 text-emerald-500" /> : <Copy className="w-3 h-3" />}
                      </button>
                    </div>
                  </div>
                )}
              </div>
            )}
          </div>

          {/* Card: Narasi Bahasa Indonesia (Editorial Typography with Paragraph Spacing) */}
          <div className="cyber-card rounded-xl p-4 sm:p-5 space-y-3">
            <div className="flex items-center justify-between">
              <h4 className="text-xs font-bold text-slate-800 dark:text-slate-100 uppercase tracking-wider font-mono flex items-center gap-1.5">
                <CheckCircle2 className="w-3.5 h-3.5 text-emerald-500" />
                Narasi Bahasa Indonesia
              </h4>
              <span className="text-[10px] font-mono px-2 py-0.5 rounded bg-slate-100 dark:bg-white/[0.04] text-slate-500 dark:text-slate-400">
                {detail.original_language && detail.original_language.toLowerCase() !== 'id'
                  ? `Terjemahan [${detail.original_language.toUpperCase()}]`
                  : 'Bahasa Indonesia'}
              </span>
            </div>

            <div className="space-y-3 text-[13px] leading-[1.7] text-slate-700 dark:text-slate-300 select-text font-sans pt-1">
              {formatNarrativeParagraphs(
                detail.indonesian_content || detail.ai_patrol?.indonesian_content || detail.caption || ''
              ).length > 0 ? (
                formatNarrativeParagraphs(
                  detail.indonesian_content || detail.ai_patrol?.indonesian_content || detail.caption || ''
                ).map((para, idx) => (
                  <p key={idx} className="whitespace-normal break-words">
                    {para}
                  </p>
                ))
              ) : (
                <p className="italic text-slate-400">(Tidak ada narasi teks)</p>
              )}
            </div>
          </div>

          {/* Accordion: Bukti Teks Mentah / OCR */}
          {(() => {
            const rawOcr = detail.evidences?.find((e) => e.ocr_text && e.ocr_text.trim())?.ocr_text?.trim() || '';
            const rawCaption = detail.caption || '';
            const isOcr = Boolean(rawOcr);
            const displaySnippet = isOcr ? rawOcr : rawCaption;
            const charCount = displaySnippet.length;
            const titleLabel = isOcr
              ? `Bukti Teks Mentah OCR (${charCount} Karakter)`
              : `Naskah Asli Peramban (${charCount} Karakter)`;

            return (
              <div className="cyber-card rounded-xl overflow-hidden">
                <button
                  type="button"
                  onClick={() => setShowRawText(!showRawText)}
                  className="w-full p-3.5 flex items-center justify-between text-xs font-mono font-semibold text-slate-600 dark:text-slate-400 hover:text-slate-900 dark:hover:text-slate-200 transition-colors"
                >
                  <span className="flex items-center gap-2">
                    <Lock className="w-3.5 h-3.5 text-blue-500" />
                    {titleLabel}
                  </span>
                  {showRawText ? <ChevronUp className="w-4 h-4" /> : <ChevronDown className="w-4 h-4" />}
                </button>

                {showRawText && (
                  <div className="p-3.5 pt-0 border-t border-slate-100 dark:border-white/[0.06]">
                    <div className="p-3 rounded-lg bg-slate-50 dark:bg-[#0A0D14] text-xs font-mono text-slate-600 dark:text-slate-400 max-h-48 overflow-y-auto whitespace-pre-wrap select-text leading-relaxed">
                      {displaySnippet || '(Tidak ada teks mentah / OCR dilewati karena naskah DOM memadai)'}
                    </div>
                  </div>
                )}
              </div>
            );
          })()}

          {/* Transkrip Percakapan Audio (Jika Ada) */}
          {detail.transcript && (
            <div className="cyber-card rounded-xl p-4 space-y-2">
              <h4 className="text-xs font-bold text-slate-800 dark:text-slate-100 uppercase tracking-wider font-mono flex items-center gap-1.5">
                <Volume2 className="w-3.5 h-3.5 text-blue-500" />
                Transkrip Audio / Percakapan
              </h4>
              <div className="p-3 rounded-lg bg-slate-50 dark:bg-[#0A0D14] text-xs font-mono text-slate-700 dark:text-slate-300 max-h-40 overflow-y-auto whitespace-pre-wrap">
                {detail.transcript}
              </div>
            </div>
          )}
        </div>

        {/* ══════════════════════════════════════════════════════════════
           KOLOM KANAN (5 Kolom) — INTELIJEN & KEPUTUSAN ANALIS
           ══════════════════════════════════════════════════════════════ */}
        <div className="lg:col-span-5 space-y-4">
          {/* Card: Verdict Header & Ringkasan Eksekutif */}
          <div className="cyber-card rounded-xl p-4 sm:p-5 space-y-3.5">
            <div className="flex items-center justify-between border-b border-slate-100 dark:border-white/[0.06] pb-3">
              <h3 className="text-xs font-bold text-slate-800 dark:text-slate-100 uppercase tracking-wider font-mono flex items-center gap-2">
                <ShieldCheck className="w-4 h-4 text-blue-500" />
                Triase Intelijen Siber
              </h3>
              {ai_patrol?.confidence_score && (
                <span className="text-[11px] font-mono text-slate-400">
                  Keyakinan: {(ai_patrol.confidence_score * 100).toFixed(0)}%
                </span>
              )}
            </div>

            {/* Verdict Strip & Status Klaim */}
            <div className="space-y-2">
              <div className="flex items-center justify-between gap-2 flex-wrap">
                <span className="text-[10px] font-mono uppercase text-slate-400 tracking-wider">
                  Klasifikasi Integritas Narasi
                </span>
                {ai_patrol?.status_klaim ? (
                  <span
                    className={`px-2.5 py-0.5 rounded-full text-[11px] font-semibold font-mono flex items-center gap-1.5 border ${
                      ai_patrol.status_klaim === 'Fakta Terverifikasi'
                        ? 'bg-emerald-500/15 text-emerald-400 border-emerald-500/30'
                        : ai_patrol.status_klaim === 'Dugaan / Belum Terverifikasi'
                        ? 'bg-amber-500/15 text-amber-400 border-amber-500/30'
                        : 'bg-rose-500/15 text-rose-400 border-rose-500/30'
                    }`}
                  >
                    {ai_patrol.status_klaim === 'Fakta Terverifikasi' ? (
                      <CheckCircle2 className="w-3 h-3 text-emerald-400" />
                    ) : (
                      <AlertTriangle className="w-3 h-3 text-amber-400" />
                    )}
                    {ai_patrol.status_klaim}
                  </span>
                ) : (
                  <span className="px-2 py-0.5 rounded text-[10px] font-mono bg-emerald-500/10 text-emerald-400 border border-emerald-500/20 font-semibold">
                    Fakta Terverifikasi
                  </span>
                )}
              </div>

              <div className="grid grid-cols-2 gap-2 font-mono">
                <div className="p-2.5 rounded-lg bg-slate-50 dark:bg-[#0A0D14] border border-slate-200 dark:border-white/[0.06]">
                  <div className="text-[9.5px] text-slate-400 uppercase">Status Operasional</div>
                  <div className="text-xs font-bold text-slate-800 dark:text-slate-200 mt-0.5">
                    {ai_patrol?.status || 'N/A'}
                  </div>
                </div>
                <div className="p-2.5 rounded-lg bg-slate-50 dark:bg-[#0A0D14] border border-slate-200 dark:border-white/[0.06]">
                  <div className="text-[9.5px] text-slate-400 uppercase">Domain Ancaman</div>
                  <div className="text-xs font-bold text-blue-500 mt-0.5 truncate">
                    {ai_patrol?.predicted_label || 'N/A'}
                  </div>
                </div>
              </div>
            </div>

            {/* Ringkasan Eksekutif */}
            <div className="p-3.5 rounded-lg bg-slate-50 dark:bg-white/[0.03] border-l-2 border-blue-500 text-xs text-slate-700 dark:text-slate-300 leading-relaxed font-sans">
              <span className="font-semibold block text-slate-900 dark:text-white mb-1.5 font-mono text-[11px] uppercase tracking-wider">
                Ringkasan Eksekutif:
              </span>
              {ai_patrol?.summary || 'Belum ada ringkasan analisis.'}
            </div>

            {/* Kutipan Bukti Sumber Verbatim (Placed cleanly under Ringkasan Eksekutif) */}
            {ai_patrol?.kutipan_bukti && (
              <div className="p-3 rounded-lg bg-slate-50 dark:bg-[#0A0D14] border border-blue-500/25 space-y-1">
                <div className="flex items-center gap-1.5 text-blue-500 dark:text-blue-400 text-[10px] font-mono uppercase tracking-wider font-bold">
                  <Fingerprint className="w-3.5 h-3.5" />
                  <span>Kutipan Bukti Sumber</span>
                </div>
                <p className="text-xs text-slate-700 dark:text-slate-300 italic leading-relaxed font-sans select-text">
                  "{ai_patrol.kutipan_bukti}"
                </p>
              </div>
            )}

            {/* Dossier Intelijen Taktis (Format BLUF: Bottom Line Up Front) */}
            {bluf ? (
              <div className="pt-2 border-t border-slate-100 dark:border-white/[0.06] space-y-3">
                <div className="flex items-center justify-between">
                  <span className="text-[11px] font-mono font-semibold uppercase text-slate-400 tracking-wider flex items-center gap-1.5">
                    <ShieldAlert className="w-3.5 h-3.5 text-blue-500" />
                    Dossier Intelijen Taktis (Format BLUF)
                  </span>
                  <span className="text-[9.5px] font-mono text-emerald-600 dark:text-emerald-400 font-semibold uppercase bg-emerald-500/10 px-2 py-0.5 rounded border border-emerald-500/20">
                    Standar Analisis BLUF
                  </span>
                </div>

                <div className="space-y-2.5">
                  {/* 1. INTISARI BLUF (Bottom Line Up Front) */}
                  <div className="p-3.5 rounded-lg bg-blue-50/70 dark:bg-blue-950/20 border-l-4 border-l-blue-600 border border-blue-200/80 dark:border-blue-900/40 space-y-1">
                    <div className="flex items-center justify-between">
                      <span className="text-[10px] text-blue-600 dark:text-blue-400 font-bold uppercase font-mono tracking-wider">
                        INTISARI // BLUF (Bottom Line Up Front)
                      </span>
                      <span className="text-[9px] font-mono text-slate-400">Kesimpulan Eksekutif</span>
                    </div>
                    <p className="text-xs text-slate-900 dark:text-slate-100 font-sans whitespace-normal break-words leading-relaxed font-semibold">
                      {bluf.intisari_bluf || '-'}
                    </p>
                  </div>

                  {/* 2. FAKTA VS KLAIM */}
                  <div className="p-3 rounded-lg bg-slate-50 dark:bg-[#0A0D14] border border-slate-200 dark:border-white/[0.06] space-y-1">
                    <span className="text-[10px] text-indigo-500 font-bold uppercase font-mono block">
                      FAKTA VS KLAIM // Verifikasi Bukti
                    </span>
                    <p className="text-xs text-slate-800 dark:text-slate-200 font-sans whitespace-pre-line break-words leading-relaxed">
                      {bluf.fakta_vs_klaim || '-'}
                    </p>
                  </div>

                  {/* 3. ANALISIS DAMPAK & AKTOR MODUS (2 Col Grid) */}
                  <div className="grid grid-cols-1 sm:grid-cols-2 gap-2.5">
                    <div className="p-3 rounded-lg bg-slate-50 dark:bg-[#0A0D14] border border-slate-200 dark:border-white/[0.06] space-y-1">
                      <span className="text-[10px] text-amber-500 font-bold uppercase font-mono block">
                        ANALISIS DAMPAK // Stabilitas IPOLEKSOSBUDHANKAM
                      </span>
                      <p className="text-xs text-slate-800 dark:text-slate-200 font-sans whitespace-normal break-words leading-relaxed">
                        {bluf.analisis_dampak || '-'}
                      </p>
                    </div>

                    <div className="p-3 rounded-lg bg-slate-50 dark:bg-[#0A0D14] border border-slate-200 dark:border-white/[0.06] space-y-1">
                      <span className="text-[10px] text-rose-500 font-bold uppercase font-mono block">
                        AKTOR & MODUS // Kanal & Pola Penyebaran
                      </span>
                      <p className="text-xs text-slate-800 dark:text-slate-200 font-sans whitespace-normal break-words leading-relaxed">
                        {bluf.aktor_dan_modus || '-'}
                      </p>
                    </div>
                  </div>

                  {/* 4. REKOMENDASI TINDAK LANJUT */}
                  <div className="p-3 rounded-lg bg-emerald-50/50 dark:bg-emerald-950/20 border-l-2 border-l-emerald-500 border border-emerald-200/70 dark:border-emerald-900/30 space-y-1">
                    <span className="text-[10px] text-emerald-600 dark:text-emerald-400 font-bold uppercase font-mono block">
                      REKOMENDASI OPERASIONAL // Tindak Lanjut Analis
                    </span>
                    <p className="text-xs text-slate-900 dark:text-slate-100 font-sans whitespace-normal break-words leading-relaxed font-medium">
                      {bluf.rekomendasi_tindak_lanjut || '-'}
                    </p>
                  </div>
                </div>
              </div>
            ) : analysis_5w1h ? (
              <div className="pt-2 border-t border-slate-100 dark:border-white/[0.06] space-y-2.5">
                <div className="flex items-center justify-between">
                  <span className="text-[11px] font-mono font-semibold uppercase text-slate-400 tracking-wider">
                    Matriks Sintesis 5W+1H
                  </span>
                  <span className="text-[9.5px] font-mono text-blue-500 uppercase">
                    Ekstraksi Multimodal
                  </span>
                </div>

                <div className="space-y-2.5">
                  {/* Primary Narrative: What (Full Width with Left Accent) */}
                  <div className="p-3.5 rounded-lg bg-slate-50 dark:bg-[#0A0D14] border-l-2 border-l-blue-500 border border-slate-200 dark:border-white/[0.06] space-y-1">
                    <span className="text-[10px] text-blue-500 font-bold uppercase font-mono block">
                      WHAT // Peristiwa Inti
                    </span>
                    <p className="text-xs text-slate-900 dark:text-slate-100 font-sans whitespace-normal break-words leading-relaxed font-medium">
                      {analysis_5w1h.what || '-'}
                    </p>
                  </div>

                  {/* Secondary Context: Who & Why */}
                  <div className="grid grid-cols-1 sm:grid-cols-2 gap-2.5">
                    <div className="p-3 rounded-lg bg-slate-50 dark:bg-[#0A0D14] border border-slate-200 dark:border-white/[0.06] space-y-1">
                      <span className="text-[10px] text-emerald-500 font-bold uppercase font-mono block">
                        WHO // Pihak Terlibat
                      </span>
                      <p className="text-xs text-slate-800 dark:text-slate-200 font-sans whitespace-normal break-words leading-relaxed">
                        {analysis_5w1h.who || '-'}
                      </p>
                    </div>

                    <div className="p-3 rounded-lg bg-slate-50 dark:bg-[#0A0D14] border border-slate-200 dark:border-white/[0.06] space-y-1">
                      <span className="text-[10px] text-amber-500 font-bold uppercase font-mono block">
                        WHY // Motif & Indikasi
                      </span>
                      <p className="text-xs text-slate-800 dark:text-slate-200 font-sans whitespace-normal break-words leading-relaxed">
                        {analysis_5w1h.why || '-'}
                      </p>
                    </div>
                  </div>

                  {/* Spatio-Temporal & Mechanism: When, Where, How */}
                  <div className="grid grid-cols-1 sm:grid-cols-3 gap-2.5">
                    <div className="p-2.5 rounded-lg bg-slate-50 dark:bg-[#0A0D14] border border-slate-200 dark:border-white/[0.06] space-y-1">
                      <span className="text-[9.5px] text-slate-500 dark:text-slate-400 font-bold uppercase font-mono block">
                        WHEN // Waktu
                      </span>
                      <p className="text-[11.5px] text-slate-800 dark:text-slate-200 font-sans whitespace-normal break-words leading-relaxed">
                        {(analysis_5w1h as any).when || analysis_5w1h.when_info || 'Tidak tertera'}
                      </p>
                    </div>

                    <div className="p-2.5 rounded-lg bg-slate-50 dark:bg-[#0A0D14] border border-slate-200 dark:border-white/[0.06] space-y-1">
                      <span className="text-[9.5px] text-slate-500 dark:text-slate-400 font-bold uppercase font-mono block">
                        WHERE // Lokasi
                      </span>
                      <p className="text-[11.5px] text-slate-800 dark:text-slate-200 font-sans whitespace-normal break-words leading-relaxed">
                        {(analysis_5w1h as any).where || analysis_5w1h.where_info || 'Tidak tertera'}
                      </p>
                    </div>

                    <div className="p-2.5 rounded-lg bg-slate-50 dark:bg-[#0A0D14] border border-slate-200 dark:border-white/[0.06] space-y-1">
                      <span className="text-[9.5px] text-slate-500 dark:text-slate-400 font-bold uppercase font-mono block">
                        HOW // Modus Operandi
                      </span>
                      <p className="text-[11.5px] text-slate-800 dark:text-slate-200 font-sans whitespace-normal break-words leading-relaxed">
                        {analysis_5w1h.how || '-'}
                      </p>
                    </div>
                  </div>
                </div>
              </div>
            ) : null}

            {/* Penalaran Kausal AI (Sub-Cards with generous spacing, parsed sections) */}
            {ai_patrol?.reasoning && (
              <div className="pt-2.5 border-t border-slate-100 dark:border-white/[0.06] space-y-2.5">
                <span className="text-[11px] font-mono font-semibold uppercase text-slate-400 tracking-wider block">
                  Penalaran Kausal AI
                </span>
                <div className="space-y-3">
                  {parseAIReasoning(ai_patrol.reasoning).map((sec, idx) => (
                    <div
                      key={idx}
                      className="p-3.5 rounded-lg bg-slate-50 dark:bg-[#0A0D14] border border-slate-200 dark:border-white/[0.06] space-y-1.5"
                    >
                      <span className="text-[11px] font-semibold uppercase tracking-wider text-blue-500 dark:text-blue-400 font-mono block">
                        {sec.title}:
                      </span>
                      <p className="text-xs text-slate-700 dark:text-slate-300 leading-relaxed font-sans whitespace-normal break-words">
                        {sec.content}
                      </p>
                    </div>
                  ))}
                </div>
              </div>
            )}
          </div>

          {/* Card: Keputusan Analis (HITL Validation) */}
          <div className="cyber-card rounded-xl p-4 sm:p-5 space-y-3.5 border border-blue-500/20">
            <div className="flex items-center justify-between border-b border-slate-100 dark:border-white/[0.06] pb-2.5">
              <h3 className="text-xs font-bold text-slate-800 dark:text-slate-100 uppercase tracking-wider font-mono flex items-center gap-1.5">
                <CheckCircle2 className="w-4 h-4 text-emerald-500" />
                Keputusan Analis
              </h3>
              {submitSuccessMsg && (
                <span className="text-[11px] font-mono text-emerald-500 font-semibold">
                  {submitSuccessMsg}
                </span>
              )}
            </div>

            <form onSubmit={handleValidationSubmit} className="space-y-3">
              {/* Segmented Control: Setuju, Ubah, Tolak */}
              <div className="grid grid-cols-3 gap-1.5 bg-slate-100 dark:bg-[#0A0D14] p-1 rounded-lg border border-slate-200 dark:border-white/[0.06]">
                <button
                  type="button"
                  onClick={() => setValidationDecision('VALIDATED')}
                  className={`py-1.5 rounded-md text-xs font-semibold font-mono flex items-center justify-center gap-1 transition-colors ${
                    validationDecision === 'VALIDATED'
                      ? 'bg-emerald-600 text-white shadow-sm'
                      : 'text-slate-600 dark:text-slate-400 hover:text-slate-900 dark:hover:text-white'
                  }`}
                >
                  <CheckCircle2 className="w-3.5 h-3.5" /> Setuju
                </button>
                <button
                  type="button"
                  onClick={() => setValidationDecision('MODIFIED')}
                  className={`py-1.5 rounded-md text-xs font-semibold font-mono flex items-center justify-center gap-1 transition-colors ${
                    validationDecision === 'MODIFIED'
                      ? 'bg-amber-600 text-white shadow-sm'
                      : 'text-slate-600 dark:text-slate-400 hover:text-slate-900 dark:hover:text-white'
                  }`}
                >
                  <AlertTriangle className="w-3.5 h-3.5" /> Ubah
                </button>
                <button
                  type="button"
                  onClick={() => setValidationDecision('REJECTED')}
                  className={`py-1.5 rounded-md text-xs font-semibold font-mono flex items-center justify-center gap-1 transition-colors ${
                    validationDecision === 'REJECTED'
                      ? 'bg-rose-600 text-white shadow-sm'
                      : 'text-slate-600 dark:text-slate-400 hover:text-slate-900 dark:hover:text-white'
                  }`}
                >
                  <XCircle className="w-3.5 h-3.5" /> Tolak
                </button>
              </div>

              {/* Conditional Override Fields */}
              {validationDecision === 'MODIFIED' && (
                <div className="grid grid-cols-2 gap-2 pt-1 font-mono">
                  <div>
                    <label className="text-[10px] uppercase text-slate-400 block mb-1">Tingkat Risiko</label>
                    <select
                      value={riskOverride}
                      onChange={(e) => setRiskOverride(e.target.value)}
                      className="w-full bg-white dark:bg-[#0A0D14] border border-slate-200 dark:border-white/[0.08] rounded-lg py-1.5 px-2 text-xs text-slate-800 dark:text-slate-200 focus:outline-none focus:border-blue-500"
                    >
                      <option value="RENDAH">RENDAH</option>
                      <option value="SEDANG">SEDANG</option>
                      <option value="TINGGI">TINGGI</option>
                    </select>
                  </div>
                  <div>
                    <label className="text-[10px] uppercase text-slate-400 block mb-1">Kategori</label>
                    <select
                      value={categoryOverride}
                      onChange={(e) => setCategoryOverride(e.target.value)}
                      className="w-full bg-white dark:bg-[#0A0D14] border border-slate-200 dark:border-white/[0.08] rounded-lg py-1.5 px-2 text-xs text-slate-800 dark:text-slate-200 focus:outline-none focus:border-blue-500"
                    >
                      <option value="Pornografi">Pornografi</option>
                      <option value="COP">COP (Child Online Protection)</option>
                      <option value="Violent Extremism">Violent Extremism</option>
                      <option value="Migrant and Human Trafficking">Migrant and Human Trafficking</option>
                      <option value="Judi Online">Judi Online</option>
                      <option value="Narkotika">Narkotika</option>
                      <option value="Umum / Di Luar Topik">Umum / Di Luar Topik</option>
                    </select>
                  </div>
                </div>
              )}

              {/* Notes */}
              <div>
                <label className="text-[10px] font-mono uppercase text-slate-400 block mb-1">
                  Catatan Analis {validationDecision !== 'VALIDATED' && <span className="text-rose-500">*</span>}
                </label>
                <textarea
                  rows={2}
                  value={analystNotes}
                  onChange={(e) => setAnalystNotes(e.target.value)}
                  placeholder={
                    validationDecision === 'VALIDATED'
                      ? 'Catatan opsional...'
                      : 'Wajib memberikan keterangan alasan...'
                  }
                  className="w-full bg-white dark:bg-[#0A0D14] border border-slate-200 dark:border-white/[0.08] rounded-lg p-2 text-xs text-slate-800 dark:text-slate-200 placeholder:text-slate-400 dark:placeholder:text-slate-600 focus:outline-none focus:border-blue-500 transition-colors"
                />
              </div>

              <button
                type="submit"
                disabled={submitting}
                className="w-full py-2 px-4 rounded-lg bg-blue-600 hover:bg-blue-500 text-white font-semibold text-xs font-mono shadow-sm transition-colors disabled:opacity-50"
              >
                {submitting ? 'Menyimpan...' : 'Simpan Keputusan'}
              </button>
            </form>
          </div>

          {/* Card: Penerusan ke Tim Dalkonten */}
          <div className="cyber-card rounded-xl p-4 sm:p-5 space-y-3.5 border border-amber-500/20">
            <div className="flex items-center justify-between border-b border-slate-100 dark:border-white/[0.06] pb-2.5">
              <h3 className="text-xs font-bold text-slate-800 dark:text-slate-100 uppercase tracking-wider font-mono flex items-center gap-1.5">
                <Send className="w-4 h-4 text-amber-500" />
                Penerusan ke Tim Dalkonten
              </h3>
              <DalkontenBadge status={ai_patrol?.dalkonten_status} />
            </div>

            {dalkontenMsg && (
              <p className="text-[11px] font-mono text-emerald-500 bg-emerald-500/10 p-2 rounded border border-emerald-500/20">
                {dalkontenMsg}
              </p>
            )}

            <div className="text-xs text-slate-600 dark:text-slate-300 space-y-1.5 bg-slate-50 dark:bg-[#0A0D14] p-3 rounded-lg border border-slate-200 dark:border-white/[0.06]">
              <div className="flex items-center justify-between">
                <span className="text-[10.5px] font-mono text-slate-400 uppercase">Status Alur:</span>
                <span className="font-mono font-semibold text-xs text-slate-800 dark:text-slate-200">
                  {ai_patrol?.dalkonten_status || 'BELUM DITERUSKAN'}
                </span>
              </div>
              {ai_patrol?.dalkonten_forwarded_by && (
                <div className="flex items-center justify-between">
                  <span className="text-[10.5px] font-mono text-slate-400 uppercase">Operator Pengaju:</span>
                  <span className="font-mono text-xs text-slate-700 dark:text-slate-300">
                    {ai_patrol.dalkonten_forwarded_by}
                  </span>
                </div>
              )}
              {ai_patrol?.dalkonten_forwarded_at && (
                <div className="flex items-center justify-between">
                  <span className="text-[10.5px] font-mono text-slate-400 uppercase">Waktu Pengajuan:</span>
                  <span className="font-mono text-[11px] text-slate-500 dark:text-slate-400">
                    {new Date(ai_patrol.dalkonten_forwarded_at).toLocaleString('id-ID')}
                  </span>
                </div>
              )}
            </div>

            <div className="space-y-2 pt-1">
              <button
                type="button"
                disabled={updatingDalkonten}
                onClick={() => handleDalkontenStatus('SIAP DITERUSKAN KE DALKONTEN')}
                className="w-full py-2 px-3 rounded-lg bg-amber-600 hover:bg-amber-500 text-white font-semibold text-xs font-mono shadow-sm transition-colors flex items-center justify-center gap-1.5 disabled:opacity-50"
              >
                <AlertTriangle className="w-3.5 h-3.5" />
                {updatingDalkonten ? 'Memproses...' : 'Tandai Siap Diteruskan ke Dalkonten'}
              </button>

              <div className="grid grid-cols-2 gap-2">
                <button
                  type="button"
                  disabled={updatingDalkonten}
                  onClick={() => handleDalkontenStatus('SUDAH DITERUSKAN')}
                  className="py-1.5 px-2.5 rounded-lg bg-emerald-600 hover:bg-emerald-500 text-white font-semibold text-[11px] font-mono shadow-sm transition-colors flex items-center justify-center gap-1 disabled:opacity-50"
                >
                  <CheckCircle2 className="w-3.5 h-3.5" /> Konfirmasi Terkirim
                </button>
                <button
                  type="button"
                  disabled={updatingDalkonten}
                  onClick={() => handleDalkontenStatus('BELUM DITERUSKAN')}
                  className="py-1.5 px-2.5 rounded-lg bg-slate-200 dark:bg-white/[0.08] hover:bg-slate-300 dark:hover:bg-white/[0.12] text-slate-700 dark:text-slate-300 font-semibold text-[11px] font-mono shadow-sm transition-colors flex items-center justify-center gap-1 disabled:opacity-50"
                >
                  <XCircle className="w-3.5 h-3.5" /> Reset Status
                </button>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};
