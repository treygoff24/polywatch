import { MarketOverview } from "@/lib/types";
import SectionCard from "./SectionCard";
import LocalizedTime from "./LocalizedTime";

interface MarketOverviewGridProps {
  overview: MarketOverview;
}

const numberFormatter = new Intl.NumberFormat("en-US", {
  maximumFractionDigits: 2
});

const currencyFormatter = new Intl.NumberFormat("en-US", {
  style: "currency",
  currency: "USD",
  maximumFractionDigits: 2
});

const percentFormatter = new Intl.NumberFormat("en-US", {
  style: "percent",
  maximumFractionDigits: 1
});

export default function MarketOverviewGrid({
  overview
}: MarketOverviewGridProps) {
  const { walletCoverage, topWallets } = overview;
  return (
    <SectionCard
      title="Market Overview"
      subtitle="Macro flow from the last ingest window"
    >
      <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-4">
        <Metric
          label="Total trades"
          primary={overview.totalTrades.toLocaleString()}
          secondary={`${currencyFormatter.format(overview.totalNotional)} notional`}
        />
        <Metric
          label="Average trade"
          primary={`${numberFormatter.format(overview.averageSize)} shares`}
          secondary={currencyFormatter.format(overview.averageNotional)}
        />
        <Metric
          label="Top wallet share"
          primary={percentFormatter.format(topWallets.tradesTop1)}
          secondary={`${percentFormatter.format(topWallets.notionalTop1)} of notional`}
        />
        <Metric
          label="Missing wallet stamps"
          primary={`${walletCoverage.missingWallets.toLocaleString()} trades`}
          secondary={percentFormatter.format(walletCoverage.missingShare)}
        />
      </div>

      <div className="mt-6 grid gap-4 md:grid-cols-2">
        {overview.largestBySize ? (
          <Callout
            title="Largest trade (shares)"
            value={`${numberFormatter.format(overview.largestBySize.size)} @ ${(overview.largestBySize.price * 100).toFixed(1)}%`}
            wallet={overview.largestBySize.wallet}
            timestamp={overview.largestBySize.timestamp}
          />
        ) : null}
        {overview.largestByNotional ? (
          <Callout
            title="Largest trade (USDC)"
            value={`${currencyFormatter.format(overview.largestByNotional.notional)} @ ${(overview.largestByNotional.price * 100).toFixed(1)}%`}
            wallet={overview.largestByNotional.wallet}
            timestamp={overview.largestByNotional.timestamp}
          />
        ) : null}
      </div>
    </SectionCard>
  );
}

function Metric({
  label,
  primary,
  secondary
}: {
  label: string;
  primary: string;
  secondary: string;
}) {
  return (
    <div className="rounded-2xl border border-white/10 bg-night-800/70 p-4">
      <p className="text-[0.65rem] uppercase tracking-[0.35em] text-slate-400">
        {label}
      </p>
      <p className="mt-3 font-display text-2xl text-white">{primary}</p>
      <p className="text-xs text-slate-400">{secondary}</p>
    </div>
  );
}

function Callout({
  title,
  value,
  wallet,
  timestamp
}: {
  title: string;
  value: string;
  wallet: string | null;
  timestamp: number;
}) {
  return (
    <div className="rounded-2xl border border-white/10 bg-gradient-to-r from-white/5 to-white/[0.02] p-4">
      <p className="text-xs uppercase tracking-[0.3em] text-neon-cyan">{title}</p>
      <p className="mt-2 font-mono text-xs text-slate-300/70">
        {wallet ?? "unknown"}
      </p>
      <p className="mt-3 text-lg font-semibold text-white">{value}</p>
      <p className="text-[0.7rem] text-slate-400">
        {timestamp ? (
          <LocalizedTime
            value={timestamp * 1000}
            options={{ dateStyle: "medium", timeStyle: "short" }}
          />
        ) : (
          "n/a"
        )}
      </p>
    </div>
  );
}
