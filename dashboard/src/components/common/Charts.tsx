import React from 'react';

// ── 1. Single Trend Line Chart (SVG) ──
interface TimelinePoint {
  snapshot_time?: string;
  date?: string;
  trending_score?: number;
  content_count?: number;
  total?: number;
}

export const TrendTimelineChart: React.FC<{
  data: TimelinePoint[];
  height?: number;
  metric?: 'trending_score' | 'content_count' | 'total';
  color?: string;
}> = ({ data, height = 180, metric = 'trending_score', color = '#3b82f6' }) => {
  if (!data || data.length === 0) {
    return (
      <div className="flex items-center justify-center h-40 text-slate-400 dark:text-slate-500 text-xs font-mono">
        Belum ada data historis snapshot
      </div>
    );
  }

  const values = data.map((d) => (d[metric] !== undefined ? Number(d[metric]) : 0));
  const maxVal = Math.max(...values, 10);
  const minVal = Math.min(...values, 0);
  const range = maxVal - minVal || 1;

  const width = 600;
  const paddingX = 30;
  const paddingY = 25;
  const plotWidth = width - paddingX * 2;
  const plotHeight = height - paddingY * 2;

  const points = values.map((val, idx) => {
    const x = paddingX + (idx / Math.max(1, values.length - 1)) * plotWidth;
    const y = height - paddingY - ((val - minVal) / range) * plotHeight;
    return `${x},${y}`;
  });

  const linePath = `M ${points.join(' L ')}`;
  const areaPath = `${linePath} L ${paddingX + plotWidth},${height - paddingY} L ${paddingX},${height - paddingY} Z`;

  return (
    <div className="w-full overflow-hidden">
      <svg viewBox={`0 0 ${width} ${height}`} className="w-full h-auto overflow-visible">
        <defs>
          <linearGradient id={`grad-${metric}`} x1="0" y1="0" x2="0" y2="1">
            <stop offset="0%" stopColor={color} stopOpacity="0.3" />
            <stop offset="100%" stopColor={color} stopOpacity="0.0" />
          </linearGradient>
        </defs>

        {/* Horizontal gridlines */}
        {[0, 0.5, 1].map((pct) => {
          const y = height - paddingY - pct * plotHeight;
          const valLabel = Math.round(minVal + pct * range);
          return (
            <g key={pct}>
              <line
                x1={paddingX}
                y1={y}
                x2={width - paddingX}
                y2={y}
                className="stroke-slate-200 dark:stroke-slate-800"
                strokeDasharray="4 4"
              />
              <text x={paddingX - 6} y={y + 3} textAnchor="end" fontSize="10" className="fill-slate-400 dark:fill-slate-500 font-mono">
                {valLabel}
              </text>
            </g>
          );
        })}

        {/* Shaded Area & Line */}
        <path d={areaPath} fill={`url(#grad-${metric})`} />
        <path d={linePath} fill="none" stroke={color} strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round" />

        {/* Data Points */}
        {values.map((val, idx) => {
          const x = paddingX + (idx / Math.max(1, values.length - 1)) * plotWidth;
          const y = height - paddingY - ((val - minVal) / range) * plotHeight;
          return (
            <g key={idx} className="group cursor-pointer">
              <circle cx={x} cy={y} r="3.5" className="fill-white dark:fill-[#090d15]" stroke={color} strokeWidth="2" />
              <title>{`Nilai: ${val}`}</title>
            </g>
          );
        })}
      </svg>
    </div>
  );
};

// ── 2. Dual Line Chart: Laporan Masuk vs Temuan Tervalidasi (Visual 1) ──
export interface DualLinePoint {
  timestamp?: string;
  date?: string;
  total_masuk?: number;
  tervalidasi?: number;
}

