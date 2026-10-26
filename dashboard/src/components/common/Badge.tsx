import React from 'react';
import { ShieldAlert, ShieldCheck, Youtube, Video, Camera, Clock, CheckCircle2, XCircle } from 'lucide-react';

export const RiskBadge: React.FC<{ level?: string }> = ({ level = 'RENDAH' }) => {
  const norm = level.toUpperCase();
  if (norm === 'TINGGI') {
    return (
      <span className="inline-flex items-center gap-1.5 px-2.5 py-0.5 rounded-full text-xs font-semibold bg-rose-500/15 text-rose-400 border border-rose-500/30">
        <ShieldAlert className="w-3.5 h-3.5" />
        Risiko Tinggi
      </span>
    );
  }
  if (norm === 'SEDANG') {
    return (
      <span className="inline-flex items-center gap-1.5 px-2.5 py-0.5 rounded-full text-xs font-semibold bg-amber-500/15 text-amber-400 border border-amber-500/30">
        <Clock className="w-3.5 h-3.5" />
        Risiko Sedang
      </span>
    );
  }
  return (
    <span className="inline-flex items-center gap-1.5 px-2.5 py-0.5 rounded-full text-xs font-semibold bg-emerald-500/15 text-emerald-400 border border-emerald-500/30">
      <ShieldCheck className="w-3.5 h-3.5" />
      Risiko Rendah
    </span>
  );
};

export const SentimentBadge: React.FC<{ sentiment?: string }> = ({ sentiment = 'NETRAL' }) => {
  const norm = (sentiment || 'NETRAL').toUpperCase();
  if (norm === 'POSITIF') {
    return (
      <span className="px-2 py-0.5 rounded text-xs font-medium bg-emerald-950/80 text-emerald-300 border border-emerald-500/30">
        Positif
      </span>
    );
  }
  if (norm === 'NEGATIF') {
    return (
      <span className="px-2 py-0.5 rounded text-xs font-medium bg-rose-950/80 text-rose-300 border border-rose-500/30">
        Negatif
      </span>
    );
  }
  if (norm === 'CAMPURAN') {
    return (
      <span className="px-2 py-0.5 rounded text-xs font-medium bg-purple-950/80 text-purple-300 border border-purple-500/30">
        Campuran
      </span>
    );
  }
  return (
    <span className="px-2 py-0.5 rounded text-xs font-medium bg-sky-950/80 text-sky-300 border border-sky-500/30">
      Netral
    </span>
  );
};

export const PlatformBadge: React.FC<{ platform: string }> = ({ platform }) => {
  const norm = (platform || '').toLowerCase();
  if (norm === 'youtube') {
    return (
      <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded text-xs font-medium bg-red-950/60 text-red-400 border border-red-500/30">
        <Youtube className="w-3.5 h-3.5 text-red-500" />
        YouTube
      </span>
    );
  }
  if (norm === 'tiktok') {
    return (
      <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded text-xs font-medium bg-cyan-950/60 text-cyan-300 border border-cyan-500/30">
        <Video className="w-3.5 h-3.5 text-cyan-400" />
        TikTok
      </span>
    );
  }
  if (norm === 'instagram') {
    return (
      <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded text-xs font-medium bg-pink-950/60 text-pink-300 border border-pink-500/30">
        <Camera className="w-3.5 h-3.5 text-pink-400" />
        Instagram
      </span>
    );
  }
  return (
    <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded text-xs font-medium bg-slate-800 text-slate-300 border border-slate-700">
      {platform}
    </span>
  );
};

export const StatusBadge: React.FC<{ status: string }> = ({ status }) => {
  const norm = (status || '').toUpperCase();
  if (norm === 'VALIDATED') {
    return (
      <span className="inline-flex items-center gap-1 px-2.5 py-0.5 rounded-full text-xs font-medium bg-emerald-500/20 text-emerald-400 border border-emerald-500/40">
        <CheckCircle2 className="w-3.5 h-3.5" />
        Tervalidasi
      </span>
    );
  }
  if (norm === 'REJECTED') {
    return (
      <span className="inline-flex items-center gap-1 px-2.5 py-0.5 rounded-full text-xs font-medium bg-rose-500/20 text-rose-400 border border-rose-500/40">
        <XCircle className="w-3.5 h-3.5" />
        Ditolak (Hoax/Safe)
      </span>
    );
  }
  return (
    <span className="inline-flex items-center gap-1 px-2.5 py-0.5 rounded-full text-xs font-medium bg-amber-500/20 text-amber-300 border border-amber-500/40">
      <Clock className="w-3.5 h-3.5" />
      Menunggu Validasi
    </span>
  );
};
