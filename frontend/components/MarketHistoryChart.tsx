'use client';

import { TimeseriesPoint } from "@/lib/types";
import clsx from "clsx";
import React, { useMemo } from "react";
import {
  CartesianGrid,
  Line,
  LineChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
  Legend
} from "recharts";

interface MarketHistoryChartProps {
  data: TimeseriesPoint[];
}

const COLORS = [
  "#F97316", // Orange
  "#38BDF8", // Sky Blue
  "#3B82F6", // Blue
  "#EAB308", // Yellow
  "#A855F7", // Purple
  "#EC4899", // Pink
  "#10B981", // Emerald
  "#F43F5E", // Rose
];

export default function MarketHistoryChart({ data }: MarketHistoryChartProps) {
  const { chartData, outcomeKeys, yDomain } = useMemo(() => {
    const allKeys = new Set<string>();
    
    // Filter data to only include points that have outcome data
    const validData = data.filter(d => d.outcomes && Object.keys(d.outcomes).length > 0);
    
    // First pass: collect all available keys
    validData.forEach(point => {
      if (point.outcomes) {
        Object.keys(point.outcomes).forEach(k => allKeys.add(k));
      }
    });

    const allKeysArray = Array.from(allKeys);
    
    // Filter logic: If " (Yes)" keys exist, prefer them to match Polymarket's default view
    const yesKeys = allKeysArray.filter(k => k.endsWith("(Yes)"));
    // If no "(Yes)" keys found (non-standard market), fall back to all keys
    const finalKeys = yesKeys.length > 0 ? yesKeys : allKeysArray;
    const finalKeysSet = new Set(finalKeys);
    
    // Second pass: Determine min/max ONLY for the selected keys
    let minVal = 1;
    let maxVal = 0;
    let hasValues = false;

    validData.forEach(point => {
        if (point.outcomes) {
            Object.entries(point.outcomes).forEach(([k, v]) => {
                if (finalKeysSet.has(k)) {
                    hasValues = true;
                    if (v < minVal) minVal = v;
                    if (v > maxVal) maxVal = v;
                }
            });
        }
    });

    const sortedKeys = finalKeys.sort();
    
    // Transform data for Recharts: flatten outcomes into the main object
    const formatted = validData.map(point => ({
        timestamp: point.timestamp,
        iso: point.iso,
        ...point.outcomes
    }));

    // Handle case with no data
    if (!hasValues || minVal > maxVal) {
        minVal = 0;
        maxVal = 1;
    }

    // 10% buffer below min and above max, clamped to [0, 1]
    // Use 10% of the value itself for relative padding
    const lower = Math.max(0, minVal * 0.9);
    const upper = Math.min(1, maxVal * 1.1);

    return { 
        chartData: formatted, 
        outcomeKeys: sortedKeys,
        yDomain: [lower, upper] as [number, number]
    };
  }, [data]);

  if (!chartData.length) {
    return null;
  }

  return (
    <div className="rounded-2xl border border-white/10 bg-night-900/50 p-6 backdrop-blur-sm">
      <div className="mb-6 flex items-center justify-between">
        <div>
            <h3 className="text-lg font-semibold text-white">Market History</h3>
            <p className="text-sm text-slate-400">Probability over time by outcome</p>
        </div>
      </div>
      
      <div className="h-[400px] w-full">
        <ResponsiveContainer width="100%" height="100%">
          <LineChart data={chartData} margin={{ top: 10, right: 10, left: -20, bottom: 0 }}>
            <CartesianGrid
              stroke="rgba(148, 163, 184, 0.1)"
              strokeDasharray="4 6"
              vertical={false}
            />
            <XAxis
              dataKey="iso"
              stroke="rgba(255,255,255,0.1)"
              tickFormatter={formatAxisTick}
              tick={{ fill: "#94a3b8", fontSize: 11 }}
              minTickGap={40}
            />
            <YAxis
              stroke="rgba(255,255,255,0.1)"
              tickFormatter={(value) => `${(value * 100).toFixed(0)}%`}
              tick={{ fill: "#94a3b8", fontSize: 11 }}
              domain={yDomain}
              allowDataOverflow={true} 
            />
            <Tooltip
              contentStyle={{
                backgroundColor: "rgba(15, 23, 42, 0.95)",
                borderRadius: "0.75rem",
                border: "1px solid rgba(255,255,255,0.1)",
                boxShadow: "0 4px 6px -1px rgba(0, 0, 0, 0.5)",
                fontSize: "12px"
              }}
              itemStyle={{ padding: "2px 0" }}
              formatter={(value: number) => [`${(value * 100).toFixed(1)}%`, ""]}
              labelFormatter={formatTooltipLabel}
            />
            <Legend 
                wrapperStyle={{ paddingTop: '20px' }}
                formatter={formatLegendLabel}
            />
            {outcomeKeys.map((key, index) => (
              <Line
                key={key}
                type="monotone"
                dataKey={key}
                stroke={COLORS[index % COLORS.length]}
                strokeWidth={2}
                dot={false}
                activeDot={{ r: 4, strokeWidth: 0 }}
                connectNulls
                animationDuration={1000}
              />
            ))}
          </LineChart>
        </ResponsiveContainer>
      </div>
    </div>
  );
}

function formatAxisTick(iso: string): string {
  return new Date(iso).toLocaleDateString(undefined, {
    month: "short",
    day: "numeric"
  });
}

function formatTooltipLabel(value: string): string {
  return new Date(value).toLocaleString(undefined, {
    month: "short",
    day: "numeric",
    hour: "2-digit",
    minute: "2-digit"
  });
}

function formatLegendLabel(value: string): React.ReactNode {
  // Try to extract name from "Will [Name] win...?"
  const match = value.match(/^Will (.+?) win/);
  if (match && match[1]) {
     // For legend, if we are filtering to Yes-only, we can drop the suffix completely
     // But we should check if the original had (Yes) to be safe.
     // The regex checks for (Yes) or (No).
     // If we are in Yes-only mode (which we usually are), we just return the name.
     return <span className="text-slate-300 text-xs">{match[1]}</span>;
  }
  return <span className="text-slate-300 text-xs">{value}</span>;
}
