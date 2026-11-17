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
  accentColor?: 'cyan' | 'emerald' | 'amber' | 'rose' | 'violet' | 'blue';
}

export const KPICard: React.FC<KPICardProps> = ({
  title,
  value,
  subtitle,
  icon,
  trend,
  accentColor = 'blue',
}) => {
  const iconTones = {
    blue: 'bg-blue-50 text-blue-600 border-blue-200/80 dark:bg-blue-500/10 dark:text-blue-400 dark:border-blue-500/20',
    cyan: 'bg-sky-50 text-sky-600 border-sky-200/80 dark:bg-sky-500/10 dark:text-sky-400 dark:border-sky-500/20',
    emerald: 'bg-emerald-50 text-emerald-600 border-emerald-200/80 dark:bg-emerald-500/10 dark:text-emerald-400 dark:border-emerald-500/20',
    amber: 'bg-amber-50 text-amber-600 border-amber-200/80 dark:bg-amber-500/10 dark:text-amber-400 dark:border-amber-500/20',
    rose: 'bg-rose-50 text-rose-600 border-rose-200/80 dark:bg-rose-500/10 dark:text-rose-400 dark:border-rose-500/20',
    violet: 'bg-violet-50 text-violet-600 border-violet-200/80 dark:bg-violet-500/10 dark:text-violet-400 dark:border-violet-500/20',
  };

  const activeTone = (accentColor === 'cyan' ? 'blue' : accentColor) as keyof typeof iconTones;

  return (
    <div className="cyber-card p-4 sm:p-5 rounded-xl transition-all duration-200">
      <div className="flex items-center justify-between">
        <span className="text-[11px] font-semibold uppercase tracking-wider text-slate-500 dark:text-slate-400 font-mono">
          {title}
        </span>
        <div className={`p-2 rounded-lg border ${iconTones[activeTone]}`}>
          {icon}
        </div>
      </div>

      <div className="mt-3 flex items-baseline gap-2">
        <span className="text-2xl sm:text-3xl font-bold tracking-tight text-slate-900 dark:text-white font-mono tabular-nums">
          {value}
        </span>
        {trend && (
          <span
            className={`text-xs font-semibold px-2 py-0.5 rounded border ${
              trend.isPositive
                ? 'text-emerald-700 bg-emerald-50 border-emerald-200 dark:text-emerald-400 dark:bg-emerald-500/10 dark:border-emerald-500/20'
                : 'text-rose-700 bg-rose-50 border-rose-200 dark:text-rose-400 dark:bg-rose-500/10 dark:border-rose-500/20'
            }`}
          >
            {trend.value}
          </span>
        )}
      </div>

      {subtitle && (
        <p className="mt-1 text-xs text-slate-500 dark:text-slate-400 font-medium">
          {subtitle}
        </p>
      )}
    </div>
  );
};
