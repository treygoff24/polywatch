import HeroBanner from "@/components/HeroBanner";
import MarketOverviewGrid from "@/components/MarketOverviewGrid";
import MarketSearchBar from "@/components/MarketSearchBar";
import OutcomeSnapshotTable from "@/components/OutcomeSnapshotTable";
import SectionCard from "@/components/SectionCard";
import Sparkline from "@/components/Sparkline";
import SuspicionIndicatorsList from "@/components/SuspicionIndicatorsList";
import {
  getReport,
  getReportIndex,
  getReportIndexEntry
} from "@/lib/fetchReport";
import { TimeseriesPoint } from "@/lib/types";
import type { Metadata } from "next";
import { notFound } from "next/navigation";

interface MarketPageProps {
  params: { slug: string };
}

export async function generateMetadata({
  params
}: MarketPageProps): Promise<Metadata> {
  const entry = await getReportIndexEntry(params.slug);
  if (!entry) {
    return {
      title: "Market not found - Polywatch"
    };
  }
  return {
    title: `${entry.title} – Polywatch`,
    description: `Suspicion score ${entry.score.toFixed(1)} (${entry.label}).`
  };
}

export default async function MarketPage({ params }: MarketPageProps) {
  const index = await getReportIndex();
  const entry = index.reports.find((item) => item.slug === params.slug);
  if (!entry) {
    notFound();
  }
  const report = await getReport(entry.slug);

  const timeseries = report.analytics.timeseries.perMinute;

  return (
    <main className="mx-auto max-w-7xl px-6 py-12 md:px-10 md:py-16">
      <div className="flex flex-col gap-10">
        <HeroBanner entry={entry} />
        <MarketSearchBar
          markets={[...index.reports].sort(
            (a, b) => b.score - a.score || b.tradeCount - a.tradeCount
          )}
        />

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
