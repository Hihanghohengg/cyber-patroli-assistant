import React, { useState, useEffect } from 'react';
import {
  Send,
  Chrome,
  MessageCircle,
  LayoutDashboard,
  CheckCircle2,
  Clock,
  ExternalLink,
  ShieldCheck,
  Zap,
  ArrowRight,
  Copy,
  Check,
} from 'lucide-react';
import axios from 'axios';

interface ChannelInfo {
  id: string;
  name: string;
  type: string;
  status: string;
  intake_count: number;
  features: string[];
  icon: string;
}

export const OmnichannelAssistantPage: React.FC = () => {
  const [channels, setChannels] = useState<ChannelInfo[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [copiedPath, setCopiedPath] = useState(false);

  // Form State
  const [testUrl, setTestUrl] = useState('');
  const [selectedChannel, setSelectedChannel] = useState('BROWSER_EXTENSION');
  const [operatorId, setOperatorId] = useState('Analyst-01');
  const [notes, setNotes] = useState('');
  const [submitting, setSubmitting] = useState(false);
  const [submitResult, setSubmitResult] = useState<any>(null);
  const [submitError, setSubmitError] = useState<string | null>(null);

  const extensionPath = 'd:\\Obed\\mini project\\cyber-patrol-assistant\\extension';

  useEffect(() => {
    fetchChannels();
  }, []);

  const fetchChannels = async () => {
    try {
      setIsLoading(true);
      const res = await axios.get('/api/v1/assistant/channels');
      if (res.data && res.data.channels) {
        setChannels(res.data.channels);
      }
    } catch (err) {
      console.error('Failed to fetch assistant channels:', err);
    } finally {
      setIsLoading(false);
    }
  };

  const handleCopyPath = () => {
    navigator.clipboard.writeText(extensionPath);
    setCopiedPath(true);
    setTimeout(() => setCopiedPath(false), 2500);
  };

  const handleSubmitIntake = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!testUrl.trim()) return;

    setSubmitting(true);
    setSubmitError(null);
    setSubmitResult(null);

    try {
      const res = await axios.post('/api/v1/assistant/intake', {
        url: testUrl.trim(),
        source_channel: selectedChannel,
        reporter_identifier: operatorId.trim() || 'Analyst-Console',
        notes: notes.trim() || undefined,
      });
      setSubmitResult(res.data);
      setTestUrl('');
      setNotes('');
      fetchChannels();
    } catch (err: any) {
      setSubmitError(err.response?.data?.detail || 'Gagal memproses intake patroli.');
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 border-b border-slate-800 pb-5">
        <div>
          <div className="flex items-center gap-2">
            <span className="px-2.5 py-0.5 rounded-full text-[11px] font-semibold bg-cyan-500/10 text-cyan-400 border border-cyan-500/20">
              Arsitektur Modular Terpadu
            </span>
            <span className="text-xs text-slate-400 font-mono">Omnichannel Assistant Gateway v3.0</span>
          </div>
          <h1 className="text-2xl font-bold text-white mt-1">Asisten Patroli Siber Multi-Kanal</h1>
          <p className="text-sm text-slate-400 mt-0.5">
            Integrasi multi-antarmuka terhubung ke satu Core Intelligence Engine (FastAPI + AI Gemini 5W+1H + RAG Preseden).
          </p>
        </div>
      </div>

      {/* Grid Kanal */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
        {/* Telegram */}
        <div className="p-4 rounded-xl bg-slate-900/60 border border-cyan-500/30 shadow-lg shadow-cyan-950/20 relative overflow-hidden">
          <div className="absolute top-0 right-0 w-24 h-24 bg-cyan-500/5 rounded-full blur-xl pointer-events-none" />
          <div className="flex items-center justify-between mb-3">
            <div className="p-2.5 rounded-lg bg-cyan-500/10 text-cyan-400 border border-cyan-500/20">
              <Send className="w-5 h-5" />
            </div>
            <span className="px-2 py-0.5 rounded text-[10px] font-bold bg-emerald-500/10 text-emerald-400 border border-emerald-500/20 flex items-center gap-1">
              <span className="w-1.5 h-1.5 rounded-full bg-emerald-400 animate-pulse" />
              ONLINE
            </span>
          </div>
          <h3 className="font-semibold text-white text-sm">Telegram Bot</h3>
          <p className="text-xs text-slate-400 mt-1">
            Kanal operasional lapangan untuk pelaporan cepat, approval tombol inline, dan rekapitulasi DOCX.
          </p>
          <div className="mt-4 pt-3 border-t border-slate-800 text-[11px] text-slate-400 space-y-1">
            <div className="flex justify-between">
              <span>Peran RBAC:</span>
              <span className="text-cyan-300 font-mono">3 Level (Op/An/Adm)</span>
            </div>
            <div className="flex justify-between">
              <span>Status:</span>
              <span className="text-emerald-400 font-medium">Long-Polling Aktif</span>
            </div>
          </div>
        </div>

        {/* Chrome Extension */}
        <div className="p-4 rounded-xl bg-slate-900/60 border border-blue-500/30 shadow-lg shadow-blue-950/20 relative overflow-hidden">
          <div className="absolute top-0 right-0 w-24 h-24 bg-blue-500/5 rounded-full blur-xl pointer-events-none" />
          <div className="flex items-center justify-between mb-3">
            <div className="p-2.5 rounded-lg bg-blue-500/10 text-blue-400 border border-blue-500/20">
              <Chrome className="w-5 h-5" />
            </div>
            <span className="px-2 py-0.5 rounded text-[10px] font-bold bg-blue-500/10 text-blue-400 border border-blue-500/20 flex items-center gap-1">
              <span className="w-1.5 h-1.5 rounded-full bg-blue-400" />
              EKSTENSI AKTIF
            </span>
          </div>
          <h3 className="font-semibold text-white text-sm">Browser Extension</h3>
          <p className="text-xs text-slate-400 mt-1">
            Ekstensi Chrome/Edge Manifest V3: 1-click capture, floating triage button, dan context menu di medsos.
          </p>
          <div className="mt-4 pt-3 border-t border-slate-800 text-[11px] text-slate-400 space-y-1">
            <div className="flex justify-between">
              <span>Mode:</span>
              <span className="text-blue-300 font-mono">Manifest V3</span>
            </div>
            <div className="flex justify-between">
              <span>Platform Target:</span>
              <span className="text-slate-300 font-medium">TikTok, YT, IG, X</span>
            </div>
          </div>
        </div>

        {/* WhatsApp */}
        <div className="p-4 rounded-xl bg-slate-900/60 border border-emerald-500/30 shadow-lg shadow-emerald-950/20 relative overflow-hidden">
          <div className="absolute top-0 right-0 w-24 h-24 bg-emerald-500/5 rounded-full blur-xl pointer-events-none" />
          <div className="flex items-center justify-between mb-3">
            <div className="p-2.5 rounded-lg bg-emerald-500/10 text-emerald-400 border border-emerald-500/20">
              <MessageCircle className="w-5 h-5" />
            </div>
            <span className="px-2 py-0.5 rounded text-[10px] font-bold bg-emerald-500/10 text-emerald-400 border border-emerald-500/20 flex items-center gap-1">
              <span className="w-1.5 h-1.5 rounded-full bg-emerald-400" />
              GATEWAY READY
            </span>
          </div>
          <h3 className="font-semibold text-white text-sm">WhatsApp Gateway</h3>
          <p className="text-xs text-slate-400 mt-1">
            Inbound webhook untuk parsing link medsos dari chat WhatsApp dan balasan terformat otomatis.
          </p>
          <div className="mt-4 pt-3 border-t border-slate-800 text-[11px] text-slate-400 space-y-1">
            <div className="flex justify-between">
              <span>Endpoint:</span>
              <span className="text-emerald-300 font-mono text-[10px]">/whatsapp/webhook</span>
            </div>
            <div className="flex justify-between">
              <span>Kompabilitas:</span>
              <span className="text-slate-300 font-medium">Twilio / Meta API</span>
            </div>
          </div>
        </div>

        {/* Web Console */}
        <div className="p-4 rounded-xl bg-slate-900/60 border border-purple-500/30 shadow-lg shadow-purple-950/20 relative overflow-hidden">
          <div className="absolute top-0 right-0 w-24 h-24 bg-purple-500/5 rounded-full blur-xl pointer-events-none" />
          <div className="flex items-center justify-between mb-3">
            <div className="p-2.5 rounded-lg bg-purple-500/10 text-purple-400 border border-purple-500/20">
              <LayoutDashboard className="w-5 h-5" />
            </div>
            <span className="px-2 py-0.5 rounded text-[10px] font-bold bg-purple-500/10 text-purple-400 border border-purple-500/20 flex items-center gap-1">
              <span className="w-1.5 h-1.5 rounded-full bg-purple-400" />
              CONNECTED
            </span>
          </div>
          <h3 className="font-semibold text-white text-sm">Web Command Console</h3>
          <p className="text-xs text-slate-400 mt-1">
            Konsol web terpusat untuk eksplorasi visual, drill-down analitik, validasi analis, dan kurasi data.
          </p>
          <div className="mt-4 pt-3 border-t border-slate-800 text-[11px] text-slate-400 space-y-1">
            <div className="flex justify-between">
              <span>Tampilan:</span>
              <span className="text-purple-300 font-mono">React + Vite</span>
            </div>
            <div className="flex justify-between">
              <span>Hak Akses:</span>
              <span className="text-slate-300 font-medium">USER vs ADMIN</span>
            </div>
          </div>
        </div>
      </div>

      {/* Detail Bagian Bawah: Panduan Ekstensi & Form Simulasi Intake */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Panduan Pemasangan Ekstensi Browser */}
        <div className="p-5 rounded-xl bg-slate-900/80 border border-slate-800 space-y-4">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-2 text-blue-400">
              <Chrome className="w-5 h-5" />
              <h2 className="text-base font-semibold text-white">Panduan Pasang Ekstensi Browser</h2>
            </div>
            <span className="px-2 py-0.5 rounded text-[11px] font-semibold bg-blue-500/10 text-blue-400 border border-blue-500/20">
              Chrome & Edge
            </span>
          </div>

          <p className="text-xs text-slate-300 leading-relaxed">
            Ekstensi telah dikompilasi lengkap dalam repositori proyek. Anda dapat langsung menginstalnya di browser tanpa build tambahan:
          </p>

          <ol className="text-xs text-slate-300 space-y-2.5 list-decimal list-inside bg-[#070b14] p-4 rounded-lg border border-slate-800">
            <li>
              Buka menu ekstensi di peramban: <code className="text-cyan-400 bg-slate-900 px-1.5 py-0.5 rounded font-mono">chrome://extensions</code> atau <code className="text-cyan-400 bg-slate-900 px-1.5 py-0.5 rounded font-mono">edge://extensions</code>
            </li>
            <li>
              Nyalakan toggle <strong>Developer mode</strong> (Mode Pengembang) di pojok kanan atas.
            </li>
            <li>
              Klik tombol <strong>Load unpacked</strong> (Muat yang belum dibongkar).
            </li>
            <li>
              Pilih folder ekstensi pada proyek ini:
            </li>
          </ol>

          <div className="flex items-center gap-2 bg-[#070b14] p-2.5 rounded-lg border border-slate-800 font-mono text-xs text-slate-300">
            <span className="truncate flex-1 text-cyan-400">{extensionPath}</span>
            <button
              onClick={handleCopyPath}
              className="px-2.5 py-1.5 rounded bg-slate-800 hover:bg-slate-700 text-slate-200 text-xs flex items-center gap-1 transition-colors shrink-0"
            >
              {copiedPath ? <Check className="w-3.5 h-3.5 text-emerald-400" /> : <Copy className="w-3.5 h-3.5" />}
              <span>{copiedPath ? 'Tersalin' : 'Salin Path'}</span>
            </button>
          </div>

          <div className="p-3 rounded-lg bg-blue-500/10 border border-blue-500/20 text-xs text-blue-300 flex items-start gap-2">
            <Zap className="w-4 h-4 text-blue-400 shrink-0 mt-0.5" />
            <span>
              Setelah dipasang, analis cukup membuka halaman video TikTok/YouTube lalu mengklik ikon ekstensi di toolbar untuk melakukan triase 1-click.
            </span>
          </div>
        </div>

        {/* Form Uji Coba Intake Multi-Kanal */}
        <div className="p-5 rounded-xl bg-slate-900/80 border border-slate-800 space-y-4">
          <div className="flex items-center gap-2 text-cyan-400">
            <Zap className="w-5 h-5" />
            <h2 className="text-base font-semibold text-white">Uji Intake Multi-Kanal (Live Simulation)</h2>
          </div>

          <p className="text-xs text-slate-300">
            Simulasikan pengiriman laporan konten mencurigakan melalui salah satu kanal yang dipilih:
          </p>

          <form onSubmit={handleSubmitIntake} className="space-y-3.5">
            <div>
              <label className="block text-xs font-semibold text-slate-300 mb-1">
                Kanal Intake Pengirim
              </label>
              <select
                value={selectedChannel}
                onChange={(e) => setSelectedChannel(e.target.value)}
                className="w-full bg-[#070b14] border border-slate-700 rounded-lg px-3 py-2 text-xs text-white focus:outline-none focus:border-cyan-500"
              >
                <option value="BROWSER_EXTENSION">Chrome / Edge Browser Extension</option>
                <option value="WHATSAPP">WhatsApp Assistant Gateway</option>
                <option value="TELEGRAM">Telegram Bot Assistant</option>
                <option value="WEB_DASHBOARD">Web Command Console (Direct Intake)</option>
              </select>
            </div>

            <div>
              <label className="block text-xs font-semibold text-slate-300 mb-1">
                URL Postingan Target (TikTok / YouTube / Instagram)
              </label>
              <input
                type="url"
                required
                value={testUrl}
                onChange={(e) => setTestUrl(e.target.value)}
                placeholder="https://www.tiktok.com/@akun_target/video/123456789"
                className="w-full bg-[#070b14] border border-slate-700 rounded-lg px-3 py-2 text-xs text-white placeholder-slate-500 focus:outline-none focus:border-cyan-500"
              />
            </div>

            <div className="grid grid-cols-2 gap-3">
              <div>
                <label className="block text-xs font-semibold text-slate-300 mb-1">
                  Identitas Pelapor
                </label>
                <input
                  type="text"
                  value={operatorId}
                  onChange={(e) => setOperatorId(e.target.value)}
                  placeholder="ID / No Telp Pelapor"
                  className="w-full bg-[#070b14] border border-slate-700 rounded-lg px-3 py-2 text-xs text-white placeholder-slate-500 focus:outline-none focus:border-cyan-500"
                />
              </div>

              <div>
                <label className="block text-xs font-semibold text-slate-300 mb-1">
                  Catatan Analis (Opsional)
                </label>
                <input
                  type="text"
                  value={notes}
                  onChange={(e) => setNotes(e.target.value)}
                  placeholder="Misal: Hoaks provokatif"
                  className="w-full bg-[#070b14] border border-slate-700 rounded-lg px-3 py-2 text-xs text-white placeholder-slate-500 focus:outline-none focus:border-cyan-500"
                />
              </div>
            </div>

            <button
              type="submit"
              disabled={submitting}
              className="w-full bg-gradient-to-r from-cyan-600 to-blue-600 hover:from-cyan-500 hover:to-blue-500 text-white font-semibold text-xs py-2.5 rounded-lg transition-all flex items-center justify-center gap-2 shadow-lg shadow-cyan-900/20 disabled:opacity-50"
            >
              {submitting ? (
                <>
                  <div className="w-3.5 h-3.5 border-2 border-white border-t-transparent rounded-full animate-spin" />
                  <span>Mendaftarkan ke Antrean Pipeline...</span>
                </>
              ) : (
                <>
                  <Send className="w-3.5 h-3.5" />
                  <span>Kirim Laporan via Kanal Terpilih</span>
                </>
              )}
            </button>
          </form>

          {submitError && (
            <div className="p-3 rounded-lg bg-red-500/10 border border-red-500/20 text-xs text-red-400">
              ⚠️ {submitError}
            </div>
          )}

          {submitResult && (
            <div className="p-3.5 rounded-lg bg-emerald-500/10 border border-emerald-500/20 text-xs space-y-2">
              <div className="flex items-center justify-between">
                <span className="text-emerald-400 font-semibold flex items-center gap-1.5">
                  <CheckCircle2 className="w-4 h-4" />
                  Intake Berhasil Didaftarkan!
                </span>
                <span className="px-2 py-0.5 rounded text-[10px] font-bold bg-cyan-500/20 text-cyan-300 font-mono">
                  {submitResult.ticket_number}
                </span>
              </div>
              <p className="text-slate-300 leading-relaxed">
                {submitResult.message}
              </p>
              <div className="pt-2 border-t border-emerald-500/20 flex justify-end">
                <a
                  href="#/contents"
                  className="text-cyan-400 hover:text-cyan-300 font-semibold flex items-center gap-1 text-[11px]"
                >
                  <span>Pantau di Content Explorer</span>
                  <ArrowRight className="w-3 h-3" />
                </a>
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  );
};
