import React, { useEffect, useState, useRef } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import { apiClient } from '../api/client';
import { ContentItem } from '../types';
import { PlatformBadge, RiskBadge, SentimentBadge, StatusBadge } from '../components/common/Badge';
import {
  Search,
  Filter,
  ArrowRight,
  Layers,
  AlertCircle,
  Zap,
  Link2,
  CheckCircle2,
  ExternalLink,
  X,
  Download,
  FileText,
  FileDown,
  ChevronDown,
} from 'lucide-react';

export const ContentExplorerPage: React.FC = () => {
  const navigate = useNavigate();
  const [contents, setContents] = useState<ContentItem[]>([]);
  const [loading, setLoading] = useState<boolean>(true);
  const [error, setError] = useState<string | null>(null);

  // Filters
  const [platform, setPlatform] = useState<string>('');
  const [category, setCategory] = useState<string>('');
  const [sentiment, setSentiment] = useState<string>('');
  const [status, setStatus] = useState<string>('');
  const [search, setSearch] = useState<string>('');

  // Direct Link Triage State
  const [showIntakeForm, setShowIntakeForm] = useState<boolean>(false);
  const [inputUrl, setInputUrl] = useState<string>('');
  const [inputNotes, setInputNotes] = useState<string>('');
  const [isSubmittingIntake, setIsSubmittingIntake] = useState<boolean>(false);
  const [intakeStage, setIntakeStage] = useState<string>('1/3 Mengamankan bukti halaman...');
  const [intakeSuccess, setIntakeSuccess] = useState<any | null>(null);
  const [intakeError, setIntakeError] = useState<string | null>(null);

  // Single Download Dropdown state
  const [showExportMenu, setShowExportMenu] = useState<boolean>(false);
  const [exportingFormat, setExportingFormat] = useState<'pdf' | 'csv' | null>(null);
  const exportMenuRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    const handleClickOutside = (event: MouseEvent) => {
      if (exportMenuRef.current && !exportMenuRef.current.contains(event.target as Node)) {
        setShowExportMenu(false);
      }
    };
    document.addEventListener('mousedown', handleClickOutside);
    return () => document.removeEventListener('mousedown', handleClickOutside);
  }, []);

  const handleExport = async (fmt: 'pdf' | 'csv') => {
    setShowExportMenu(false);
    try {
      setExportingFormat(fmt);
      await apiClient.v1.exportBlob(fmt, {
        platform: platform || undefined,
        category: category || undefined,
        status: status || undefined,
      });
    } catch (err) {
      console.error('Failed to export:', err);
    } finally {
      setExportingFormat(null);
    }
  };

  const fetchContents = async () => {
    try {
      setLoading(true);
      const params: any = {};
      if (platform) params.platform = platform;
      if (category) params.category = category;
      if (sentiment) params.sentiment = sentiment;
      if (status) params.status = status;
      if (search.trim()) params.search = search.trim();

      const data = await apiClient.contents.list(params);
      setContents(data);
    } catch (err) {
      setError('Gagal memuat arsip temuan');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchContents();
  }, [platform, category, sentiment, status]);

  const handleSearchSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    fetchContents();
  };

  const handleIntakeSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!inputUrl.trim()) return;

    setIsSubmittingIntake(true);
    setIntakeStage('1/3 Mengamankan bukti halaman...');
    setIntakeError(null);
    setIntakeSuccess(null);

    const stageTimer1 = setTimeout(() => {
      setIntakeStage('2/3 Memahami konteks & bahasa...');
    }, 2800);

    const stageTimer2 = setTimeout(() => {
      setIntakeStage('3/3 Menyusun ringkasan & analisis...');
    }, 6000);

    try {
      const res = await apiClient.assistant.intake({
        url: inputUrl.trim(),
        source_channel: 'WEB_DASHBOARD',
        reporter_identifier: 'Web-Console-Analyst',
        notes: inputNotes.trim() || undefined,
      });

      clearTimeout(stageTimer1);
      clearTimeout(stageTimer2);
      setIntakeSuccess(res);
      setInputUrl('');
      setInputNotes('');
      await fetchContents();

      // Auto-redirect langsung ke halaman detail temuan
      if (res && res.content_id) {
        navigate(`/contents/${res.content_id}`);
      }
    } catch (err: any) {
      clearTimeout(stageTimer1);
      clearTimeout(stageTimer2);
      setIntakeError(err.response?.data?.detail || 'Gagal mengirim URL untuk triase.');
    } finally {
      setIsSubmittingIntake(false);
    }
  };

  return (
    <div className="space-y-4 pb-10">
      {/* ── 1. HEADER RINGKAS & TOMBOL AKSI ── */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 border-b border-slate-200 dark:border-white/[0.06] pb-3">
        <h1 className="text-lg font-semibold tracking-tight text-slate-900 dark:text-white flex items-center gap-2">
          Arsip Temuan
        </h1>

        <div className="flex items-center gap-2">
          {/* Export Dropdown Button */}
          <div className="relative" ref={exportMenuRef}>
            <button
              onClick={() => setShowExportMenu(!showExportMenu)}
              disabled={exportingFormat !== null}
              className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-semibold bg-white dark:bg-[#12151E] text-slate-800 dark:text-slate-200 border border-slate-200 dark:border-white/[0.08] hover:border-blue-500 shadow-sm transition-colors disabled:opacity-50 font-mono"
            >
              <Download className={`w-3.5 h-3.5 text-blue-500 ${exportingFormat ? 'animate-bounce' : ''}`} />
              <span>{exportingFormat ? `Mengunduh...` : 'Ekspor'}</span>
              <ChevronDown className="w-3 h-3 text-slate-400" />
            </button>

            {showExportMenu && (
              <div className="absolute right-0 mt-1.5 w-52 rounded-xl bg-white dark:bg-[#0F1117] border border-slate-200 dark:border-white/[0.08] shadow-2xl py-1.5 z-50 text-xs">
                <button
                  onClick={() => handleExport('pdf')}
                  className="w-full px-3.5 py-2 text-left flex items-start gap-2.5 hover:bg-slate-50 dark:hover:bg-white/[0.04] transition-colors"
                >
                  <FileText className="w-4 h-4 text-rose-500 shrink-0 mt-0.5" />
                  <div>
                    <div className="font-semibold text-slate-800 dark:text-slate-200">Dossier PDF</div>
                    <div className="text-[10px] text-slate-500 font-mono">Berkas resmi berbukti visual</div>
                  </div>
                </button>
                <div className="border-t border-slate-100 dark:border-white/[0.06] my-1" />
                <button
                  onClick={() => handleExport('csv')}
                  className="w-full px-3.5 py-2 text-left flex items-start gap-2.5 hover:bg-slate-50 dark:hover:bg-white/[0.04] transition-colors"
                >
                  <FileDown className="w-4 h-4 text-emerald-500 shrink-0 mt-0.5" />
                  <div>
                    <div className="font-semibold text-slate-800 dark:text-slate-200">Metadata CSV</div>
                    <div className="text-[10px] text-slate-500 font-mono">Tabel data olahan</div>
                  </div>
                </button>
              </div>
            )}
          </div>

          <button
            onClick={() => setShowIntakeForm(!showIntakeForm)}
            className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-semibold bg-blue-500/10 text-blue-600 dark:text-blue-400 border border-blue-500/20 hover:bg-blue-500 hover:text-white transition-colors font-mono"
          >
            <Zap className="w-3.5 h-3.5 text-blue-400" />
            {showIntakeForm ? 'Tutup Form' : '+ Input URL'}
          </button>
        </div>
      </div>

      {/* ── 2. FORM INTAKE (DIRECT LINK TRIAGE) ── */}
      {showIntakeForm && (
        <div className="cyber-card rounded-xl p-3.5 border border-blue-500/30 space-y-2.5">
          <div className="flex items-center justify-between border-b border-slate-100 dark:border-white/[0.06] pb-2">
            <h3 className="text-xs font-semibold text-slate-800 dark:text-slate-200 font-mono flex items-center gap-1.5">
              <Link2 className="w-3.5 h-3.5 text-blue-500" />
              Input URL untuk Triase Otonom
            </h3>
            <button onClick={() => setShowIntakeForm(false)} className="text-slate-400 hover:text-slate-200">
              <X className="w-3.5 h-3.5" />
            </button>
          </div>

          <form onSubmit={handleIntakeSubmit} className="space-y-2.5 pt-1">
            <div className="flex flex-col sm:flex-row gap-2">
              <div className="flex-1 relative">
                <input
                  type="url"
                  required
                  value={inputUrl}
                  onChange={(e) => setInputUrl(e.target.value)}
                  placeholder="https://tiktok.com/@... atau https://youtu.be/... atau https://instagram.com/..."
                  className="w-full pl-8 pr-3 py-1.5 bg-white dark:bg-[#0A0D14] border border-slate-200 dark:border-white/[0.08] rounded-lg text-xs text-slate-800 dark:text-white placeholder:text-slate-400 dark:placeholder:text-slate-600 focus:outline-none focus:border-blue-500 font-mono transition-colors"
                />
                <Link2 className="w-3.5 h-3.5 text-slate-400 absolute left-2.5 top-2.5" />
              </div>

              <input
                type="text"
                value={inputNotes}
                onChange={(e) => setInputNotes(e.target.value)}
                placeholder="Catatan analisis opsional..."
                className="sm:w-1/3 px-3 py-1.5 bg-white dark:bg-[#0A0D14] border border-slate-200 dark:border-white/[0.08] rounded-lg text-xs text-slate-800 dark:text-white placeholder:text-slate-400 dark:placeholder:text-slate-600 focus:outline-none focus:border-blue-500 transition-colors"
              />

              <button
                type="submit"
                disabled={isSubmittingIntake}
                className="px-3.5 py-1.5 bg-blue-600 hover:bg-blue-500 text-white font-semibold text-xs rounded-lg transition-colors flex items-center justify-center gap-1 font-mono disabled:opacity-50 shrink-0"
              >
                <Zap className={`w-3.5 h-3.5 ${isSubmittingIntake ? 'animate-spin' : ''}`} />
                {isSubmittingIntake ? intakeStage : 'Kirim Triase'}
              </button>
            </div>
          </form>

          {/* Sukses Alert */}
          {intakeSuccess && (
            <div className="p-2.5 rounded-lg bg-emerald-500/10 border border-emerald-500/20 flex items-center justify-between text-xs font-mono">
              <div className="flex items-center gap-2 text-emerald-400">
                <CheckCircle2 className="w-4 h-4 text-emerald-400 shrink-0" />
                <span>
                  Tiket <strong>{intakeSuccess.ticket_number}</strong> berhasil dibuat!
                </span>
              </div>
              <Link
                to={`/contents/${intakeSuccess.content_id}`}
                className="px-2 py-0.5 bg-emerald-600 text-white rounded text-xs font-semibold flex items-center gap-1"
              >
                <span>Buka</span>
                <ExternalLink className="w-3 h-3" />
              </Link>
            </div>
          )}

          {/* Error Alert */}
          {intakeError && (
            <div className="p-2.5 rounded-lg bg-rose-500/10 border border-rose-500/20 flex items-center justify-between text-xs font-mono text-rose-400">
              <div className="flex items-center gap-2">
                <AlertCircle className="w-4 h-4 shrink-0" />
                <span>{intakeError}</span>
              </div>
              <button onClick={() => setIntakeError(null)}>
                <X className="w-3.5 h-3.5" />
              </button>
            </div>
          )}
        </div>
      )}

      {/* ── 3. FILTER BAR RINGKAS ── */}
      <div className="cyber-card rounded-xl p-3 space-y-2 border border-slate-200 dark:border-white/[0.06]">
        <form onSubmit={handleSearchSubmit} className="flex flex-col sm:flex-row gap-2">
          <div className="relative flex-1">
            <input
              type="text"
              value={search}
              onChange={(e) => setSearch(e.target.value)}
              placeholder="Cari judul, kata kunci, akun, atau URL..."
              className="w-full pl-8 pr-3 py-1.5 bg-white dark:bg-[#0A0D14] border border-slate-200 dark:border-white/[0.08] rounded-lg text-xs text-slate-800 dark:text-slate-200 placeholder:text-slate-400 dark:placeholder:text-slate-600 focus:outline-none focus:border-blue-500 transition-colors"
            />
            <Search className="w-3.5 h-3.5 text-slate-400 absolute left-2.5 top-2" />
          </div>

          <button
            type="submit"
            className="px-3.5 py-1.5 bg-blue-600 hover:bg-blue-500 text-white font-semibold text-xs rounded-lg transition-colors flex items-center justify-center gap-1.5 shrink-0 font-mono"
          >
            <Filter className="w-3 h-3" /> Filter
          </button>
        </form>

        <div className="grid grid-cols-2 sm:grid-cols-4 gap-2 pt-0.5">
          <select
            value={platform}
            onChange={(e) => setPlatform(e.target.value)}
            className="bg-white dark:bg-[#0A0D14] border border-slate-200 dark:border-white/[0.08] rounded-lg py-1 px-2 text-xs text-slate-700 dark:text-slate-300 focus:outline-none focus:border-blue-500 transition-colors"
          >
            <option value="">Semua Platform</option>
            <option value="youtube">YouTube</option>
            <option value="tiktok">TikTok</option>
            <option value="instagram">Instagram</option>
            <option value="x">X (Twitter)</option>
            <option value="web">Web / Media</option>
          </select>

          <select
            value={category}
            onChange={(e) => setCategory(e.target.value)}
            className="bg-white dark:bg-[#0A0D14] border border-slate-200 dark:border-white/[0.08] rounded-lg py-1 px-2 text-xs text-slate-700 dark:text-slate-300 focus:outline-none focus:border-blue-500 transition-colors"
          >
            <option value="">Semua Kategori</option>
            <option value="Kejahatan Finansial">Kejahatan Finansial</option>
            <option value="Perjudian Daring">Perjudian Daring</option>
            <option value="Disinformasi Politik & Kebijakan Publik">Disinformasi Politik</option>
            <option value="Hoaks Kesehatan & Pangan">Hoaks Kesehatan</option>
            <option value="Klarifikasi & Edukasi Resmi">Klarifikasi Resmi</option>
          </select>

          <select
            value={sentiment}
            onChange={(e) => setSentiment(e.target.value)}
            className="bg-white dark:bg-[#0A0D14] border border-slate-200 dark:border-white/[0.08] rounded-lg py-1 px-2 text-xs text-slate-700 dark:text-slate-300 focus:outline-none focus:border-blue-500 transition-colors"
          >
            <option value="">Semua Sentimen</option>
            <option value="POSITIF">Positif</option>
            <option value="NEGATIF">Negatif</option>
            <option value="NETRAL">Netral</option>
            <option value="CAMPURAN">Campuran</option>
          </select>

          <select
            value={status}
            onChange={(e) => setStatus(e.target.value)}
            className="bg-white dark:bg-[#0A0D14] border border-slate-200 dark:border-white/[0.08] rounded-lg py-1 px-2 text-xs text-slate-700 dark:text-slate-300 focus:outline-none focus:border-blue-500 transition-colors"
          >
            <option value="">Semua Status</option>
            <option value="WAITING_VALIDATION">Menunggu Validasi</option>
            <option value="VALIDATED">Tervalidasi</option>
            <option value="MODIFIED">Koreksi Analis</option>
            <option value="REJECTED">Bukan Pelanggaran</option>
          </select>
        </div>
      </div>

      {/* ── 4. TABEL DATA LINEAR-STYLE ── */}
      {loading ? (
        <div className="cyber-card rounded-xl p-4 space-y-2.5">
          <div className="h-4 w-32 rounded skeleton-shimmer" />
          <div className="space-y-2">
            {[1, 2, 3, 4, 5].map((i) => (
              <div key={i} className="h-10 rounded skeleton-shimmer" />
            ))}
          </div>
        </div>
      ) : error ? (
        <div className="p-8 cyber-card rounded-xl text-center">
          <AlertCircle className="w-8 h-8 text-rose-500 mx-auto mb-2" />
          <p className="text-rose-500 text-sm font-semibold">{error}</p>
        </div>
      ) : contents.length === 0 ? (
        <div className="cyber-card rounded-xl p-10 text-center text-slate-400 font-mono text-xs">
          Belum ada konten temuan yang sesuai filter.
        </div>
      ) : (
        <div className="cyber-card rounded-xl overflow-hidden border border-slate-200 dark:border-white/[0.06]">
          <div className="overflow-x-auto">
            <table className="w-full text-left text-xs">
              <thead className="bg-slate-50 dark:bg-[#0A0D14] text-slate-500 dark:text-slate-400 uppercase text-[10px] font-semibold tracking-wider border-b border-slate-200 dark:border-white/[0.06] font-mono">
                <tr>
                  <th className="py-2.5 px-3.5">Platform & Judul</th>
                  <th className="py-2.5 px-3.5">Akun Sumber</th>
                  <th className="py-2.5 px-3.5">Kategori</th>
                  <th className="py-2.5 px-3.5 text-center">Sentimen</th>
                  <th className="py-2.5 px-3.5 text-center">Risiko</th>
                  <th className="py-2.5 px-3.5 text-center">Status</th>
                  <th className="py-2.5 px-3.5 text-right">Aksi</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-100 dark:divide-white/[0.04]">
                {contents.map((item) => (
                  <tr
                    key={item.content_id}
                    onClick={() => navigate(`/contents/${item.content_id}`)}
                    className="hover:bg-slate-50 dark:hover:bg-white/[0.02] cursor-pointer transition-colors"
                  >
                    <td className="py-2.5 px-3.5 max-w-sm">
                      <div className="flex items-center gap-1.5 mb-0.5">
                        <PlatformBadge platform={item.platform} />
                        <span className="text-[10px] text-slate-400 font-mono">
                          {new Date(item.created_at).toLocaleDateString('id-ID')}
                        </span>
                      </div>
                      <div className="font-semibold text-slate-800 dark:text-slate-100 line-clamp-1">
                        {item.title || 'Tanpa Judul'}
                      </div>
                      <p className="text-[11px] text-slate-500 dark:text-slate-400 line-clamp-1 font-mono">
                        {item.caption_snippet || item.url}
                      </p>
                    </td>

                    <td className="py-2.5 px-3.5 font-mono">
                      <span className="text-blue-600 dark:text-blue-400 font-medium">
                        {item.author_username && ['x.com', 'instagram.com', 'facebook.com', 'twitter.com', 'tiktok.com'].includes(item.author_username.toLowerCase())
                          ? '@Anonim'
                          : (item.author_username && (item.author_username.endsWith('.com') || item.author_username.endsWith('.id'))
                            ? item.author_username
                            : `@${(item.author_username || 'Anonim').replace(/^@/, '')}`)}
                      </span>
                    </td>

                    <td className="py-2.5 px-3.5">
                      <div className="text-slate-700 dark:text-slate-200 font-medium">{item.category || 'Lainnya'}</div>
                      {item.issue_title && (
                        <div className="text-[10px] text-blue-500 line-clamp-1 font-mono">
                          {item.issue_title}
                        </div>
                      )}
                    </td>

                    <td className="py-2.5 px-3.5 text-center">
                      <SentimentBadge sentiment={item.sentiment} />
                    </td>

                    <td className="py-2.5 px-3.5 text-center">
                      <RiskBadge level={item.risk_level} />
                    </td>

                    <td className="py-2.5 px-3.5 text-center">
                      <StatusBadge status={item.status} />
                    </td>

                    <td className="py-2.5 px-3.5 text-right font-mono">
                      <span className="inline-flex items-center gap-1 text-slate-400 hover:text-blue-400 text-xs">
                        Periksa
                        <ArrowRight className="w-3 h-3" />
                      </span>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}
    </div>
  );
};
