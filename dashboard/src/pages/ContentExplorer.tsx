import React, { useEffect, useState, useRef } from 'react';
import { Link } from 'react-router-dom';
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
      setError('Gagal memuat data konten patroli');
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
    setIntakeError(null);
    setIntakeSuccess(null);

    try {
      const res = await apiClient.assistant.intake({
        url: inputUrl.trim(),
        source_channel: 'WEB_DASHBOARD',
        reporter_identifier: 'Web-Console-Analyst',
        notes: inputNotes.trim() || undefined,
      });

      setIntakeSuccess(res);
      setInputUrl('');
      setInputNotes('');
      await fetchContents();
    } catch (err: any) {
      setIntakeError(err.response?.data?.detail || 'Gagal mengirim URL untuk triase.');
    } finally {
      setIsSubmittingIntake(false);
    }
  };

  return (
    <div className="space-y-5">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3">
        <div>
          <h2 className="text-base font-bold tracking-tight text-slate-900 dark:text-white flex items-center gap-2">
            <Layers className="w-5 h-5 text-blue-600 dark:text-blue-400" />
            Daftar Temuan & Bukti Digital
          </h2>
        </div>

        <div className="flex items-center gap-2 flex-wrap">
          {/* Single Download Dropdown Button */}
          <div className="relative" ref={exportMenuRef}>
            <button
              onClick={() => setShowExportMenu(!showExportMenu)}
              disabled={exportingFormat !== null}
              className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-semibold bg-white dark:bg-slate-900 text-slate-800 dark:text-slate-200 border border-slate-300 dark:border-slate-700 hover:border-blue-500 shadow-sm transition-all disabled:opacity-50"
              title="Unduh / Ekspor data temuan"
            >
              <Download className={`w-3.5 h-3.5 text-blue-600 dark:text-blue-400 ${exportingFormat ? 'animate-bounce' : ''}`} />
              <span>{exportingFormat ? `Mengunduh ${exportingFormat.toUpperCase()}...` : 'Ekspor'}</span>
              <ChevronDown className="w-3 h-3 text-slate-400" />
            </button>

            {showExportMenu && (
              <div className="absolute right-0 mt-1.5 w-52 rounded-xl bg-white dark:bg-[#0f1523] border border-slate-200 dark:border-slate-800 shadow-xl py-1.5 z-50 text-xs">
                <button
                  onClick={() => handleExport('pdf')}
                  className="w-full px-3.5 py-2 text-left flex items-start gap-2.5 hover:bg-slate-50 dark:hover:bg-slate-800 transition-colors"
                >
                  <FileText className="w-4 h-4 text-rose-500 shrink-0 mt-0.5" />
                  <div>
                    <div className="font-semibold text-slate-800 dark:text-slate-200">Laporan Resmi (PDF)</div>
                    <div className="text-[10px] text-slate-500">Berkas dossier lengkap & bukti visual</div>
                  </div>
                </button>
                <div className="border-t border-slate-100 dark:border-slate-800 my-1" />
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

          <button
            onClick={() => setShowIntakeForm(!showIntakeForm)}
            className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-semibold bg-blue-50 dark:bg-blue-600/20 text-blue-600 dark:text-blue-300 border border-blue-200 dark:border-blue-500/40 hover:bg-blue-100 dark:hover:bg-blue-600/30 transition-all"
          >
            <Zap className="w-3.5 h-3.5 text-blue-500 dark:text-blue-400" />
            {showIntakeForm ? 'Tutup Form' : '+ Input URL Temuan'}
          </button>
        </div>
      </div>

      {/* Direct Link Triage Form Card */}
      {showIntakeForm && (
        <div className="cyber-card rounded-xl p-4 border border-blue-400/40 dark:border-blue-500/30 shadow-md space-y-3">
          <div className="flex items-center justify-between border-b border-slate-200 dark:border-slate-800 pb-2">
            <div className="flex items-center gap-2">
              <div className="w-6 h-6 rounded-lg bg-blue-50 dark:bg-blue-600/15 border border-blue-200 dark:border-blue-500/30 flex items-center justify-center">
                <Link2 className="w-3.5 h-3.5 text-blue-600 dark:text-blue-400" />
              </div>
              <h3 className="text-xs font-bold text-slate-800 dark:text-slate-100">
                Input URL Temuan
              </h3>
            </div>
          </div>

          <form onSubmit={handleIntakeSubmit} className="space-y-3 pt-1">
            <div className="flex flex-col md:flex-row gap-2.5">
              <div className="flex-1 relative">
                <input
                  type="url"
                  required
                  value={inputUrl}
                  onChange={(e) => setInputUrl(e.target.value)}
                  placeholder="https://www.tiktok.com/@... atau https://youtu.be/... atau https://instagram.com/..."
                  className="w-full pl-9 pr-3 py-2 bg-white dark:bg-slate-950 border border-slate-300 dark:border-slate-700 rounded-lg text-xs text-slate-800 dark:text-white placeholder:text-slate-400 dark:placeholder:text-slate-500 focus:outline-none focus:border-blue-500 font-mono"
                />
                <Link2 className="w-4 h-4 text-slate-400 absolute left-3 top-2.5" />
              </div>

              <div className="md:w-1/3">
                <input
                  type="text"
                  value={inputNotes}
                  onChange={(e) => setInputNotes(e.target.value)}
                  placeholder="Catatan / keterangan isu (opsional)..."
                  className="w-full px-3 py-2 bg-white dark:bg-slate-950 border border-slate-300 dark:border-slate-700 rounded-lg text-xs text-slate-800 dark:text-white placeholder:text-slate-400 dark:placeholder:text-slate-500 focus:outline-none focus:border-blue-500"
                />
              </div>

              <button
                type="submit"
                disabled={isSubmittingIntake}
                className="px-4 py-2 bg-blue-600 hover:bg-blue-500 text-white font-semibold text-xs rounded-lg transition-all flex items-center justify-center gap-1.5 shadow-sm disabled:opacity-50 shrink-0"
              >
                <Zap className={`w-3.5 h-3.5 ${isSubmittingIntake ? 'animate-spin' : ''}`} />
                {isSubmittingIntake ? 'Menganalisis...' : 'Kirim Triase'}
              </button>
            </div>
          </form>

          {/* Sukses Alert */}
          {intakeSuccess && (
            <div className="p-3 rounded-lg bg-emerald-50 dark:bg-emerald-950/40 border border-emerald-200 dark:border-emerald-500/40 flex flex-col sm:flex-row items-start sm:items-center justify-between gap-2.5 text-xs">
              <div className="flex items-center gap-2 text-emerald-800 dark:text-emerald-300">
                <CheckCircle2 className="w-4 h-4 text-emerald-600 dark:text-emerald-400 shrink-0" />
                <span>
                  Tiket <strong className="font-mono text-emerald-700 dark:text-emerald-200">{intakeSuccess.ticket_number}</strong> berhasil dibuat!
                </span>
              </div>
              <div className="flex items-center gap-2">
                <Link
                  to={`/contents/${intakeSuccess.content_id}`}
                  className="px-2.5 py-1 bg-emerald-600 hover:bg-emerald-500 text-white font-semibold text-xs rounded flex items-center gap-1 transition-colors"
                >
                  <span>Buka Tiket</span>
                  <ExternalLink className="w-3 h-3" />
                </Link>
                <button
                  onClick={() => setIntakeSuccess(null)}
                  className="p-1 text-slate-400 hover:text-slate-600 dark:hover:text-white"
                >
                  <X className="w-3.5 h-3.5" />
                </button>
              </div>
            </div>
          )}

          {/* Error Alert */}
          {intakeError && (
            <div className="p-3 rounded-lg bg-rose-50 dark:bg-rose-950/40 border border-rose-200 dark:border-rose-500/40 flex items-center justify-between text-xs text-rose-700 dark:text-rose-300">
              <div className="flex items-center gap-2">
                <AlertCircle className="w-4 h-4 text-rose-600 dark:text-rose-400 shrink-0" />
                <span>{intakeError}</span>
              </div>
              <button onClick={() => setIntakeError(null)} className="text-slate-400 hover:text-slate-600 dark:hover:text-white">
                <X className="w-3.5 h-3.5" />
              </button>
            </div>
          )}
        </div>
      )}

      {/* Multi-Filter Bar */}
      <div className="cyber-card rounded-xl p-3.5 space-y-2.5">
        <form onSubmit={handleSearchSubmit} className="flex flex-col sm:flex-row gap-2">
          <div className="relative flex-1">
            <input
              type="text"
              value={search}
              onChange={(e) => setSearch(e.target.value)}
              placeholder="Cari judul, caption, akun, atau URL postingan..."
              className="w-full pl-9 pr-3 py-1.5 bg-white dark:bg-[#0c121e] border border-slate-200 dark:border-slate-800 rounded-lg text-xs text-slate-800 dark:text-slate-200 placeholder:text-slate-400 dark:placeholder:text-slate-500 focus:outline-none focus:border-blue-500 focus:ring-1 focus:ring-blue-500 transition-colors"
            />
            <Search className="w-3.5 h-3.5 text-slate-400 absolute left-3 top-2" />
          </div>

          <button
            type="submit"
            className="px-4 py-1.5 bg-blue-600 hover:bg-blue-500 text-white font-semibold text-xs rounded-lg transition-colors flex items-center justify-center gap-1.5 shrink-0 shadow-sm"
          >
            <Filter className="w-3 h-3" /> Cari
          </button>
        </form>

        <div className="grid grid-cols-2 sm:grid-cols-4 gap-2 pt-0.5">
          <select
            value={platform}
            onChange={(e) => setPlatform(e.target.value)}
            className="bg-white dark:bg-[#0c121e] border border-slate-200 dark:border-slate-800 rounded-lg py-1.5 px-2.5 text-xs text-slate-700 dark:text-slate-300 focus:outline-none focus:border-blue-500 focus:ring-1 focus:ring-blue-500 transition-colors"
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
            className="bg-white dark:bg-[#0c121e] border border-slate-200 dark:border-slate-800 rounded-lg py-1.5 px-2.5 text-xs text-slate-700 dark:text-slate-300 focus:outline-none focus:border-blue-500 focus:ring-1 focus:ring-blue-500 transition-colors"
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
            className="bg-white dark:bg-[#0c121e] border border-slate-200 dark:border-slate-800 rounded-lg py-1.5 px-2.5 text-xs text-slate-700 dark:text-slate-300 focus:outline-none focus:border-blue-500 focus:ring-1 focus:ring-blue-500 transition-colors"
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
            className="bg-white dark:bg-[#0c121e] border border-slate-200 dark:border-slate-800 rounded-lg py-1.5 px-2.5 text-xs text-slate-700 dark:text-slate-300 focus:outline-none focus:border-blue-500 focus:ring-1 focus:ring-blue-500 transition-colors"
          >
            <option value="">Semua Status</option>
            <option value="WAITING_VALIDATION">Menunggu Validasi</option>
            <option value="VALIDATED">Tervalidasi</option>
            <option value="MODIFIED">Koreksi Analis</option>
            <option value="REJECTED">Bukan Pelanggaran</option>
          </select>
        </div>
      </div>

      {/* Table Results */}
      {loading ? (
        <div className="cyber-card rounded-xl p-4 space-y-3">
          <div className="h-4 w-32 rounded skeleton-shimmer" />
          <div className="space-y-2">
            {[1, 2, 3, 4, 5].map((i) => (
              <div key={i} className="flex items-center gap-3 py-3 border-b border-slate-100 dark:border-slate-800/60 last:border-0">
                <div className="h-3 w-28 rounded skeleton-shimmer" />
                <div className="h-3 flex-1 rounded skeleton-shimmer" />
                <div className="h-4 w-16 rounded-md skeleton-shimmer" />
                <div className="h-4 w-16 rounded-md skeleton-shimmer" />
              </div>
            ))}
          </div>
        </div>
      ) : error ? (
        <div className="p-8 cyber-card rounded-xl text-center">
          <AlertCircle className="w-8 h-8 text-rose-500 mx-auto mb-2" />
          <p className="text-rose-600 dark:text-rose-300 text-sm font-semibold">{error}</p>
        </div>
      ) : contents.length === 0 ? (
        <div className="cyber-card rounded-xl p-10 text-center text-slate-400">
          <Layers className="w-8 h-8 text-slate-400 mx-auto mb-2" />
          <h3 className="text-xs font-semibold text-slate-600 dark:text-slate-300">Belum ada konten yang sesuai</h3>
          <p className="text-[11px] text-slate-400 mt-0.5">Sesuaikan kata kunci atau filter di atas.</p>
        </div>
      ) : (
        <div className="cyber-card rounded-xl overflow-hidden">
          <div className="overflow-x-auto">
            <table className="w-full text-left text-xs">
              <thead className="bg-slate-100 dark:bg-slate-900/90 text-slate-600 dark:text-slate-400 uppercase text-[10px] font-semibold tracking-wider border-b border-slate-200 dark:border-slate-800">
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
              <tbody className="divide-y divide-slate-100 dark:divide-slate-800/60 font-medium">
                {contents.map((item) => (
                  <tr key={item.content_id} className="hover:bg-slate-50 dark:hover:bg-slate-800/30 transition-colors">
                    <td className="py-3 px-3.5 max-w-sm">
                      <div className="flex items-center gap-1.5 mb-0.5">
                        <PlatformBadge platform={item.platform} />
                        <span className="text-[10px] text-slate-400 font-mono">
                          {new Date(item.created_at).toLocaleDateString('id-ID')}
                        </span>
                      </div>
                      <div className="font-semibold text-slate-800 dark:text-slate-100 line-clamp-1">
                        {item.title || 'Tanpa Judul'}
                      </div>
                      <p className="text-[11px] text-slate-500 dark:text-slate-400 line-clamp-1">
                        {item.caption_snippet || item.url}
                      </p>
                    </td>

                    <td className="py-3 px-3.5">
                      <span className="font-mono text-blue-600 dark:text-blue-300 font-semibold">
                        {item.author_username && ['x.com', 'instagram.com', 'facebook.com', 'twitter.com', 'tiktok.com'].includes(item.author_username.toLowerCase())
                          ? '@Anonim'
                          : (item.author_username && (item.author_username.endsWith('.com') || item.author_username.endsWith('.id'))
                              ? item.author_username
                              : `@${(item.author_username || 'Anonim').replace(/^@/, '')}`)}
                      </span>
                    </td>

                    <td className="py-3 px-3.5">
                      <div className="text-slate-700 dark:text-slate-200 font-medium">{item.category || 'Lainnya'}</div>
                      {item.issue_title && (
                        <div className="text-[10px] text-blue-600 dark:text-blue-400 line-clamp-1">
                          {item.issue_title}
                        </div>
                      )}
                    </td>

                    <td className="py-3 px-3.5 text-center">
                      <SentimentBadge sentiment={item.sentiment} />
                    </td>

                    <td className="py-3 px-3.5 text-center">
                      <RiskBadge level={item.risk_level} />
                    </td>

                    <td className="py-3 px-3.5 text-center">
                      <StatusBadge status={item.status} />
                    </td>

                    <td className="py-3 px-3.5 text-right">
                      <Link
                        to={`/contents/${item.content_id}`}
                        className="inline-flex items-center gap-1 px-2.5 py-1 rounded-md bg-slate-100 hover:bg-slate-200 dark:bg-slate-800 dark:hover:bg-slate-700 text-blue-600 dark:text-blue-400 text-xs font-semibold transition-colors border border-slate-200 dark:border-slate-700"
                      >
                        Periksa
                        <ArrowRight className="w-3 h-3" />
                      </Link>
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
