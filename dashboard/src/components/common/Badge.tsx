import React from 'react';
import { ShieldAlert, ShieldCheck, Youtube, Video, Camera, Clock, Globe } from 'lucide-react';

export const RiskBadge: React.FC<{ level?: string | null }> = ({ level }) => {
  if (!level) {
    return (
      <span className="inline-flex items-center gap-1.5 px-2 py-0.5 rounded-md text-[10px] font-semibold bg-slate-100 text-slate-600 dark:bg-slate-800 dark:text-slate-400 border border-slate-200 dark:border-slate-700">
        <span className="w-1.5 h-1.5 rounded-full bg-slate-400" />
        Belum Dinilai
      </span>
    );
  }
  const norm = level.toUpperCase();
  if (norm === 'TINGGI') {
    return (
      <span className="inline-flex items-center gap-1.5 px-2 py-0.5 rounded-md text-[10px] font-semibold bg-rose-50 text-rose-700 border-rose-200 dark:bg-rose-500/10 dark:text-rose-400 dark:border-rose-500/20 border">
        <span className="w-1.5 h-1.5 rounded-full bg-rose-500" />
        <ShieldAlert className="w-3 h-3 text-rose-600 dark:text-rose-400" />
        Tinggi
      </span>
    );
  }
  if (norm === 'SEDANG') {
    return (
      <span className="inline-flex items-center gap-1.5 px-2 py-0.5 rounded-md text-[10px] font-semibold bg-amber-50 text-amber-700 border-amber-200 dark:bg-amber-500/10 dark:text-amber-400 dark:border-amber-500/20 border">
        <span className="w-1.5 h-1.5 rounded-full bg-amber-500" />
        <Clock className="w-3 h-3 text-amber-600 dark:text-amber-400" />
        Sedang
      </span>
    );
  }
  return (
    <span className="inline-flex items-center gap-1.5 px-2 py-0.5 rounded-md text-[10px] font-semibold bg-emerald-50 text-emerald-700 border-emerald-200 dark:bg-emerald-500/10 dark:text-emerald-400 dark:border-emerald-500/20 border">
      <span className="w-1.5 h-1.5 rounded-full bg-emerald-500" />
      <ShieldCheck className="w-3 h-3 text-emerald-600 dark:text-emerald-400" />
      Rendah
    </span>
  );
};

export const SentimentBadge: React.FC<{ sentiment?: string }> = ({ sentiment = 'NETRAL' }) => {
  const norm = (sentiment || 'NETRAL').toUpperCase();
  if (norm === 'POSITIF') {
    return (
      <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded-md text-[10px] font-semibold bg-emerald-50 text-emerald-700 border-emerald-200 dark:bg-emerald-500/10 dark:text-emerald-400 dark:border-emerald-500/20 border font-mono">
        <span className="w-1.5 h-1.5 rounded-full bg-emerald-500" />
        Positif
      </span>
    );
  }
  if (norm === 'NEGATIF') {
    return (
      <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded-md text-[10px] font-semibold bg-rose-50 text-rose-700 border-rose-200 dark:bg-rose-500/10 dark:text-rose-400 dark:border-rose-500/20 border font-mono">
        <span className="w-1.5 h-1.5 rounded-full bg-rose-500" />
        Negatif
      </span>
    );
  }
  if (norm === 'CAMPURAN') {
    return (
      <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded-md text-[10px] font-semibold bg-blue-50 text-blue-700 border-blue-200 dark:bg-blue-500/10 dark:text-blue-400 dark:border-blue-500/20 border font-mono">
        <span className="w-1.5 h-1.5 rounded-full bg-blue-500" />
        Campuran
      </span>
    );
  }
  return (
    <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded-md text-[10px] font-semibold bg-slate-100 text-slate-700 border-slate-200 dark:bg-slate-800 dark:text-slate-300 dark:border-slate-700 border font-mono">
      <span className="w-1.5 h-1.5 rounded-full bg-slate-400" />
      Netral
    </span>
  );
};

