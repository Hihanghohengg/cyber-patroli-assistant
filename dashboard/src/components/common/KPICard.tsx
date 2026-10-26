import React from 'react';

interface KPICardProps {
  title: string;
  value: string | number;
  subtitle?: string;
  icon: React.ReactNode;
  trend?: {
    value: string;
    isPositive?: boolean;
  };
  accentColor?: 'cyan' | 'emerald' | 'amber' | 'rose' | 'violet';
}

export const KPICard: React.FC<KPICardProps> = ({
  title,
  value,
  subtitle,
  icon,
  trend,
  accentColor = 'cyan',
}) => {
  const borderAccents = {
    cyan: 'hover:border-cyan-500/50 hover:shadow-cyan-500/10',
    emerald: 'hover:border-emerald-500/50 hover:shadow-emerald-500/10',
    amber: 'hover:border-amber-500/50 hover:shadow-amber-500/10',
    rose: 'hover:border-rose-500/50 hover:shadow-rose-500/10',
    violet: 'hover:border-violet-500/50 hover:shadow-violet-500/10',
  };

  const iconColors = {
    cyan: 'bg-cyan-950/60 text-cyan-400 border-cyan-800/40',
    emerald: 'bg-emerald-950/60 text-emerald-400 border-emerald-800/40',
    amber: 'bg-amber-950/60 text-amber-400 border-amber-800/40',
    rose: 'bg-rose-950/60 text-rose-400 border-rose-800/40',
    violet: 'bg-violet-950/60 text-violet-400 border-violet-800/40',
  };

  return (
    <div
      className={`cyber-card p-5 rounded-xl transition-all duration-300 ${borderAccents[accentColor]}`}
    >
      <div className="flex items-center justify-between">
        <span className="text-xs font-semibold uppercase tracking-wider text-slate-400">
          {title}
        </span>
        <div className={`p-2.5 rounded-lg border ${iconColors[accentColor]}`}>
          {icon}
        </div>
      </div>

      <div className="mt-4 flex items-baseline gap-2">
        <span className="text-3xl font-extrabold tracking-tight text-white font-mono">
          {value}
        </span>
        {trend && (
          <span
            className={`text-xs font-semibold px-1.5 py-0.5 rounded ${
              trend.isPositive
                ? 'text-emerald-400 bg-emerald-950/50'
                : 'text-rose-400 bg-rose-950/50'
            }`}
          >
            {trend.value}
          </span>
        )}
      </div>

      {subtitle && (
        <p className="mt-1.5 text-xs text-slate-400 font-medium">
          {subtitle}
        </p>
      )}
    </div>
  );
};
