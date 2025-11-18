import HeroBanner from "@/components/HeroBanner";
import MarketOverviewGrid from "@/components/MarketOverviewGrid";
import MarketSearchBar from "@/components/MarketSearchBar";
import MarketPulseChart from "@/components/MarketPulseChart";
import OutcomeSnapshotTable from "@/components/OutcomeSnapshotTable";
import SectionCard from "@/components/SectionCard";
import Sparkline from "@/components/Sparkline";
import SuspicionIndicatorsList from "@/components/SuspicionIndicatorsList";
import RefreshMarketButton from "@/components/RefreshMarketButton";
import {
  DEFAULT_MARKET_SLUG,
  getLiveReport,
  getReport,
  getReportIndexEntry,
  getResolvedReportIndex
} from "@/lib/fetchReport";
import { isBackendConfigured } from "@/lib/backendClient";
import { TimeseriesPoint } from "@/lib/types";
import type { Metadata } from "next";
import { notFound } from "next/navigation";

export const dynamic = "force-dynamic";

interface MarketPageProps {
  params: Promise<{ slug: string }>;
}

export async function generateMetadata({
  params
}: MarketPageProps): Promise<Metadata> {
  const { slug } = await params;
  const entry = await getReportIndexEntry(slug);
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
  const { slug } = await params;
  const { index, source } = await getResolvedReportIndex();
  const entry = index.reports.find((item) => item.slug === slug);
  if (!entry) {
    notFound();
  }
  const backendConfigured = isBackendConfigured();
  if (!backendConfigured && source === "static" && slug !== DEFAULT_MARKET_SLUG) {
    notFound();
  }

  const report =
    source === "backend" ? await getLiveReport(slug) : await getReport(slug);
  const timeseries = report.analytics.timeseries.perMinute;
  const allowRefresh = source === "backend" && slug !== DEFAULT_MARKET_SLUG;
  const sortedMarkets = [...index.reports].sort(
    (a, b) => b.score - a.score || b.tradeCount - a.tradeCount
  );

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
        <MarketSearchBar markets={sortedMarkets} />
        {allowRefresh ? (
          <div>
            <RefreshMarketButton slug={slug} />
          </div>
        ) : null}

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