export const DualLineChart: React.FC<{
  data: DualLinePoint[];
  height?: number;
  onPointClick?: (point: DualLinePoint) => void;
}> = ({ data, height = 200, onPointClick }) => {
  if (!data || data.length === 0) {
    return (
      <div className="flex items-center justify-center h-44 text-slate-400 dark:text-slate-500 text-xs font-mono">
        Belum ada data deret waktu laporan
      </div>
    );
  }

  const masukVals = data.map((d) => Number(d.total_masuk ?? 0));
  const valVals = data.map((d) => Number(d.tervalidasi ?? 0));
  const maxVal = Math.max(...masukVals, ...valVals, 5);
  const minVal = 0;
  const range = maxVal - minVal || 1;

  const width = 650;
  const paddingX = 35;
  const paddingY = 25;
  const plotWidth = width - paddingX * 2;
  const plotHeight = height - paddingY * 2;

  const getPoints = (values: number[]) =>
    values.map((val, idx) => {
      const x = paddingX + (idx / Math.max(1, values.length - 1)) * plotWidth;
      const y = height - paddingY - ((val - minVal) / range) * plotHeight;
      return { x, y, val };
    });

  const ptsMasuk = getPoints(masukVals);
  const ptsVal = getPoints(valVals);

  const pathMasuk = `M ${ptsMasuk.map((p) => `${p.x},${p.y}`).join(' L ')}`;
  const pathVal = `M ${ptsVal.map((p) => `${p.x},${p.y}`).join(' L ')}`;

  return (
    <div className="w-full space-y-2">
      {/* Legend */}
      <div className="flex items-center justify-end gap-4 text-xs">
        <div className="flex items-center gap-1.5">
          <span className="w-3 h-0.5 bg-blue-500 inline-block rounded" />
          <span className="text-slate-600 dark:text-slate-300 font-medium">Laporan Masuk</span>
        </div>
        <div className="flex items-center gap-1.5">
          <span className="w-3 h-0.5 bg-emerald-500 inline-block rounded" />
          <span className="text-slate-600 dark:text-slate-300 font-medium">Temuan Tervalidasi</span>
        </div>
      </div>

      <div className="w-full overflow-hidden">
        <svg viewBox={`0 0 ${width} ${height}`} className="w-full h-auto overflow-visible">
          {/* Horizontal Grid */}
          {[0, 0.5, 1].map((pct) => {
            const y = height - paddingY - pct * plotHeight;
            const valLabel = Math.round(minVal + pct * range);
            return (
              <g key={pct}>
                <line
                  x1={paddingX}
                  y1={y}
                  x2={width - paddingX}
                  y2={y}
                  className="stroke-slate-200 dark:stroke-slate-800"
                  strokeDasharray="4 4"
                />
                <text x={paddingX - 8} y={y + 3} textAnchor="end" fontSize="10" className="fill-slate-400 dark:fill-slate-500 font-mono">
                  {valLabel}
                </text>
              </g>
            );
          })}

          {/* Lines */}
          <path d={pathMasuk} fill="none" stroke="#3b82f6" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round" />
          <path d={pathVal} fill="none" stroke="#10b981" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round" strokeDasharray="3 3" />

          {/* Dots */}
          {ptsMasuk.map((p, idx) => {
            const raw = data[idx];
            const dateStr = raw.timestamp ? raw.timestamp.slice(5, 10) : `H${idx + 1}`;
            return (
              <g
                key={`m-${idx}`}
                className="cursor-pointer group"
                onClick={() => onPointClick?.(raw)}
              >
                <circle cx={p.x} cy={p.y} r="3.5" className="fill-white dark:fill-[#090d15]" stroke="#3b82f6" strokeWidth="2" />
                <circle cx={ptsVal[idx].x} cy={ptsVal[idx].y} r="3.5" className="fill-white dark:fill-[#090d15]" stroke="#10b981" strokeWidth="2" />
                {/* X Axis Label */}
                <text x={p.x} y={height - 6} textAnchor="middle" fontSize="9" className="fill-slate-400 dark:fill-slate-500 font-mono">
                  {dateStr}
                </text>
                <title>{`${dateStr} — Masuk: ${p.val}, Tervalidasi: ${ptsVal[idx].val}`}</title>
              </g>
            );
          })}
        </svg>
      </div>
    </div>
  );
};

// ── 3. Vertical Bar Chart ──
export interface VerticalBarItem {
  label: string;
  count: number;
  color?: string;
  key?: string;
}

