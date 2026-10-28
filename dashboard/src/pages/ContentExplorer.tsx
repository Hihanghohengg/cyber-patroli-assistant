import React, { useEffect, useState } from 'react';
import { Link } from 'react-router-dom';
import { apiClient } from '../api/client';
import { ContentItem } from '../types';
import { PlatformBadge, RiskBadge, SentimentBadge, StatusBadge } from '../components/common/Badge';
import { Search, Filter, ArrowRight, Layers, AlertCircle, RefreshCw, Zap, Plus, Link2, CheckCircle2, ExternalLink, X } from 'lucide-react';

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
  const [showIntakeForm, setShowIntakeForm] = useState<boolean>(true);
  const [inputUrl, setInputUrl] = useState<string>('');
  const [inputNotes, setInputNotes] = useState<string>('');
  const [isSubmittingIntake, setIsSubmittingIntake] = useState<boolean>(false);
  const [intakeSuccess, setIntakeSuccess] = useState<any | null>(null);
  const [intakeError, setIntakeError] = useState<string | null>(null);

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
      // Refresh daftar konten seketika
      await fetchContents();
    } catch (err: any) {
      setIntakeError(err.response?.data?.detail || 'Gagal mengirim URL untuk triase.');
    } finally {
      setIsSubmittingIntake(false);
    }
  };

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <h2 className="text-lg font-bold tracking-tight text-white flex items-center gap-2">
            <Layers className="w-5 h-5 text-cyan-400" />
            Daftar Temuan & Bukti Digital
          </h2>
          <p className="text-xs text-slate-400 mt-0.5">
            Eksplorasi konten media sosial, status validasi bukti digital, dan analisis 5W+1H.
          </p>
        </div>

        <button
          onClick={() => setShowIntakeForm(!showIntakeForm)}
          className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-semibold bg-cyan-600/20 text-cyan-300 border border-cyan-500/40 hover:bg-cyan-600/30 transition-all self-start sm:self-auto"
        >
          <Zap className="w-3.5 h-3.5 text-cyan-400" />
          {showIntakeForm ? 'Tutup Form' : '+ Input URL Temuan'}
        </button>
      </div>

      {/* Direct Link Triage Form Card */}
      {showIntakeForm && (
        <div className="cyber-card rounded-xl p-4 border border-cyan-500/30 bg-gradient-to-r from-slate-900/90 via-[#070b14] to-cyan-950/20 shadow-md space-y-3">
          <div className="flex items-center justify-between border-b border-slate-800 pb-2.5">
            <div className="flex items-center gap-2">
              <div className="w-6 h-6 rounded-lg bg-cyan-500/10 border border-cyan-500/30 flex items-center justify-center">
                <Link2 className="w-3.5 h-3.5 text-cyan-400" />
              </div>
              <div>
                <h3 className="text-xs font-bold text-slate-100 flex items-center gap-2">
                  Input URL Temuan
                </h3>
                <p className="text-[11px] text-slate-400">
                  Masukkan link konten media sosial untuk ekstraksi bukti digital dan triase AI otomatis.
                </p>
              </div>
            </div>
          </div>

          <form onSubmit={handleIntakeSubmit} className="space-y-3 pt-1">
            <div className="flex flex-col md:flex-row gap-3">
              <div className="flex-1 relative">
                <input
                  type="url"
                  required
                  value={inputUrl}
                  onChange={(e) => setInputUrl(e.target.value)}
                  placeholder="https://www.tiktok.com/@... atau https://youtu.be/... atau https://x.com/..."
                  className="w-full pl-9 pr-4 py-2 bg-slate-950 border border-slate-700 rounded-lg text-xs text-white placeholder:text-slate-500 focus:outline-none focus:border-cyan-400 font-mono"
                />
                <Link2 className="w-4 h-4 text-slate-500 absolute left-3 top-2.5" />
              </div>

              <div className="md:w-1/3">
                <input
                  type="text"
                  value={inputNotes}
                  onChange={(e) => setInputNotes(e.target.value)}
                  placeholder="Catatan / keterangan isu (opsional)..."
                  className="w-full px-3 py-2 bg-slate-950 border border-slate-700 rounded-lg text-xs text-white placeholder:text-slate-500 focus:outline-none focus:border-cyan-400"
                />
              </div>

              <button
                type="submit"
                disabled={isSubmittingIntake}
                className="px-5 py-2 bg-cyan-600 hover:bg-cyan-500 text-white font-semibold text-xs rounded-lg transition-all flex items-center justify-center gap-2 shadow-md shadow-cyan-600/30 disabled:opacity-50 shrink-0"
              >
                <Zap className={`w-3.5 h-3.5 ${isSubmittingIntake ? 'animate-spin' : ''}`} />
                {isSubmittingIntake ? 'Menganalisis AI...' : '⚡ Kirim & Triase AI'}
              </button>
            </div>
          </form>

          {/* Sukses Alert */}
          {intakeSuccess && (
            <div className="p-3.5 rounded-lg bg-emerald-950/40 border border-emerald-500/40 flex flex-col sm:flex-row items-start sm:items-center justify-between gap-3 text-xs animate-fade-in">
              <div className="flex items-center gap-2 text-emerald-300">
                <CheckCircle2 className="w-4 h-4 text-emerald-400 shrink-0" />
                <span>
                  Tiket <strong className="font-mono text-emerald-200">{intakeSuccess.ticket_number}</strong> berhasil dibuat dan langsung terdaftar di antrean web!
                </span>
              </div>
              <div className="flex items-center gap-2">
                <Link
                  to={`/contents/${intakeSuccess.content_id}`}
                  className="px-3 py-1 bg-emerald-600 hover:bg-emerald-500 text-white font-semibold text-xs rounded flex items-center gap-1.5 transition-colors"
                >
                  <span>Buka Detail Tiket</span>
                  <ExternalLink className="w-3 h-3" />
                </Link>
                <button
                  onClick={() => setIntakeSuccess(null)}
                  className="p-1 text-slate-400 hover:text-white"
                  title="Tutup Notifikasi"
                >
                  <X className="w-3.5 h-3.5" />
                </button>
              </div>
            </div>
          )}

          {/* Error Alert */}
          {intakeError && (
            <div className="p-3 rounded-lg bg-rose-950/40 border border-rose-500/40 flex items-center justify-between text-xs text-rose-300">
              <div className="flex items-center gap-2">
                <AlertCircle className="w-4 h-4 text-rose-400 shrink-0" />
                <span>{intakeError}</span>
              </div>
              <button onClick={() => setIntakeError(null)} className="text-slate-400 hover:text-white">
                <X className="w-3.5 h-3.5" />
              </button>
            </div>
          )}
        </div>
      )}


      {/* Multi-Filter Bar */}
      <div className="cyber-card rounded-xl p-4 space-y-3">
        <form onSubmit={handleSearchSubmit} className="flex flex-col md:flex-row gap-3">
          <div className="relative flex-1">
            <input
              type="text"
              value={search}
              onChange={(e) => setSearch(e.target.value)}
              placeholder="Cari judul, caption, atau URL postingan..."
              className="w-full pl-9 pr-4 py-2 bg-slate-900 border border-slate-800 rounded-lg text-xs text-slate-200 placeholder:text-slate-500 focus:outline-none focus:border-cyan-500"
            />
            <Search className="w-4 h-4 text-slate-500 absolute left-3 top-2.5" />
          </div>

          <button
            type="submit"
            className="px-4 py-2 bg-cyan-600 hover:bg-cyan-500 text-white font-semibold text-xs rounded-lg transition-colors flex items-center justify-center gap-1.5"
          >
            <Filter className="w-3.5 h-3.5" /> Filter Temuan
          </button>
        </form>

        <div className="grid grid-cols-2 sm:grid-cols-4 gap-3 pt-1">
          {/* Platform */}
          <select
            value={platform}
            onChange={(e) => setPlatform(e.target.value)}
            className="bg-slate-900 border border-slate-800 rounded-lg py-1.5 px-3 text-xs text-slate-300 focus:outline-none focus:border-cyan-500 font-medium"
          >
            <option value="">Semua Platform</option>
            <option value="youtube">YouTube</option>
            <option value="tiktok">TikTok</option>
            <option value="instagram">Instagram</option>
            <option value="x">X / Twitter</option>
          </select>

          {/* Kategori */}
          <select
            value={category}
            onChange={(e) => setCategory(e.target.value)}
            className="bg-slate-900 border border-slate-800 rounded-lg py-1.5 px-3 text-xs text-slate-300 focus:outline-none focus:border-cyan-500 font-medium"
          >
            <option value="">Semua Kategori</option>
            <option value="Kejahatan Finansial">Kejahatan Finansial</option>
            <option value="Perjudian Daring">Perjudian Daring</option>
            <option value="Disinformasi Politik & Kebijakan Publik">Disinformasi Politik</option>
            <option value="Hoaks Kesehatan & Pangan">Hoaks Kesehatan & Pangan</option>
            <option value="Klarifikasi & Edukasi Resmi">Klarifikasi Resmi</option>
          </select>

          {/* Sentimen */}
          <select
            value={sentiment}
            onChange={(e) => setSentiment(e.target.value)}
            className="bg-slate-900 border border-slate-800 rounded-lg py-1.5 px-3 text-xs text-slate-300 focus:outline-none focus:border-cyan-500 font-medium"
          >
            <option value="">Semua Sentimen</option>
            <option value="POSITIF">Positif</option>
            <option value="NEGATIF">Negatif</option>
            <option value="NETRAL">Netral</option>
            <option value="CAMPURAN">Campuran</option>
          </select>

          {/* Status Validasi 7 Siklus Tiket */}
          <select
            value={status}
            onChange={(e) => setStatus(e.target.value)}
            className="bg-slate-900 border border-slate-800 rounded-lg py-1.5 px-3 text-xs text-slate-300 focus:outline-none focus:border-cyan-500 font-medium"
          >
            <option value="">Semua Status</option>
            <option value="WAITING_VALIDATION">Menunggu Validasi</option>
            <option value="VALIDATED">Tervalidasi (Setuju)</option>
            <option value="MODIFIED">Koreksi Analis (Diubah)</option>
            <option value="REJECTED">Bukan Pelanggaran (Ditolak)</option>
            <option value="MANUAL_FALLBACK">Fallback Manual</option>
            <option value="PENDING_ANALYSIS">Dalam Antrean</option>
            <option value="FAILED">Gagal Analisis</option>
          </select>
        </div>
      </div>

      {/* Table Results */}
      {loading ? (
        <div className="flex flex-col items-center justify-center min-h-[40vh] gap-3">
          <div className="w-8 h-8 border-2 border-cyan-400 border-t-transparent rounded-full animate-spin" />
          <span className="text-xs font-mono text-cyan-400">MEMUAT DAFTAR KONTEN...</span>
        </div>
      ) : error ? (
        <div className="p-8 cyber-card rounded-xl text-center">
          <AlertCircle className="w-8 h-8 text-rose-400 mx-auto mb-2" />
          <p className="text-rose-300 text-sm font-semibold">{error}</p>
        </div>
      ) : contents.length === 0 ? (
        <div className="cyber-card rounded-xl p-12 text-center text-slate-400">
          <Layers className="w-10 h-10 text-slate-600 mx-auto mb-3" />
          <h3 className="text-sm font-semibold text-slate-300">Belum ada konten yang sesuai</h3>
          <p className="text-xs text-slate-500 mt-1">Coba sesuaikan kata kunci pencarian atau reset filter.</p>
        </div>
      ) : (
        <div className="cyber-card rounded-xl overflow-hidden">
          <div className="overflow-x-auto">
            <table className="w-full text-left text-xs">
              <thead className="bg-slate-900/90 text-slate-400 uppercase text-[10px] font-semibold tracking-wider border-b border-slate-800">
                <tr>
                  <th className="py-3 px-4">Platform & Judul</th>
                  <th className="py-3 px-4">Akun Sumber</th>
                  <th className="py-3 px-4">Kategori & Isu</th>
                  <th className="py-3 px-4 text-center">Sentimen</th>
                  <th className="py-3 px-4 text-center">Tingkat Risiko</th>
                  <th className="py-3 px-4 text-center">Status</th>
                  <th className="py-3 px-4 text-right">Aksi</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-800/60 font-medium">
                {contents.map((item) => (
                  <tr key={item.content_id} className="hover:bg-slate-800/30 transition-colors">
                    <td className="py-3.5 px-4 max-w-sm">
                      <div className="flex items-center gap-2 mb-1">
                        <PlatformBadge platform={item.platform} />
                        <span className="text-[10px] text-slate-500 font-mono">
                          {new Date(item.created_at).toLocaleDateString('id-ID')}
                        </span>
                      </div>
                      <div className="font-semibold text-slate-100 line-clamp-1">
                        {item.title || 'Tanpa Judul'}
                      </div>
                      <p className="text-[11px] text-slate-400 line-clamp-1 mt-0.5">
                        {item.caption_snippet || item.url}
                      </p>
                    </td>

                    <td className="py-3.5 px-4">
                      <span className="font-mono text-cyan-300 font-semibold">
                        @{item.author_username || 'Anonim'}
                      </span>
                    </td>

                    <td className="py-3.5 px-4">
                      <div className="text-slate-200 font-medium">{item.category || 'Lainnya'}</div>
                      {item.issue_title && (
                        <div className="text-[10px] text-cyan-400 line-clamp-1 mt-0.5">
                          Topik: {item.issue_title}
                        </div>
                      )}
                    </td>

                    <td className="py-3.5 px-4 text-center">
                      <SentimentBadge sentiment={item.sentiment} />
                    </td>

                    <td className="py-3.5 px-4 text-center">
                      <RiskBadge level={item.risk_level} />
                    </td>

                    <td className="py-3.5 px-4 text-center">
                      <StatusBadge status={item.status} />
                    </td>

                    <td className="py-3.5 px-4 text-right">
                      <Link
                        to={`/contents/${item.content_id}`}
                        className="inline-flex items-center gap-1 px-3 py-1.5 rounded-lg bg-slate-800 hover:bg-slate-700 text-cyan-400 text-xs font-semibold transition-colors border border-slate-700"
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
