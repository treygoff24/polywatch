'use client';

import { TimeseriesPoint } from "@/lib/types";
import clsx from "clsx";
import { useId, useMemo } from "react";
import {
  Area,
  AreaChart,
  CartesianGrid,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis
} from "recharts";

interface MarketPulseChartProps {
  data: TimeseriesPoint[];
}

interface PricePoint extends TimeseriesPoint {
  vwap: number;
}

export default function MarketPulseChart({ data }: MarketPulseChartProps) {
  const gradientId = useId();
  const priceSeries = useMemo<PricePoint[]>(
    () =>
      data
        .filter((point): point is PricePoint => typeof point.vwap === "number")
        .sort((a, b) => a.timestamp - b.timestamp),
    [data]
  );

  if (!priceSeries.length) {
    return (
      <div className="flex h-72 items-center justify-center rounded-2xl border border-white/10 bg-black/20 text-sm text-slate-400">
        Market flow chart will appear once VWAP samples arrive.
      </div>
    );
  }

  const firstPoint = priceSeries[0];
  const latestPoint = priceSeries[priceSeries.length - 1];
  const change = latestPoint.vwap - firstPoint.vwap;
  const low = Math.min(...priceSeries.map((point) => point.vwap));
  const high = Math.max(...priceSeries.map((point) => point.vwap));
  const lookbackSeconds = latestPoint.timestamp - firstPoint.timestamp;
  const windowLabel = formatWindowDuration(lookbackSeconds);
  const pad = Math.max((high - low) * 0.25, 0.02);
  const yDomain: [number, number] = [
    Math.max(low - pad, 0),
    Math.min(high + pad, 1)
  ];
  const deltaClass =
    change === 0
      ? "text-slate-200"
      : change > 0
        ? "text-emerald-400"
        : "text-rose-400";

  return (
    <div className="space-y-6">
      <div className="grid gap-6 md:grid-cols-3">
        <Stat
          label="Current price"
          value={formatPercent(latestPoint.vwap)}
          footer={`as of ${formatTooltipLabel(latestPoint.iso)}`}
        />
        <Stat
          label="Lookback change"
          value={`${change >= 0 ? "+" : ""}${(change * 100).toFixed(2)} pts`}
          valueClassName={deltaClass}
          footer={`${formatPercent(firstPoint.vwap)} → ${formatPercent(latestPoint.vwap)}`}
        />
        <Stat
          label="Range"
          value={`${formatPercent(low)} – ${formatPercent(high)}`}
          footer={windowLabel}
        />
      </div>
      <div className="h-72 w-full rounded-[1.75rem] border border-white/10 bg-gradient-to-br from-night-900/80 to-black p-4">
        <ResponsiveContainer width="100%" height="100%">
          <AreaChart data={priceSeries} margin={{ top: 10, right: 0, left: 0, bottom: 0 }}>
            <defs>
              <linearGradient id={gradientId} x1="0" y1="0" x2="0" y2="1">
                <stop offset="0%" stopColor="#ff73fa" stopOpacity={0.8} />
                <stop offset="100%" stopColor="#00f5ff" stopOpacity={0.05} />
              </linearGradient>
            </defs>
            <CartesianGrid
              stroke="rgba(148, 163, 184, 0.2)"
              strokeDasharray="4 6"
              vertical={false}
            />
            <XAxis
              dataKey="iso"
              stroke="rgba(255,255,255,0.08)"
              tickFormatter={formatAxisTick}
              tick={{ fill: "#cbd5f5", fontSize: 12 }}
              minTickGap={32}
              padding={{ left: 10, right: 10 }}
            />
            <YAxis
              domain={yDomain}
              stroke="rgba(255,255,255,0.08)"
              tickFormatter={(value) => formatPercent(Number(value))}
              tick={{ fill: "#cbd5f5", fontSize: 12 }}
              width={70}
            />
            <Tooltip
              contentStyle={{
                backgroundColor: "rgba(2,6,23,0.95)",
                borderRadius: "1rem",
                border: "1px solid rgba(0,245,255,0.3)"
              }}
              itemStyle={{ color: "#fff" }}
              formatter={(value: number | string) => formatPercent(Number(value))}
              labelFormatter={formatTooltipLabel}
            />
            <Area
              type="monotone"
              dataKey="vwap"
              stroke="#00f5ff"
              strokeWidth={2.5}
              fill={`url(#${gradientId})`}
              dot={false}
              isAnimationActive={false}
            />
          </AreaChart>
        </ResponsiveContainer>
      </div>
    </div>
  );
}

function Stat({
  label,
  value,
  valueClassName,
  footer
}: {
  label: string;
  value: string;
  valueClassName?: string;
  footer?: string;
}) {
  return (
    <div className="rounded-2xl border border-white/10 bg-white/5 p-4">
      <p className="text-xs uppercase tracking-[0.35em] text-slate-400">{label}</p>
      <p className={clsx("mt-2 font-mono text-2xl text-white", valueClassName)}>{value}</p>
      {footer ? <p className="mt-1 text-xs text-slate-400">{footer}</p> : null}
    </div>
  );
}

function formatPercent(value: number): string {
  return `${(value * 100).toFixed(2)}%`;
}

function formatAxisTick(iso: string): string {
  return new Date(iso).toLocaleTimeString(undefined, {
    hour: "2-digit",
    minute: "2-digit"
  });
}

function formatTooltipLabel(value: string): string {
  return new Date(value).toLocaleString(undefined, {
    month: "short",
    day: "2-digit",
    hour: "2-digit",
    minute: "2-digit"
  });
}

function formatWindowDuration(seconds: number): string {
  if (seconds <= 0) {
    return "single sample";
  }
  const hours = seconds / 3600;
  if (hours >= 1) {
    return `${hours.toFixed(1)}h window`;
  }
  const minutes = Math.max(1, Math.round(seconds / 60));
  return `${minutes}m window`;
}
