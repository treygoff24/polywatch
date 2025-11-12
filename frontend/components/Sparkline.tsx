'use client';

import { TimeseriesPoint } from "@/lib/types";
import {
  Area,
  AreaChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis
} from "recharts";

interface SparklineProps {
  data: TimeseriesPoint[];
  field: "tradeCount" | "vwap";
  label: string;
  height?: number;
}

export default function Sparkline({
  data,
  field,
  label,
  height = 140
}: SparklineProps) {
  if (!data.length) {
    return (
      <div className="flex h-[140px] items-center justify-center rounded-2xl border border-white/10 bg-white/5 text-xs text-slate-400">
        No activity sampled
      </div>
    );
  }

  const gradientId = `gradient-${field}`;

  return (
    <div className="rounded-2xl border border-white/10 bg-black/30 p-4">
      <div className="mb-2 text-xs uppercase tracking-[0.3em] text-slate-400">
        {label}
      </div>
      <ResponsiveContainer width="100%" height={height}>
        <AreaChart data={data}>
          <defs>
            <linearGradient id={gradientId} x1="0" y1="0" x2="0" y2="1">
              <stop offset="0%" stopColor="#00f5ff" stopOpacity={0.7} />
              <stop offset="100%" stopColor="#00f5ff" stopOpacity={0} />
            </linearGradient>
          </defs>
          <XAxis
            dataKey="iso"
            hide
            padding={{ left: 10, right: 10 }}
            tickFormatter={(iso) => new Date(iso).toLocaleTimeString()}
          />
          <YAxis hide domain={["auto", "auto"]} />
          <Tooltip
            contentStyle={{
              background: "rgba(10,12,18,0.9)",
              borderRadius: "0.75rem",
              border: "1px solid rgba(0,245,255,0.3)"
            }}
            formatter={(value: number) =>
              field === "vwap" ? `${(value * 100).toFixed(2)}%` : value
            }
            labelFormatter={(iso: string) =>
              new Date(iso).toLocaleString(undefined, {
                hour: "2-digit",
                minute: "2-digit"
              })
            }
          />
          <Area
            type="monotone"
            dataKey={field}
            stroke="#00f5ff"
            strokeWidth={2}
            fill={`url(#${gradientId})`}
            dot={false}
            isAnimationActive={false}
          />
        </AreaChart>
      </ResponsiveContainer>
    </div>
  );
}

