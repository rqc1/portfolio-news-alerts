"use client";

import {
  ResponsiveContainer,
  BarChart,
  Bar,
  XAxis,
  YAxis,
  Tooltip,
  PieChart,
  Pie,
  Cell,
  ScatterChart,
  Scatter,
  CartesianGrid,
  AreaChart,
  Area,
  LineChart,
  Line,
} from "recharts";
import type { PieLabelRenderProps } from "recharts";

/* ── Shared theme ─────────────────────────────────────────────────────── */

const AXIS_STYLE = {
  fontSize: 11,
  fontFamily: "var(--font-sans)",
  fill: "var(--text-muted)",
};

const GRID_STROKE = "rgba(148,163,184,0.06)";

const DIRECTION_COLORS: Record<string, string> = {
  bajista: "#ef4444",
  alcista: "#10b981",
  neutral: "#f59e0b",
};

const CHART_COLORS = [
  "#6366f1",
  "#a78bfa",
  "#06b6d4",
  "#10b981",
  "#f59e0b",
  "#ef4444",
  "#ec4899",
  "#8b5cf6",
];

/* ── Custom tooltip ───────────────────────────────────────────────────── */

function ChartTooltip({
  active,
  payload,
  label,
}: {
  active?: boolean;
  payload?: Array<{ name: string; value: number; color?: string }>;
  label?: string;
}) {
  if (!active || !payload?.length) return null;
  return (
    <div className="rounded-[var(--radius-md)] border border-[var(--border-default)] bg-[var(--bg-elevated)] px-3 py-2 shadow-xl">
      {label && (
        <p className="mb-1 text-[11px] font-semibold text-[var(--text-secondary)]">
          {label}
        </p>
      )}
      {payload.map((entry, i) => (
        <p key={i} className="text-[11px] text-[var(--text-primary)]">
          <span
            className="mr-1.5 inline-block h-2 w-2 rounded-full"
            style={{ backgroundColor: entry.color ?? CHART_COLORS[0] }}
          />
          {entry.name}: <span className="font-bold">{entry.value}</span>
        </p>
      ))}
    </div>
  );
}

/* ── Event Distribution Bar ───────────────────────────────────────────── */

export function EventDistributionChart({
  data,
}: {
  data: Array<{ name: string; count: number }>;
}) {
  return (
    <ResponsiveContainer width="100%" height={300}>
      <BarChart data={data} layout="vertical" margin={{ left: 8, right: 16, top: 4, bottom: 4 }}>
        <CartesianGrid horizontal={false} stroke={GRID_STROKE} />
        <XAxis type="number" tick={AXIS_STYLE} axisLine={false} tickLine={false} />
        <YAxis
          type="category"
          dataKey="name"
          width={140}
          tick={AXIS_STYLE}
          axisLine={false}
          tickLine={false}
        />
        <Tooltip content={<ChartTooltip />} cursor={{ fill: "rgba(99,102,241,0.04)" }} />
        <Bar dataKey="count" name="Cantidad" fill="#6366f1" radius={[0, 4, 4, 0]} barSize={18} />
      </BarChart>
    </ResponsiveContainer>
  );
}

/* ── Direction Pie ────────────────────────────────────────────────────── */

export function DirectionPieChart({
  data,
}: {
  data: Array<{ name: string; value: number }>;
}) {
  return (
    <ResponsiveContainer width="100%" height={300}>
      <PieChart>
        <Pie
          data={data}
          cx="50%"
          cy="50%"
          innerRadius={65}
          outerRadius={100}
          paddingAngle={3}
          dataKey="value"
          nameKey="name"
          stroke="var(--bg-root)"
          strokeWidth={3}
        >
          {data.map((entry) => (
            <Cell
              key={entry.name}
              fill={DIRECTION_COLORS[entry.name] ?? CHART_COLORS[0]}
            />
          ))}
        </Pie>
        <Tooltip content={<ChartTooltip />} />
      </PieChart>
    </ResponsiveContainer>
  );
}

/* ── Severity vs Confidence Scatter ───────────────────────────────────── */

export function SeverityConfidenceScatter({
  data,
}: {
  data: Array<{
    severity: number;
    confidence: number;
    direction: string;
    title?: string;
  }>;
}) {
  const grouped = Object.entries(DIRECTION_COLORS).map(([dir, color]) => ({
    direction: dir,
    color,
    points: data.filter((d) => d.direction === dir),
  }));

  return (
    <ResponsiveContainer width="100%" height={300}>
      <ScatterChart margin={{ top: 8, right: 16, bottom: 4, left: 8 }}>
        <CartesianGrid stroke={GRID_STROKE} />
        <XAxis
          type="number"
          dataKey="severity"
          name="Severidad"
          domain={[0, 1]}
          tick={AXIS_STYLE}
          axisLine={false}
          tickLine={false}
        />
        <YAxis
          type="number"
          dataKey="confidence"
          name="Confianza"
          domain={[0, 1]}
          tick={AXIS_STYLE}
          axisLine={false}
          tickLine={false}
        />
        <Tooltip content={<ChartTooltip />} cursor={{ strokeDasharray: "3 3" }} />
        {grouped.map(({ direction, color, points }) =>
          points.length > 0 ? (
            <Scatter key={direction} name={direction} data={points} fill={color}>
              {points.map((_, i) => (
                <Cell key={i} fill={color} />
              ))}
            </Scatter>
          ) : null,
        )}
      </ScatterChart>
    </ResponsiveContainer>
  );
}