export const VerticalBarChart: React.FC<{
  items: VerticalBarItem[];
  height?: number;
  onBarClick?: (item: VerticalBarItem) => void;
}> = ({ items, height = 180, onBarClick }) => {
  if (!items || items.length === 0) {
    return (
      <div className="flex items-center justify-center h-36 text-slate-400 dark:text-slate-500 text-xs font-mono">
        Tidak ada data grafik
      </div>
    );
  }

  const maxVal = Math.max(...items.map((i) => i.count), 1);
  const width = 400;
  const paddingX = 35;
  const paddingY = 28;
  const plotWidth = width - paddingX * 2;
  const plotHeight = height - paddingY * 2;

  const barWidth = Math.min(44, (plotWidth / items.length) * 0.55);

  return (
    <div className="w-full overflow-hidden">
      <svg viewBox={`0 0 ${width} ${height}`} className="w-full h-auto overflow-visible">
        {/* Baseline */}
        <line
          x1={paddingX - 10}
          y1={height - paddingY}
          x2={width - paddingX + 10}
          y2={height - paddingY}
          className="stroke-slate-200 dark:stroke-slate-800"
          strokeWidth="1.5"
        />

        {items.map((item, idx) => {
          const colX = paddingX + (idx + 0.5) * (plotWidth / items.length);
          const barH = (item.count / maxVal) * plotHeight;
          const barY = height - paddingY - barH;
          const barColor = item.color || '#3b82f6';

          return (
            <g
              key={idx}
              className="cursor-pointer group"
              onClick={() => onBarClick?.(item)}
            >
              <rect
                x={colX - barWidth / 2}
                y={barY}
                width={barWidth}
                height={Math.max(barH, 3)}
                rx="4"
                fill={barColor}
                opacity="0.85"
                className="transition-all duration-200 group-hover:opacity-100"
              />
              {/* Value on top */}
              <text
                x={colX}
                y={barY - 5}
                textAnchor="middle"
                fontSize="11"
                fontWeight="bold"
                className="fill-slate-700 dark:fill-slate-200 font-mono"
              >
                {item.count}
              </text>
              {/* Label at bottom */}
              <text
                x={colX}
                y={height - paddingY + 16}
                textAnchor="middle"
                fontSize="10"
                fontWeight="500"
                className="fill-slate-500 dark:fill-slate-400"
              >
                {item.label}
              </text>
              <title>{`${item.label}: ${item.count} laporan`}</title>
            </g>
          );
        })}
      </svg>
    </div>
  );
};

// ── 4. Donut Chart ──
export interface DonutItem {
  label: string;
  count: number;
  color: string;
  key?: string;
}

export const DonutChart: React.FC<{
  items: DonutItem[];
  centerLabel?: string;
  centerValue?: string | number;
  onItemClick?: (item: DonutItem) => void;
}> = ({ items, centerLabel = 'Total', centerValue, onItemClick }) => {
  const total = items.reduce((acc, curr) => acc + curr.count, 0) || 1;
  const radius = 55;
  const strokeWidth = 16;
  const circumference = 2 * Math.PI * radius;

  let accumulatedPercent = 0;

  return (
    <div className="flex flex-col sm:flex-row items-center justify-center gap-5">
      <div className="relative w-32 h-32 flex items-center justify-center">
        <svg viewBox="0 0 150 150" className="w-full h-full -rotate-90">
          {items.map((item, idx) => {
            const percent = item.count / total;
            const strokeDasharray = `${percent * circumference} ${circumference}`;
            const strokeDashoffset = -accumulatedPercent * circumference;
            accumulatedPercent += percent;

            return (
              <circle
                key={idx}
                cx="75"
                cy="75"
                r={radius}
                fill="transparent"
                stroke={item.color}
                strokeWidth={strokeWidth}
                strokeDasharray={strokeDasharray}
                strokeDashoffset={strokeDashoffset}
                strokeLinecap="round"
                className="transition-all duration-300 hover:opacity-80 cursor-pointer"
                onClick={() => onItemClick?.(item)}
              >
                <title>{`${item.label}: ${item.count} (${Math.round(percent * 100)}%)`}</title>
              </circle>
            );
          })}
        </svg>
        <div className="absolute flex flex-col items-center justify-center text-center pointer-events-none">
          <span className="text-lg font-bold font-mono text-slate-900 dark:text-white">
            {centerValue !== undefined ? centerValue : total}
          </span>
          <span className="text-[10px] text-slate-500 uppercase tracking-wider">{centerLabel}</span>
        </div>
      </div>

      <div className="flex flex-col gap-1.5 min-w-[120px]">
        {items.map((item, idx) => {
          const pct = Math.round((item.count / total) * 100);
          return (
            <div
              key={idx}
              className="flex items-center justify-between text-xs gap-3 cursor-pointer hover:bg-slate-50 dark:hover:bg-white/[0.04] px-2 py-1 rounded transition-colors"
              onClick={() => onItemClick?.(item)}
            >
              <div className="flex items-center gap-1.5">
                <span className="w-2.5 h-2.5 rounded-full" style={{ backgroundColor: item.color }} />
                <span className="text-slate-700 dark:text-slate-300 font-medium">{item.label}</span>
              </div>
              <span className="text-slate-500 dark:text-slate-400 font-mono font-semibold">
                {item.count} <span className="text-[10px] text-slate-400">({pct}%)</span>
              </span>
            </div>
          );
        })}
      </div>
    </div>
  );
};

