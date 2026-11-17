import React, { useEffect, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { apiClient } from '../api/client';
import { ContentItem } from '../types';
import { PlatformBadge, RiskBadge, SentimentBadge, StatusBadge } from '../components/common/Badge';
import {
  Search,
  Filter,
  ArrowRight,
  AlertCircle,
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

  return (
    <div className="space-y-4 pb-10">
      {/* ── 1. HEADER RINGKAS ── */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 border-b border-slate-200 dark:border-white/[0.06] pb-3">
        <div>
          <div className="flex items-center gap-2 mb-1">
            <span className="font-mono text-[10px] tracking-widest text-blue-600 dark:text-blue-400 font-bold uppercase">
              ARSIP FORENSIK // TILIK
            </span>
            <span className="text-[10px] text-slate-300 dark:text-slate-700 font-mono">•</span>
            <span className="font-mono text-[10px] text-slate-400 dark:text-slate-500 uppercase">
              RANTAI BUKTI DIGITAL
            </span>
          </div>
          <h1 className="text-lg sm:text-xl font-bold tracking-tight text-slate-900 dark:text-white font-mono">
            Arsip Temuan Patroli
          </h1>
          <p className="text-xs text-slate-500 dark:text-slate-400 mt-0.5">
            Daftar seluruh barang bukti digital, hasil triase, dan rekam audit berstandar NIST FIPS 198-1
          </p>
        </div>
      </div>

      {/* ── 2. FILTER BAR RINGKAS ── */}
      <div className="cyber-card rounded-xl p-3 space-y-2 border border-slate-200 dark:border-white/[0.06]">
        <form onSubmit={handleSearchSubmit} className="flex flex-col sm:flex-row gap-2">
          <div className="relative flex-1">
            <input
              type="text"
              value={search}
              onChange={(e) => setSearch(e.target.value)}
              placeholder="Cari judul, kata kunci, akun, atau URL..."
              className="w-full pl-8 pr-3 py-1.5 bg-white dark:bg-[#0A0D14] border border-slate-200 dark:border-white/[0.08] rounded-lg text-xs text-slate-800 dark:text-slate-200 placeholder:text-slate-400 dark:placeholder:text-slate-600 focus:outline-none focus:ring-2 focus:ring-blue-500/20 focus:border-blue-500 transition-colors"
            />
            <Search className="w-3.5 h-3.5 text-slate-400 absolute left-2.5 top-2" />
          </div>

          <button
            type="submit"
            className="px-3.5 py-1.5 bg-blue-600 hover:bg-blue-500 active:scale-[0.98] text-white font-semibold text-xs rounded-lg transition-all flex items-center justify-center gap-1.5 shrink-0 font-mono shadow-xs"
          >
            <Filter className="w-3 h-3" /> Filter
          </button>
        </form>

        <div className="grid grid-cols-2 sm:grid-cols-4 gap-2 pt-0.5">
          <select
            value={platform}
            onChange={(e) => setPlatform(e.target.value)}
            className="bg-white dark:bg-[#0A0D14] border border-slate-200 dark:border-white/[0.08] rounded-lg py-1 px-2 text-xs text-slate-700 dark:text-slate-300 focus:outline-none focus:ring-2 focus:ring-blue-500/20 focus:border-blue-500 transition-colors"
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
            className="bg-white dark:bg-[#0A0D14] border border-slate-200 dark:border-white/[0.08] rounded-lg py-1 px-2 text-xs text-slate-700 dark:text-slate-300 focus:outline-none focus:ring-2 focus:ring-blue-500/20 focus:border-blue-500 transition-colors"
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
            className="bg-white dark:bg-[#0A0D14] border border-slate-200 dark:border-white/[0.08] rounded-lg py-1 px-2 text-xs text-slate-700 dark:text-slate-300 focus:outline-none focus:ring-2 focus:ring-blue-500/20 focus:border-blue-500 transition-colors"
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
            className="bg-white dark:bg-[#0A0D14] border border-slate-200 dark:border-white/[0.08] rounded-lg py-1 px-2 text-xs text-slate-700 dark:text-slate-300 focus:outline-none focus:ring-2 focus:ring-blue-500/20 focus:border-blue-500 transition-colors"
          >
            <option value="">Semua Status</option>
            <option value="WAITING_VALIDATION">Menunggu Validasi</option>
            <option value="VALIDATED">Tervalidasi</option>
            <option value="MODIFIED">Koreksi Analis</option>
            <option value="REJECTED">Bukan Pelanggaran</option>
          </select>
        </div>
      </div>

      {/* ── 3. TABEL DATA LINEAR-STYLE ── */}
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
        <div className="cyber-card rounded-xl p-10 sm:p-14 text-center border border-slate-200 dark:border-white/[0.06] space-y-3">
          <div className="w-12 h-12 rounded-xl bg-blue-500/10 border border-blue-500/20 text-blue-500 flex items-center justify-center mx-auto">
            <Search className="w-6 h-6" />
          </div>
          <div className="space-y-1">
            <h4 className="text-sm font-semibold text-slate-800 dark:text-slate-200 font-mono">
              {search || platform || category || sentiment || status
                ? 'Tidak Ada Temuan yang Sesuai Kriteria Filter'
                : 'Arsip Temuan Siap — Belum Ada Rekam Bukti'}
            </h4>
            <p className="text-xs text-slate-500 dark:text-slate-400 max-w-md mx-auto leading-relaxed">
              {search || platform || category || sentiment || status
                ? 'Coba sesuaikan kata kunci atau kosongkan filter pencarian untuk menampilkan seluruh arsip.'
                : 'Seluruh tangkapan layar, teks ekstraksi OCR, dan segel kriptografi NIST FIPS 198-1 HMAC-SHA256 akan otomatis tersimpan rapi di sini setelah akuisisi patroli.'}
            </p>
          </div>
          {(search || platform || category || sentiment || status) && (
            <button
              type="button"
              onClick={() => {
                setSearch('');
                setPlatform('');
                setCategory('');
                setSentiment('');
                setStatus('');
              }}
              className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-mono font-semibold bg-blue-600 hover:bg-blue-500 text-white transition-colors shadow-xs"
            >
              <span>Reset Seluruh Filter</span>
            </button>
          )}
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
