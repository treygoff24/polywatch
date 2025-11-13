import { ReportIndexEntry } from "@/lib/types";
import clsx from "clsx";
import ScoreBadge from "./ScoreBadge";
import LocalizedTime from "./LocalizedTime";
import { ReactNode } from "react";

interface HeroBannerProps {
  entry: ReportIndexEntry;
}

export default function HeroBanner({ entry }: HeroBannerProps) {
  const lookbackHours = entry.lookbackSeconds / 3600;
  return (
    <div
      className={clsx(
        "relative overflow-hidden rounded-[2.5rem] border border-cyan-400/20",
        "bg-gradient-to-br from-night-800/80 via-night-900 to-black p-8 md:p-12",
        "shadow-[0_0_65px_rgba(0,245,255,0.4)]"
      )}
    >
      <div className="pointer-events-none absolute inset-0 cyber-grid opacity-25" />
      <div className="pointer-events-none absolute -left-24 -top-24 h-64 w-64 rounded-full bg-neon-cyan/20 blur-3xl" />
      <div className="pointer-events-none absolute -right-32 bottom-0 h-72 w-72 rounded-full bg-neon-magenta/20 blur-3xl" />

      <div className="relative z-10 flex flex-col gap-6">
        <div className="flex flex-col gap-4 md:flex-row md:items-start md:justify-between">
          <div>
            <p className="font-display text-sm uppercase tracking-[0.4em] text-neon-cyan">
              Polymarket anomaly radar
            </p>
            <h1 className="font-display text-4xl leading-tight text-white md:text-5xl lg:text-6xl">
              {entry.title}
            </h1>
            <p className="mt-3 max-w-2xl text-base text-slate-300/80">
              Streaming bot detection heuristics across all outcomes. Lookback window{" "}
              {lookbackHours.toFixed(1)}h • {entry.tradeCount.toLocaleString()} trades processed.
            </p>
          </div>
          <ScoreBadge
            score={entry.score}
            label={entry.label}
            size="lg"
            className="self-start"
          />
        </div>

        <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
          <StatTile
            label="Last ingest"
            value={
              <LocalizedTime
                value={entry.updatedAt}
                options={{ dateStyle: "full", timeStyle: "short" }}
              />
            }
          />
          <StatTile
            label="Last trade"
            value={
              entry.lastTradeTimestamp ? (
                <LocalizedTime
                  value={entry.lastTradeTimestamp * 1000}
                  options={{ dateStyle: "medium", timeStyle: "short" }}
                />
              ) : (
                "n/a"
              )
            }
          />
          <StatTile label="Slug" value={entry.slug} />
          <StatTile
            label="Top drivers"
            value={entry.topSignals.length ? entry.topSignals.slice(0, 3).join(" · ") : "Still warming up"}
          />
        </div>
      </div>
    </div>
  );
}

function StatTile({
  label,
  value
}: {
  label: string;
  value: ReactNode | string;
}) {
  return (
    <div className="rounded-2xl border border-white/10 bg-white/5 p-4 backdrop-blur-md">
      <p className="text-xs uppercase tracking-[0.3em] text-slate-400">{label}</p>
      <p className="mt-2 font-mono text-sm text-slate-100">{value}</p>
    </div>
  );
}
