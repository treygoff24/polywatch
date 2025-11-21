import HeroBanner from "@/components/HeroBanner";
import MarketOverviewGrid from "@/components/MarketOverviewGrid";
import MarketSearchBar from "@/components/MarketSearchBar";
import MarketPulseChart from "@/components/MarketPulseChart";
import MarketHistoryChart from "@/components/MarketHistoryChart";
import OutcomeSnapshotTable from "@/components/OutcomeSnapshotTable";
import SectionCard from "@/components/SectionCard";
import Sparkline from "@/components/Sparkline";
import SuspicionIndicatorsList from "@/components/SuspicionIndicatorsList";
import { getFeaturedReport } from "@/lib/fetchReport";
import { TimeseriesPoint } from "@/lib/types";

const STALE_THRESHOLD_HOURS = Number(
  process.env.REPORT_STALE_HOURS ?? "6"
);
const STALE_THRESHOLD_MS = STALE_THRESHOLD_HOURS * 60 * 60 * 1000;

export default async function Home() {
  const { entry, report, index } = await getFeaturedReport();

  if (!entry || !report) {
    return (
      <main className="mx-auto flex min-h-screen max-w-4xl flex-col items-center justify-center px-6 text-center">
        <h1 className="font-display text-5xl text-white">Polywatch</h1>
        <p className="mt-4 text-slate-300">
          No cached reports available yet. Run{" "}
          <code className="rounded bg-black/40 px-2 py-1 font-mono text-sm text-neon-cyan">
            python scripts/export_report.py
          </code>{" "}
          to generate the JSON dataset.
        </p>
      </main>
    );
  }

  const timeseries = report.analytics.timeseries.perMinute;
  const updatedAtIso = entry?.updatedAt ?? index.generatedAt;
  const updatedAtDate = updatedAtIso ? new Date(updatedAtIso) : null;
  const isStale =
    !updatedAtDate ||
    Date.now() - updatedAtDate.getTime() > STALE_THRESHOLD_MS;
  const updatedLabel = updatedAtDate
    ? updatedAtDate.toUTCString()
    : "unknown";

  return (
    <main className="mx-auto max-w-7xl px-6 py-12 md:px-10 md:py-16">
      <div className="flex flex-col gap-10">
        <HeroBanner entry={entry} />
        <SectionCard
          title="Market Pulse"
          subtitle="Live Polymarket price trace across the current window"
        >
          <MarketPulseChart data={timeseries as TimeseriesPoint[]} />
        </SectionCard>
        {isStale && (
          <SectionCard
            title="Stale snapshot"
            subtitle={`Data older than ${STALE_THRESHOLD_HOURS}h`}
          >
            <p className="text-sm text-slate-100">
              Latest exporter run:{" "}
              <span className="font-mono text-neon-cyan">{updatedLabel}</span>.{" "}
              Refresh the reports branch or fix the exporter workflow to
              restore live data.
            </p>
          </SectionCard>
        )}
        <MarketSearchBar
          markets={[...index.reports].sort(
            (a, b) => b.score - a.score || b.tradeCount - a.tradeCount
          )}
        />

        <MarketHistoryChart data={timeseries as TimeseriesPoint[]} />

        <div className="grid gap-8 lg:grid-cols-[2fr_1fr]">
          <MarketOverviewGrid overview={report.analytics.marketOverview} />
          <SectionCard
            title="Live Flow Trace"
            subtitle="Minute-level prints and VWAP"
          >
            <div className="flex flex-col gap-4">
              <Sparkline
                data={timeseries as TimeseriesPoint[]}
                field="tradeCount"
                label="Trades per minute"
              />
              <Sparkline
                data={timeseries as TimeseriesPoint[]}
                field="vwap"
                label="VWAP by minute"
              />
            </div>
          </SectionCard>
        </div>

        <OutcomeSnapshotTable outcomes={report.analytics.outcomes} />
        <SuspicionIndicatorsList heuristics={report.heuristics} />
      </div>
    </main>
  );
}
