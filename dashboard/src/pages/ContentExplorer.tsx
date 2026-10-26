import React, { useEffect, useState } from 'react';
import { Link } from 'react-router-dom';
import { apiClient } from '../api/client';
import { ContentItem } from '../types';
import { PlatformBadge, RiskBadge, SentimentBadge, StatusBadge } from '../components/common/Badge';
import { Search, Filter, ArrowRight, Layers, AlertCircle, RefreshCw } from 'lucide-react';

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

  return (
    <div className="space-y-6">
      {/* Header */}
      <div>
        <h2 className="text-xl font-bold tracking-tight text-white flex items-center gap-2">
          <Layers className="w-5 h-5 text-cyan-400" />
          Penjelajah Konten & Bukti Digital Patroli
        </h2>
        <p className="text-xs text-slate-400 mt-1">
          Eksplorasi seluruh konten yang diunggah dan dianalisis melalui Telegram Bot maupun API.
        </p>
      </div>

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
          </select>

          {/* Kategori */}
          <select
            value={category}
            onChange={(e) => setCategory(e.target.value)}
            className="bg-slate-900 border border-slate-800 rounded-lg py-1.5 px-3 text-xs text-slate-300 focus:outline-none focus:border-cyan-500 font-medium"
          >
            <option value="">Semua Kategori</option>
            <option value="HOAKS">HOAKS</option>
            <option value="DI_LUAR_KONTEKS">DI_LUAR_KONTEKS</option>
            <option value="UJARAN_KEBENCIAN">UJARAN_KEBENCIAN</option>
            <option value="PROVOKASI_SARA">PROVOKASI_SARA</option>
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