// ── 5. Horizontal Progress Bars ──
export const HorizontalBarList: React.FC<{
  items: Array<{ label: string; count: number; color?: string; key?: string; subtitle?: string }>;
  onBarClick?: (item: any) => void;
}> = ({ items, onBarClick }) => {
  if (!items || items.length === 0) {
    return (
      <div className="text-slate-400 dark:text-slate-500 text-xs font-mono py-4 text-center">
        Tidak ada data peringkat entitas
      </div>
    );
  }

  const max = Math.max(...items.map((i) => i.count), 1);

  return (
    <div className="space-y-2.5">
      {items.map((item, idx) => {
        const pct = Math.round((item.count / max) * 100);
        return (
          <div
            key={idx}
            className="space-y-1 group cursor-pointer hover:bg-slate-50 dark:hover:bg-white/[0.04] p-1.5 rounded-lg transition-colors"
            onClick={() => onBarClick?.(item)}
          >
            <div className="flex justify-between text-xs">
              <span className="text-slate-700 dark:text-slate-200 font-medium group-hover:text-blue-600 dark:group-hover:text-blue-300 transition-colors">
                {item.label}
                {item.subtitle && <span className="text-slate-400 text-[10px] ml-1.5">({item.subtitle})</span>}
              </span>
              <span className="font-mono text-blue-600 dark:text-blue-400 font-semibold">{item.count}</span>
            </div>
            <div className="w-full h-1.5 bg-slate-200 dark:bg-slate-800 rounded-full overflow-hidden">
              <div
                className="h-full rounded-full transition-all duration-300"
                style={{
                  width: `${pct}%`,
                  backgroundColor: item.color || '#3b82f6',
                }}
              />
            </div>
          </div>
        );
      })}
    </div>
  );
};

// ── 6. Score Gauge ──
export const ScoreGauge: React.FC<{ score: number; size?: number; label?: string }> = ({
  score,
  size = 56,
  label = 'SKOR',
}) => {
  const normScore = Math.max(0, Math.min(100, Math.round(score)));
  const radius = 38;
  const circumference = 2 * Math.PI * radius;
  const strokeOffset = circumference * (1 - normScore / 100);

  let color = '#10b981';
  if (normScore >= 70) {
    color = '#f43f5e';
  } else if (normScore >= 45) {
    color = '#f59e0b';
  }

  const isSmall = size <= 65;

  return (
    <div
      className="shrink-0 relative flex items-center justify-center rounded-full bg-slate-50 dark:bg-[#0c121d] border border-slate-200 dark:border-white/[0.08] shadow-sm"
      style={{ width: size, height: size }}
    >
      <svg viewBox="0 0 100 100" className="w-full h-full overflow-visible">
        <circle
          cx="50"
          cy="50"
          r={radius}
          className="stroke-slate-200 dark:stroke-slate-800"
          strokeWidth="6"
          fill="transparent"
        />
        <circle
          cx="50"
          cy="50"
          r={radius}
          stroke={color}
          strokeWidth="6"
          strokeDasharray={circumference}
          strokeDashoffset={strokeOffset}
          strokeLinecap="round"
          fill="transparent"
          transform="rotate(-90 50 50)"
          className="transition-all duration-500 ease-out"
        />
      </svg>

      <div className="absolute inset-0 flex flex-col items-center justify-center pointer-events-none text-center">
        <span
          className={`font-black font-mono text-slate-800 dark:text-white leading-none ${
            isSmall ? 'text-xs' : 'text-base'
          }`}
        >
          {normScore}
        </span>
        <span
          className={`font-bold font-mono tracking-wider uppercase text-slate-400 leading-none ${
            isSmall ? 'text-[8px] mt-0.5' : 'text-[9px] mt-0.5'
          }`}
        >
          {label}
        </span>
      </div>
    </div>
  );
};
