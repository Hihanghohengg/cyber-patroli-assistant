import React, { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { useAuth } from '../context/AuthContext';
import { Shield, Lock, User, AlertCircle, ArrowRight, KeyRound } from 'lucide-react';

export const LoginPage: React.FC = () => {
  const [username, setUsername] = useState<string>('admin');
  const [password, setPassword] = useState<string>('patroladmin2026');
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState<boolean>(false);

  const { login } = useAuth();
  const navigate = useNavigate();

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError(null);
    setLoading(true);

    try {
      await login(username, password);
      navigate('/');
    } catch (err: any) {
      setError(
        err.response?.data?.detail ||
          'Autentikasi gagal. Pastikan nama pengguna dan kata sandi benar.'
      );
    } finally {
      setLoading(false);
    }
  };

  const handleFillDemo = () => {
    setUsername('admin');
    setPassword('patroladmin2026');
  };

  return (
    <div className="min-h-screen bg-[#090d16] flex items-center justify-center p-4 relative overflow-hidden selection:bg-blue-600/30 selection:text-blue-200">
      <div className="w-full max-w-md relative z-10 space-y-6">
        {/* Institutional Terminal Header */}
        <div className="text-center space-y-2">
          <div className="inline-flex p-3 rounded-xl bg-blue-600/15 border border-blue-500/30 mb-2 shadow-sm">
            <Shield className="w-7 h-7 text-blue-400" />
          </div>
          <div className="flex items-center justify-center gap-2">
            <span className="font-mono text-[10px] font-bold tracking-widest uppercase px-2 py-0.5 rounded bg-blue-950/80 text-blue-400 border border-blue-800/40">
              TILIK v5.0
            </span>
            <span className="font-mono text-[10px] text-slate-400 tracking-wider">
              NIST FIPS 198-1
            </span>
          </div>
          <h1 className="text-lg font-bold tracking-tight text-white uppercase font-sans">
            Sistem Asisten Patroli Siber Terpadu
          </h1>
          <p className="text-[11px] text-slate-400 font-mono">
            Stasiun Kerja Intelijen Siber & Rantai Bukti Digital
          </p>
        </div>

        {/* Login Card */}
        <div className="cyber-card rounded-2xl p-6 sm:p-8 space-y-6">
          <div className="border-b border-slate-800 pb-4">
            <h2 className="text-sm font-bold text-white">Autentikasi Petugas Analis</h2>
            <p className="text-xs text-slate-400 mt-0.5">
              Silakan masukkan kredensial resmi untuk mengakses workstation intelijen siber.
            </p>
          </div>

          {error && (
            <div className="p-3 rounded-lg bg-rose-500/10 border border-rose-500/30 flex items-start gap-2.5 text-xs text-rose-300">
              <AlertCircle className="w-4 h-4 text-rose-400 shrink-0 mt-0.5" />
              <span>{error}</span>
            </div>
          )}

          <form onSubmit={handleSubmit} className="space-y-4">
            <div className="space-y-1.5">
              <label className="text-xs font-semibold text-slate-300 flex items-center gap-1.5">
                <User className="w-3.5 h-3.5 text-slate-400" />
                Nama Pengguna (Username)
              </label>
              <input
                type="text"
                required
                value={username}
                onChange={(e) => setUsername(e.target.value)}
                placeholder="cth: admin"
                className="w-full bg-[#0b0f17] border border-slate-800 rounded-lg py-2.5 px-3 text-xs text-slate-200 placeholder:text-slate-600 focus:outline-none focus:border-blue-500 focus:ring-1 focus:ring-blue-500/30 font-mono transition-colors"
              />
            </div>

            <div className="space-y-1.5">
              <label className="text-xs font-semibold text-slate-300 flex items-center gap-1.5">
                <Lock className="w-3.5 h-3.5 text-slate-400" />
                Kata Sandi (Password)
              </label>
              <input
                type="password"
                required
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                placeholder="••••••••••••"
                className="w-full bg-[#0b0f17] border border-slate-800 rounded-lg py-2.5 px-3 text-xs text-slate-200 placeholder:text-slate-600 focus:outline-none focus:border-blue-500 focus:ring-1 focus:ring-blue-500/30 font-mono transition-colors"
              />
            </div>

            <button
              type="submit"
              disabled={loading}
              className="w-full py-2.5 px-4 rounded-lg bg-blue-600 hover:bg-blue-500 text-white font-semibold text-xs tracking-wide shadow-sm shadow-blue-500/10 transition-all flex items-center justify-center gap-2 disabled:opacity-50 mt-2"
            >
              {loading ? (
                <>
                  <div className="w-3.5 h-3.5 border-2 border-white border-t-transparent rounded-full animate-spin" />
                  <span>MEMVERIFIKASI...</span>
                </>
              ) : (
                <>
                  <span>MASUK KE WORKSTATION</span>
                  <ArrowRight className="w-3.5 h-3.5" />
                </>
              )}
            </button>
          </form>

          {/* Quick Demo Helper */}
          <div className="pt-4 border-t border-slate-800/80">
            <button
              type="button"
              onClick={handleFillDemo}
              className="w-full py-2 px-3 rounded-lg bg-slate-900/80 hover:bg-slate-800 text-slate-300 text-[11px] font-mono border border-slate-800 hover:border-slate-700 flex items-center justify-center gap-1.5 transition-colors"
            >
              <KeyRound className="w-3.5 h-3.5 text-blue-400" />
              <span>Gunakan Akun Default (admin / patroladmin2026)</span>
            </button>
          </div>
        </div>

        <div className="text-center text-[11px] text-slate-600 font-mono">
          Sistem Patroli Siber Resmi &copy; 2026
        </div>
      </div>
    </div>
  );
};
