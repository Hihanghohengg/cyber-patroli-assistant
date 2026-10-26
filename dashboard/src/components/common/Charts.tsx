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
}> = ({ data, height = 180, metric = 'trending_score', color = '#00f0ff' }) => {
  if (!data || data.length === 0) {
    return (
      <div className="flex items-center justify-center h-44 text-slate-500 text-xs font-mono">
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
            <stop offset="0%" stopColor={color} stopOpacity="0.4" />
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
                stroke="#1e293b"
                strokeDasharray="4 4"
              />
              <text x={paddingX - 6} y={y + 3} textAnchor="end" fill="#64748b" fontSize="10">
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
              <circle cx={x} cy={y} r="4" fill="#070b14" stroke={color} strokeWidth="2" />
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
}> = ({ data, height = 210, onPointClick }) => {
  if (!data || data.length === 0) {
    return (
      <div className="flex items-center justify-center h-48 text-slate-500 text-xs font-mono">
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
  const paddingY = 30;
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
      <div className="flex items-center justify-end gap-5 text-xs">
        <div className="flex items-center gap-1.5">
          <span className="w-3 h-0.5 bg-cyan-400 inline-block rounded" />
          <span className="text-slate-300 font-medium">Laporan Masuk</span>
        </div>
        <div className="flex items-center gap-1.5">
          <span className="w-3 h-0.5 bg-emerald-400 inline-block rounded" />
          <span className="text-slate-300 font-medium">Temuan Tervalidasi</span>
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
                  stroke="#1e293b"
                  strokeDasharray="4 4"
                />
                <text x={paddingX - 8} y={y + 3} textAnchor="end" fill="#64748b" fontSize="10" className="font-mono">
                  {valLabel}
                </text>
              </g>
            );
          })}

          {/* Lines */}
          <path d={pathMasuk} fill="none" stroke="#06b6d4" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round" />
          <path d={pathVal} fill="none" stroke="#10b981" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round" strokeDasharray="2 2" />

          {/* Dots */}
          {ptsMasuk.map((p, idx) => {
            const raw = data[idx];
            const dateStr = raw.timestamp ? raw.timestamp.slice(5, 10) : `H${idx + 1}`;
            return (
              <g
                key={`m-${idx}`}
                className="group cursor-pointer"
                onClick={() => onPointClick?.(raw)}
              >
                <circle cx={p.x} cy={p.y} r="4" fill="#070b14" stroke="#06b6d4" strokeWidth="2" className="transition-all hover:r-6" />
                <circle cx={ptsVal[idx].x} cy={ptsVal[idx].y} r="4" fill="#070b14" stroke="#10b981" strokeWidth="2" className="transition-all hover:r-6" />
                {/* X Axis Label */}
                <text x={p.x} y={height - 8} textAnchor="middle" fill="#64748b" fontSize="9" className="font-mono">
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

// ── 3. Vertical Bar Chart (Visual 2 & Visual 8) ──
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
      <div className="flex items-center justify-center h-40 text-slate-500 text-xs font-mono">
        Tidak ada data grafik
      </div>
    );
  }

  const maxVal = Math.max(...items.map((i) => i.count), 1);
  const width = 400;
  const paddingX = 40;
  const paddingY = 30;
  const plotWidth = width - paddingX * 2;
  const plotHeight = height - paddingY * 2;

  const barWidth = Math.min(48, (plotWidth / items.length) * 0.55);

  return (
    <div className="w-full overflow-hidden">
      <svg viewBox={`0 0 ${width} ${height}`} className="w-full h-auto overflow-visible">
        {/* Baseline */}
        <line
          x1={paddingX - 10}
          y1={height - paddingY}
          x2={width - paddingX + 10}
          y2={height - paddingY}
          stroke="#1e293b"
          strokeWidth="1.5"
        />

        {items.map((item, idx) => {
          const colX = paddingX + (idx + 0.5) * (plotWidth / items.length);
          const barH = (item.count / maxVal) * plotHeight;
          const barY = height - paddingY - barH;
          const barColor = item.color || '#00f0ff';

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
                className="transition-all duration-300 group-hover:opacity-100 group-hover:brightness-125"
              />
              {/* Value on top */}
              <text
                x={colX}
                y={barY - 6}
                textAnchor="middle"
                fill="#e2e8f0"
                fontSize="11"
                fontWeight="bold"
                className="font-mono"
              >
                {item.count}
              </text>
              {/* Label at bottom */}
              <text
                x={colX}
                y={height - paddingY + 16}
                textAnchor="middle"
                fill="#94a3b8"
                fontSize="10"
                fontWeight="500"
              >
                {item.label}
              </text>
              <title>{`${item.label}: ${item.count} laporan (Klik untuk drill-down)`}</title>
            </g>
          );
        })}
      </svg>
    </div>
  );
};

// ── 4. Donut Chart (SVG) (Visual 4) ──
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
  const radius = 60;
  const strokeWidth = 18;
  const circumference = 2 * Math.PI * radius;

  let accumulatedPercent = 0;

  return (
    <div className="flex flex-col sm:flex-row items-center justify-center gap-6">
      <div className="relative w-36 h-36 flex items-center justify-center">
        <svg viewBox="0 0 160 160" className="w-full h-full -rotate-90">
          {items.map((item, idx) => {
            const percent = item.count / total;
            const strokeDasharray = `${percent * circumference} ${circumference}`;
            const strokeDashoffset = -accumulatedPercent * circumference;
            accumulatedPercent += percent;

            return (
              <circle
                key={idx}
                cx="80"
                cy="80"
                r={radius}
                fill="transparent"
                stroke={item.color}
                strokeWidth={strokeWidth}
                strokeDasharray={strokeDasharray}
                strokeDashoffset={strokeDashoffset}
                strokeLinecap="round"
                className="transition-all duration-500 hover:opacity-80 cursor-pointer"
                onClick={() => onItemClick?.(item)}
              >
                <title>{`${item.label}: ${item.count} (${Math.round(percent * 100)}%)`}</title>
              </circle>
            );
          })}
        </svg>
        <div className="absolute flex flex-col items-center justify-center text-center pointer-events-none">
          <span className="text-xl font-bold font-mono text-white">
            {centerValue !== undefined ? centerValue : total}
          </span>
          <span className="text-[10px] text-slate-400 uppercase tracking-wider">{centerLabel}</span>
        </div>
      </div>

      <div className="flex flex-col gap-2 min-w-[120px]">
        {items.map((item, idx) => {
          const pct = Math.round((item.count / total) * 100);
          return (
            <div
              key={idx}
              className="flex items-center justify-between text-xs gap-3 cursor-pointer hover:bg-slate-800/60 p-1 rounded transition-colors"
              onClick={() => onItemClick?.(item)}
            >
              <div className="flex items-center gap-2">
                <span className="w-2.5 h-2.5 rounded-full" style={{ backgroundColor: item.color }} />
                <span className="text-slate-300 font-medium">{item.label}</span>
              </div>
              <span className="text-slate-400 font-mono font-semibold">
                {item.count} <span className="text-[10px] text-slate-500">({pct}%)</span>
              </span>
            </div>
          );
        })}
      </div>
    </div>
  );
};

