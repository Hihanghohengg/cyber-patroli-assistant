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
  accentColor?: 'cyan' | 'emerald' | 'amber' | 'rose' | 'violet' | 'blue';
  onClick?: () => void;
}

export const KPICard: React.FC<KPICardProps> = ({
  title,
  value,
  subtitle,
  icon,
  trend,
  onClick,
}) => {
  return (
    <div
      onClick={onClick}
      className={`cyber-card p-4 rounded-xl transition-all duration-150 ${
        onClick ? 'cursor-pointer hover:border-slate-400 dark:hover:border-white/[0.15]' : ''
      }`}
    >
      <div className="flex items-center justify-between text-slate-400 dark:text-slate-500 mb-2">
        <span className="text-[11px] font-semibold uppercase tracking-wider font-mono">
          {title}
        </span>
        {icon && <span className="opacity-60">{icon}</span>}
      </div>

      <div className="flex items-baseline justify-between gap-2">
        <span className="text-2xl font-semibold tracking-tight text-slate-900 dark:text-white font-mono tabular-nums">
          {value}
        </span>
        {trend && (
          <span
            className={`text-[11px] font-mono font-semibold px-1.5 py-0.5 rounded border ${
              trend.isPositive
                ? 'text-emerald-500 bg-emerald-500/10 border-emerald-500/20'
                : 'text-rose-500 bg-rose-500/10 border-rose-500/20'
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
