import React, { useState, useEffect } from 'react';
import {
  Chrome,
  LayoutDashboard,
  CheckCircle2,
  ExternalLink,
  ShieldCheck,
  Zap,
  Copy,
  Check,
  AlertCircle,
  FileSpreadsheet,
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
  const [operatorId, setOperatorId] = useState('Analyst-Browser');
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
        reporter_identifier: operatorId.trim() || 'Analyst-Browser',
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

  const extensionIntakeCount = channels.find((c) => c.id === 'browser_extension')?.intake_count || 0;
  const webConsoleIntakeCount = channels.find((c) => c.id === 'web_dashboard')?.intake_count || 0;

  return (
    <div className="space-y-5">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3">
        <div>
          <h1 className="text-base font-bold text-slate-900 dark:text-white flex items-center gap-2">
            <Chrome className="w-5 h-5 text-blue-600 dark:text-blue-400" />
            Ekstensi Browser & Intake Patroli
          </h1>
        </div>
      </div>

      {/* Grid Status Arsitektur */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
        {/* Chrome Extension - PRIMARY */}
        <div className="cyber-card p-4 rounded-xl border border-blue-400/40 dark:border-blue-500/40">
          <div className="flex items-center justify-between mb-2">
            <div className="p-2 rounded-lg bg-blue-50 dark:bg-blue-600/20 text-blue-600 dark:text-blue-300 border border-blue-200 dark:border-blue-400/40">
              <Chrome className="w-4 h-4" />
            </div>
            <span className="px-2 py-0.5 rounded text-[10px] font-bold bg-blue-600 text-white flex items-center gap-1 shadow-sm">
              KANAL UTAMA
            </span>
          </div>
          <h3 className="font-bold text-slate-900 dark:text-white text-xs">
            Browser Extension MV3
          </h3>
          <p className="text-[11px] text-slate-500 dark:text-slate-400 mt-1 leading-relaxed">
            Asisten utama bagi analis saat berselancar di media sosial dengan 1-click triage & in-page floating button.
          </p>
          <div className="mt-3 pt-2.5 border-t border-slate-100 dark:border-slate-800 text-[11px] text-slate-500 dark:text-slate-400 space-y-1">
            <div className="flex justify-between">
              <span>Total Laporan:</span>
              <span className="text-blue-600 dark:text-blue-300 font-semibold font-mono">{extensionIntakeCount}</span>
            </div>
          </div>
        </div>

        {/* Web Command Console */}
        <div className="cyber-card p-4 rounded-xl">
          <div className="flex items-center justify-between mb-2">
            <div className="p-2 rounded-lg bg-purple-50 dark:bg-purple-500/10 text-purple-600 dark:text-purple-400 border border-purple-200 dark:border-purple-500/20">
              <LayoutDashboard className="w-4 h-4" />
            </div>
            <span className="px-2 py-0.5 rounded text-[10px] font-bold bg-purple-50 text-purple-700 dark:bg-purple-500/10 dark:text-purple-400 border border-purple-200 dark:border-purple-500/20">
              PUSAT KENDALI
            </span>
          </div>
          <h3 className="font-semibold text-slate-900 dark:text-white text-xs">Web Dashboard Console</h3>
          <p className="text-[11px] text-slate-500 dark:text-slate-400 mt-1 leading-relaxed">
            Pusat monitoring, eksplorasi bukti visual, validasi HITL oleh analis, dan kurasi preseden AI.
          </p>
          <div className="mt-3 pt-2.5 border-t border-slate-100 dark:border-slate-800 text-[11px] text-slate-500 dark:text-slate-400 space-y-1">
            <div className="flex justify-between">
              <span>Input Langsung:</span>
              <span className="text-purple-600 dark:text-purple-300 font-mono font-semibold">{webConsoleIntakeCount}</span>
            </div>
          </div>
        </div>

        {/* Client-First Forensic Integrity */}
        <div className="cyber-card p-4 rounded-xl">
          <div className="flex items-center justify-between mb-2">
            <div className="p-2 rounded-lg bg-emerald-50 dark:bg-emerald-500/10 text-emerald-600 dark:text-emerald-400 border border-emerald-200 dark:border-emerald-500/20">
              <ShieldCheck className="w-4 h-4" />
            </div>
            <span className="px-2 py-0.5 rounded text-[10px] font-bold bg-emerald-50 text-emerald-700 dark:bg-emerald-500/10 dark:text-emerald-400 border border-emerald-200 dark:border-emerald-500/20">
              SHA-256
            </span>
          </div>
          <h3 className="font-semibold text-slate-900 dark:text-white text-xs">Integritas Bukti Digital</h3>
          <p className="text-[11px] text-slate-500 dark:text-slate-400 mt-1 leading-relaxed">
            Tangkapan layar dan DOM dihitung hash SHA-256 langsung di browser klien via WebCrypto API sebelum dikirim.
          </p>
          <div className="mt-3 pt-2.5 border-t border-slate-100 dark:border-slate-800 text-[11px] text-slate-500 dark:text-slate-400 space-y-1">
            <div className="flex justify-between">
              <span>Standar Hash:</span>
              <span className="text-emerald-600 dark:text-emerald-300 font-mono">FIPS 180-4</span>
            </div>
          </div>
        </div>
      </div>

      {/* Detail Bagian Bawah: Panduan Ekstensi & Form Simulasi Intake */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-5">
        {/* Panduan Pemasangan Ekstensi Browser */}
        <div className="cyber-card p-4 sm:p-5 rounded-xl space-y-3">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-2 text-blue-600 dark:text-blue-400">
              <Chrome className="w-4 h-4" />
              <h2 className="text-sm font-semibold text-slate-800 dark:text-white">Panduan Pasang Ekstensi</h2>
            </div>
            <span className="px-2 py-0.5 rounded text-[10px] font-semibold bg-blue-50 dark:bg-blue-500/10 text-blue-600 dark:text-blue-400 border border-blue-200 dark:border-blue-500/20">
              Chrome & Edge
            </span>
          </div>

          <ol className="text-xs text-slate-600 dark:text-slate-300 space-y-2 list-decimal list-inside bg-slate-50 dark:bg-slate-950 p-3.5 rounded-lg border border-slate-200 dark:border-slate-800">
            <li>
              Buka menu ekstensi browser: <code className="text-blue-600 dark:text-blue-400 bg-slate-200 dark:bg-slate-900 px-1 py-0.5 rounded font-mono">chrome://extensions</code>
            </li>
            <li>
              Nyalakan toggle <strong>Developer mode</strong> di kanan atas.
            </li>
            <li>
              Klik tombol <strong>Load unpacked (Muat yang belum dibongkar)</strong>.
            </li>
            <li>
              Pilih folder ekstensi:
            </li>
          </ol>

          <div className="flex items-center gap-2 bg-slate-50 dark:bg-slate-950 p-2 rounded-lg border border-slate-200 dark:border-slate-800 font-mono text-xs text-slate-600 dark:text-slate-300">
            <span className="truncate flex-1 text-blue-600 dark:text-blue-400">{extensionPath}</span>
            <button
              onClick={handleCopyPath}
              className="px-2.5 py-1 rounded bg-slate-200 hover:bg-slate-300 dark:bg-slate-800 dark:hover:bg-slate-700 text-slate-700 dark:text-slate-200 text-xs flex items-center gap-1 transition-colors shrink-0"
            >
              {copiedPath ? <Check className="w-3.5 h-3.5 text-emerald-500" /> : <Copy className="w-3.5 h-3.5" />}
              <span>{copiedPath ? 'Tersalin' : 'Salin Path'}</span>
            </button>
          </div>
        </div>

        {/* Form Simulasi Input Intake */}
        <div className="cyber-card p-4 sm:p-5 rounded-xl space-y-3">
          <div className="flex items-center gap-2 text-purple-600 dark:text-purple-400">
            <Zap className="w-4 h-4" />
            <h2 className="text-sm font-semibold text-slate-800 dark:text-white">Uji Intake Manual</h2>
          </div>

          <form onSubmit={handleSubmitIntake} className="space-y-3">
            <div>
              <label className="block text-[11px] text-slate-500 mb-1">URL Postingan Target</label>
              <input
                type="url"
                required
                value={testUrl}
                onChange={(e) => setTestUrl(e.target.value)}
                placeholder="https://www.tiktok.com/@... atau https://youtu.be/..."
                className="w-full bg-white dark:bg-slate-950 border border-slate-300 dark:border-slate-700 rounded-lg px-3 py-1.5 text-xs text-slate-800 dark:text-white placeholder:text-slate-400 focus:outline-none focus:border-blue-500 font-mono"
              />
            </div>

            <div>
              <label className="block text-[11px] text-slate-500 mb-1">Catatan Analis</label>
              <input
                type="text"
                value={notes}
                onChange={(e) => setNotes(e.target.value)}
                placeholder="Keterangan singkat..."
                className="w-full bg-white dark:bg-slate-950 border border-slate-300 dark:border-slate-700 rounded-lg px-3 py-1.5 text-xs text-slate-800 dark:text-white placeholder:text-slate-400 focus:outline-none focus:border-blue-500"
              />
            </div>

            <button
              type="submit"
              disabled={submitting}
              className="w-full py-2 bg-blue-600 hover:bg-blue-500 text-white font-semibold text-xs rounded-lg transition-colors flex items-center justify-center gap-1.5 disabled:opacity-50"
            >
              <Zap className={`w-3.5 h-3.5 ${submitting ? 'animate-spin' : ''}`} />
              <span>{submitting ? 'Memproses...' : 'Kirim Triase'}</span>
            </button>
          </form>

          {submitResult && (
            <div className="p-2.5 rounded-lg bg-emerald-50 dark:bg-emerald-950/40 border border-emerald-200 dark:border-emerald-500/30 text-xs text-emerald-800 dark:text-emerald-300 flex items-center gap-2">
              <CheckCircle2 className="w-4 h-4 text-emerald-600 dark:text-emerald-400 shrink-0" />
              <span>Tiket {submitResult.ticket_number} berhasil dibuat.</span>
            </div>
          )}

          {submitError && (
            <div className="p-2.5 rounded-lg bg-rose-50 dark:bg-rose-950/40 border border-rose-200 dark:border-rose-500/30 text-xs text-rose-800 dark:text-rose-300 flex items-center gap-2">
              <AlertCircle className="w-4 h-4 text-rose-600 dark:text-rose-400 shrink-0" />
              <span>{submitError}</span>
            </div>
          )}
        </div>
      </div>
    </div>
  );
};