// ── 5. Horizontal Progress Bars (Visual 3, 5, 6, 7) ──
export const HorizontalBarList: React.FC<{
  items: Array<{ label: string; count: number; color?: string; key?: string; subtitle?: string }>;
  onBarClick?: (item: any) => void;
}> = ({ items, onBarClick }) => {
  if (!items || items.length === 0) {
    return (
      <div className="text-slate-500 text-xs font-mono py-4 text-center">
        Tidak ada data peringkat entitas
      </div>
    );
  }

  const max = Math.max(...items.map((i) => i.count), 1);

  return (
    <div className="space-y-3">
      {items.map((item, idx) => {
        const pct = Math.round((item.count / max) * 100);
        return (
          <div
            key={idx}
            className="space-y-1 group cursor-pointer hover:bg-slate-800/40 p-1.5 rounded transition-colors"
            onClick={() => onBarClick?.(item)}
          >
            <div className="flex justify-between text-xs">
              <span className="text-slate-200 font-medium group-hover:text-cyan-300 transition-colors">
                {item.label}
                {item.subtitle && <span className="text-slate-500 text-[10px] ml-1.5">({item.subtitle})</span>}
              </span>
              <span className="font-mono text-cyan-300 font-semibold">{item.count}</span>
            </div>
            <div className="w-full h-2 bg-slate-800 rounded-full overflow-hidden">
              <div
                className="h-full rounded-full transition-all duration-500"
                style={{
                  width: `${pct}%`,
                  backgroundColor: item.color || '#00f0ff',
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
export const ScoreGauge: React.FC<{ score: number; size?: number }> = ({ score, size = 90 }) => {
  const normScore = Math.max(0, Math.min(100, Math.round(score)));
  const radius = size * 0.38;
  const circumference = 2 * Math.PI * radius;
  const strokeOffset = circumference - (normScore / 100) * circumference;

  let color = '#10b981';
  if (normScore >= 70) color = '#ef4444';
  else if (normScore >= 45) color = '#f59e0b';

  return (
    <div className="relative inline-flex items-center justify-center" style={{ width: size, height: size }}>
      <svg className="w-full h-full -rotate-90">
        <circle cx={size / 2} cy={size / 2} r={radius} stroke="#1e293b" strokeWidth="7" fill="transparent" />
        <circle
          cx={size / 2}
          cy={size / 2}
          r={radius}
          stroke={color}
          strokeWidth="7"
          strokeDasharray={circumference}
          strokeDashoffset={strokeOffset}
          strokeLinecap="round"
          fill="transparent"
          className="transition-all duration-700 ease-out"
        />
      </svg>
      <div className="absolute flex flex-col items-center">
        <span className="text-base font-extrabold font-mono text-white leading-tight">
          {normScore}
        </span>
        <span className="text-[9px] font-semibold uppercase tracking-wider text-slate-400">
          Skor
        </span>
      </div>
    </div>
  );
};