export const PlatformBadge: React.FC<{ platform: string }> = ({ platform }) => {
  const norm = (platform || '').toLowerCase();
  if (norm === 'youtube') {
    return (
      <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded-md text-[10px] font-semibold bg-red-50 text-red-700 border-red-200 dark:bg-red-500/10 dark:text-red-400 dark:border-red-500/20 border">
        <Youtube className="w-3 h-3 text-red-600 dark:text-red-400" />
        YouTube
      </span>
    );
  }
  if (norm === 'tiktok') {
    return (
      <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded-md text-[10px] font-semibold bg-sky-50 text-sky-800 border-sky-200 dark:bg-sky-500/10 dark:text-sky-400 dark:border-sky-500/20 border">
        <Video className="w-3 h-3 text-sky-600 dark:text-sky-400" />
        TikTok
      </span>
    );
  }
  if (norm === 'instagram') {
    return (
      <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded-md text-[10px] font-semibold bg-pink-50 text-pink-700 border-pink-200 dark:bg-pink-500/10 dark:text-pink-400 dark:border-pink-500/20 border">
        <Camera className="w-3 h-3 text-pink-600 dark:text-pink-400" />
        Instagram
      </span>
    );
  }
  if (norm === 'x' || norm === 'twitter') {
    return (
      <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded-md text-[10px] font-semibold bg-slate-100 text-slate-800 border-slate-200 dark:bg-slate-800 dark:text-slate-200 dark:border-slate-700 border font-mono">
        <span className="font-bold text-xs leading-none">𝕏</span>
        X (Twitter)
      </span>
    );
  }
  if (norm === 'threads') {
    return (
      <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded-md text-[10px] font-semibold bg-purple-50 text-purple-700 border-purple-200 dark:bg-purple-500/10 dark:text-purple-300 dark:border-purple-500/20 border font-mono">
        <span className="font-bold text-xs leading-none">@</span>
        Threads
      </span>
    );
  }
  if (norm === 'facebook') {
    return (
      <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded-md text-[10px] font-semibold bg-blue-50 text-blue-700 border-blue-200 dark:bg-blue-500/10 dark:text-blue-300 dark:border-blue-500/20 border">
        <span className="font-bold text-xs leading-none font-mono">f</span>
        Facebook
      </span>
    );
  }
  return (
    <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded-md text-[10px] font-semibold bg-slate-100 text-slate-700 border-slate-200 dark:bg-slate-800 dark:text-slate-300 dark:border-slate-700 border">
      <Globe className="w-3 h-3 text-slate-500" />
      {platform.toUpperCase()}
    </span>
  );
};

export const StatusBadge: React.FC<{ status: string }> = ({ status }) => {
  const norm = (status || '').toUpperCase();
  if (norm === 'VALIDATED') {
    return (
      <span className="inline-flex items-center px-2 py-0.5 rounded-md text-[10px] font-semibold bg-emerald-50 text-emerald-700 border-emerald-200 dark:bg-emerald-500/10 dark:text-emerald-400 dark:border-emerald-500/20 border font-mono">
        TERVALIDASI
      </span>
    );
  }
  if (norm === 'MODIFIED') {
    return (
      <span className="inline-flex items-center px-2 py-0.5 rounded-md text-[10px] font-semibold bg-amber-50 text-amber-700 border-amber-200 dark:bg-amber-500/10 dark:text-amber-400 dark:border-amber-500/20 border font-mono">
        KOREKSI ANALIS
      </span>
    );
  }
  if (norm === 'REJECTED') {
    return (
      <span className="inline-flex items-center px-2 py-0.5 rounded-md text-[10px] font-semibold bg-rose-50 text-rose-700 border-rose-200 dark:bg-rose-500/10 dark:text-rose-400 dark:border-rose-500/20 border font-mono">
        BUKAN PELANGGARAN
      </span>
    );
  }
  return (
    <span className="inline-flex items-center px-2 py-0.5 rounded-md text-[10px] font-semibold bg-blue-50 text-blue-700 border-blue-200 dark:bg-blue-500/10 dark:text-blue-400 dark:border-blue-500/20 border font-mono">
      MENUNGGU VALIDASI
    </span>
  );
};
