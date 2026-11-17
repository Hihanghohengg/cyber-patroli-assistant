import React from 'react';

interface KPICardProps {
  title: string;
  value: string | number;
  subtitle?: string;
  icon?: React.ReactNode;
  trend?: {
    value: string;
    isPositive?: boolean;
  };
  accentColor?: 'blue' | 'amber' | 'rose' | 'emerald';
  onClick?: () => void;
}

export const KPICard: React.FC<KPICardProps> = ({
  title,
  value,
  subtitle,
  icon,
  trend,
  accentColor,
  onClick,
}) => {
  const accentBorder = {
    blue: 'hover:border-blue-500/40 dark:hover:border-blue-500/30',
    amber: 'hover:border-amber-500/40 dark:hover:border-amber-500/30',
    rose: 'hover:border-rose-500/40 dark:hover:border-rose-500/30',
    emerald: 'hover:border-emerald-500/40 dark:hover:border-emerald-500/30',
  }[accentColor || 'blue'];

  return (
    <div
      onClick={onClick}
      className={`cyber-card p-4 rounded-xl transition-all duration-150 border border-slate-200 dark:border-white/[0.06] ${
        onClick
          ? `cursor-pointer active:scale-[0.98] ${accentBorder}`
          : ''
      }`}
    >
      <div className="flex items-center justify-between text-slate-500 dark:text-slate-400 mb-2">
        <span className="text-[11px] font-semibold uppercase tracking-wider font-mono">
          {title}
        </span>
        {icon && <span className="opacity-75">{icon}</span>}
      </div>

      <div className="flex items-baseline justify-between gap-2">
        <span className="text-2xl font-bold tracking-tight text-slate-900 dark:text-white font-mono tabular-nums">
          {value}
        </span>
        {trend && (
          <span
            className={`text-[10px] font-mono font-bold px-1.5 py-0.5 rounded border ${
              trend.isPositive
                ? 'text-emerald-600 dark:text-emerald-400 bg-emerald-500/10 border-emerald-500/20'
                : 'text-rose-600 dark:text-rose-400 bg-rose-500/10 border-rose-500/20'
            }`}
          >
            {trend.value}
          </span>
        )}
      </div>

      {subtitle && (
        <p className="mt-1 text-[11px] text-slate-500 dark:text-slate-400 font-mono truncate">
          {subtitle}
        </p>
      )}
    </div>
  );
};

