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
    <div className="min-h-screen bg-[#090A0F] flex items-center justify-center p-4 relative overflow-hidden selection:bg-blue-600/30 selection:text-blue-200">
      <div className="w-full max-w-sm relative z-10 space-y-5">
        {/* Institutional Minimalist Header */}
        <div className="text-center space-y-1.5">
          <div className="inline-flex p-2.5 rounded-xl bg-blue-500/10 border border-blue-500/20 text-blue-400 mb-1">
            <Shield className="w-6 h-6" />
          </div>
          <div className="flex items-center justify-center gap-1.5 font-mono text-[10px] text-slate-400">
            <span className="font-bold text-blue-400 uppercase">TILIK v5.0</span>
            <span>•</span>
            <span>NIST FIPS 198-1</span>
          </div>
          <h1 className="text-sm font-semibold tracking-tight text-white uppercase font-mono">
            Workstation Intelijen Siber
          </h1>
        </div>

        {/* Login Card */}
        <div className="bg-[#0F1117] border border-white/[0.08] rounded-xl p-6 space-y-4 shadow-2xl">
          <div className="border-b border-white/[0.06] pb-3">
            <h2 className="text-xs font-semibold text-slate-200 font-mono uppercase tracking-wider">
              Autentikasi Petugas
            </h2>
          </div>

          {error && (
            <div className="p-2.5 rounded-lg bg-rose-500/10 border border-rose-500/20 flex items-start gap-2 text-xs text-rose-300 font-mono">
              <AlertCircle className="w-4 h-4 text-rose-400 shrink-0 mt-0.5" />
              <span>{error}</span>
            </div>
          )}

          <form onSubmit={handleSubmit} className="space-y-3">
            <div className="space-y-1">
              <label className="text-[11px] font-mono font-medium text-slate-400 flex items-center gap-1.5">
                <User className="w-3 h-3 text-slate-500" />
                Nama Pengguna
              </label>
              <input
                type="text"
                required
                value={username}
                onChange={(e) => setUsername(e.target.value)}
                placeholder="cth: admin"
                className="w-full bg-[#0A0D14] border border-white/[0.08] rounded-lg py-1.5 px-3 text-xs text-slate-200 placeholder:text-slate-600 focus:outline-none focus:border-blue-500 font-mono transition-colors"
              />
            </div>

            <div className="space-y-1">
              <label className="text-[11px] font-mono font-medium text-slate-400 flex items-center gap-1.5">
                <Lock className="w-3 h-3 text-slate-500" />
                Kata Sandi
              </label>
              <input
                type="password"
                required
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                placeholder="••••••••••••"
                className="w-full bg-[#0A0D14] border border-white/[0.08] rounded-lg py-1.5 px-3 text-xs text-slate-200 placeholder:text-slate-600 focus:outline-none focus:border-blue-500 font-mono transition-colors"
              />
            </div>

            <button
              type="submit"
              disabled={loading}
              className="w-full py-2 px-4 rounded-lg bg-blue-600 hover:bg-blue-500 text-white font-semibold text-xs font-mono shadow-sm transition-colors flex items-center justify-center gap-1.5 disabled:opacity-50 mt-1"
            >
              {loading ? (
                <>
                  <div className="w-3 h-3 border-2 border-white border-t-transparent rounded-full animate-spin" />
                  <span>MEMVERIFIKASI...</span>
                </>
              ) : (
                <>
                  <span>MASUK</span>
                  <ArrowRight className="w-3.5 h-3.5" />
                </>
              )}
            </button>
          </form>

          {/* Quick Demo Helper */}
          <div className="pt-3 border-t border-white/[0.06]">
            <button
              type="button"
              onClick={handleFillDemo}
              className="w-full py-1.5 px-2.5 rounded-lg bg-white/[0.03] hover:bg-white/[0.06] text-slate-400 hover:text-slate-200 text-[10.5px] font-mono border border-white/[0.06] flex items-center justify-center gap-1.5 transition-colors"
            >
              <KeyRound className="w-3 h-3 text-blue-400" />
              <span>Gunakan Akun Default (admin)</span>
            </button>
          </div>
        </div>

        <div className="text-center text-[10.5px] text-slate-600 font-mono">
          TILIK Patroli Siber Terpadu &copy; 2026
        </div>
      </div>
    </div>
  );
};