/* ── Severity Histogram ───────────────────────────────────────────────── */

export function SeverityHistogram({
  data,
}: {
  data: Array<{ range: string; count: number }>;
}) {
  return (
    <ResponsiveContainer width="100%" height={300}>
      <BarChart data={data} margin={{ left: 0, right: 8, top: 4, bottom: 4 }}>
        <CartesianGrid vertical={false} stroke={GRID_STROKE} />
        <XAxis dataKey="range" tick={AXIS_STYLE} axisLine={false} tickLine={false} />
        <YAxis tick={AXIS_STYLE} axisLine={false} tickLine={false} />
        <Tooltip content={<ChartTooltip />} cursor={{ fill: "rgba(167,139,250,0.06)" }} />
        <Bar dataKey="count" name="Frecuencia" fill="#a78bfa" radius={[4, 4, 0, 0]} barSize={20} />
      </BarChart>
    </ResponsiveContainer>
  );
}

/* ── Portfolio Weight Pie ─────────────────────────────────────────────── */

export function WeightPieChart({
  data,
}: {
  data: Array<{ name: string; value: number }>;
}) {
  return (
    <ResponsiveContainer width="100%" height={280}>
      <PieChart>
        <Pie
          data={data}
          cx="50%"
          cy="50%"
          innerRadius={55}
          outerRadius={90}
          paddingAngle={2}
          dataKey="value"
          nameKey="name"
          stroke="var(--bg-root)"
          strokeWidth={2}
          label={(props: PieLabelRenderProps) =>
            `${props.name ?? ""} ${(((props.percent as number) ?? 0) * 100).toFixed(0)}%`
          }
        >
          {data.map((_, i) => (
            <Cell key={i} fill={CHART_COLORS[i % CHART_COLORS.length]} />
          ))}
        </Pie>
        <Tooltip content={<ChartTooltip />} />
      </PieChart>
    </ResponsiveContainer>
  );
}

/* ── Sector Bar ───────────────────────────────────────────────────────── */

export function SectorBarChart({
  data,
}: {
  data: Array<{ sector: string; weight: number }>;
}) {
  return (
    <ResponsiveContainer width="100%" height={280}>
      <BarChart data={data} margin={{ left: 0, right: 8, top: 4, bottom: 4 }}>
        <CartesianGrid vertical={false} stroke={GRID_STROKE} />
        <XAxis dataKey="sector" tick={AXIS_STYLE} axisLine={false} tickLine={false} />
        <YAxis tick={AXIS_STYLE} axisLine={false} tickLine={false} />
        <Tooltip content={<ChartTooltip />} cursor={{ fill: "rgba(99,102,241,0.04)" }} />
        <Bar dataKey="weight" name="Peso" fill="#6366f1" radius={[4, 4, 0, 0]} barSize={28} />
      </BarChart>
    </ResponsiveContainer>
  );
}

/* ── Cumulative Return Area ───────────────────────────────────────────── */

export function ReturnAreaChart({
  data,
}: {
  data: Array<{ date: string; value: number }>;
}) {
  return (
    <ResponsiveContainer width="100%" height={300}>
      <AreaChart data={data} margin={{ left: 0, right: 8, top: 4, bottom: 4 }}>
        <defs>
          <linearGradient id="returnGradient" x1="0" y1="0" x2="0" y2="1">
            <stop offset="5%" stopColor="#6366f1" stopOpacity={0.3} />
            <stop offset="95%" stopColor="#6366f1" stopOpacity={0} />
          </linearGradient>
        </defs>
        <CartesianGrid stroke={GRID_STROKE} />
        <XAxis dataKey="date" tick={AXIS_STYLE} axisLine={false} tickLine={false} interval="preserveStartEnd" />
        <YAxis
          tick={AXIS_STYLE}
          axisLine={false}
          tickLine={false}
          tickFormatter={(v: number) => `${v.toFixed(1)}%`}
        />
        <Tooltip content={<ChartTooltip />} />
        <Area
          type="monotone"
          dataKey="value"
          name="Retorno %"
          stroke="#6366f1"
          fill="url(#returnGradient)"
          strokeWidth={2}
        />
      </AreaChart>
    </ResponsiveContainer>
  );
}

/* ── Asset Performance Bar (horizontal) ───────────────────────────────── */

export function AssetPerformanceChart({
  data,
}: {
  data: Array<{ ticker: string; return_pct: number }>;
}) {
  return (
    <ResponsiveContainer width="100%" height={Math.max(200, data.length * 36)}>
      <BarChart data={data} layout="vertical" margin={{ left: 8, right: 16, top: 4, bottom: 4 }}>
        <CartesianGrid horizontal={false} stroke={GRID_STROKE} />
        <XAxis
          type="number"
          tick={AXIS_STYLE}
          axisLine={false}
          tickLine={false}
          tickFormatter={(v: number) => `${v.toFixed(1)}%`}
        />
        <YAxis type="category" dataKey="ticker" width={60} tick={AXIS_STYLE} axisLine={false} tickLine={false} />
        <Tooltip content={<ChartTooltip />} cursor={{ fill: "rgba(99,102,241,0.04)" }} />
        <Bar dataKey="return_pct" name="Retorno %" radius={[0, 4, 4, 0]} barSize={20}>
          {data.map((entry, i) => (
            <Cell key={i} fill={entry.return_pct >= 0 ? "#10b981" : "#ef4444"} />
          ))}
        </Bar>
      </BarChart>
    </ResponsiveContainer>
  );
}
