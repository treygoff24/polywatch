import { OutcomeSummary } from "@/lib/types";
import SectionCard from "./SectionCard";
import ScoreBadge from "./ScoreBadge";

interface OutcomeSnapshotTableProps {
  outcomes: OutcomeSummary[];
}

const currencyFormatter = new Intl.NumberFormat("en-US", {
  style: "currency",
  currency: "USD",
  maximumFractionDigits: 2
});

const percentFormatter = new Intl.NumberFormat("en-US", {
  style: "percent",
  maximumFractionDigits: 1
});

const numberFormatter = new Intl.NumberFormat("en-US", {
  maximumFractionDigits: 2
});

export default function OutcomeSnapshotTable({
  outcomes
}: OutcomeSnapshotTableProps) {
  return (
    <SectionCard
      title="Outcome Snapshot"
      subtitle="Per-outcome flow, VWAP, and suspicion scoring"
    >
      <div className="overflow-x-auto">
        <table className="min-w-full divide-y divide-white/10 text-sm">
          <thead>
            <tr className="text-left text-xs uppercase tracking-[0.35em] text-slate-400">
              <th className="py-3 pr-8 font-normal">Outcome</th>
              <th className="py-3 pr-6 font-normal">Trades</th>
              <th className="py-3 pr-6 font-normal">Notional</th>
              <th className="py-3 pr-6 font-normal">Volume %</th>
              <th className="py-3 pr-6 font-normal">VWAP</th>
              <th className="py-3 pr-6 font-normal">Last</th>
              <th className="py-3 font-normal">Suspicion</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-white/5">
            {outcomes.map((outcome) => (
              <tr key={`${outcome.conditionId}-${outcome.outcomeIndex}`}>
                <td className="py-4 pr-8 text-sm text-white">
                  <div className="font-semibold">{outcome.label}</div>
                  <div className="text-xs text-slate-400">
                    {outcome.heuristics
                      .filter((h) => h.triggered)
                      .slice(0, 2)
                      .map((h) => h.summary)
                      .join(" · ") || outcome.labelText}
                  </div>
                </td>
                <td className="py-4 pr-6 font-mono text-xs text-slate-200">
                  {outcome.tradeCount.toLocaleString()}
                </td>
                <td className="py-4 pr-6 font-mono text-xs text-slate-200">
                  {currencyFormatter.format(outcome.notional)}
                </td>
                <td className="py-4 pr-6 font-mono text-xs text-slate-200">
                  {percentFormatter.format(outcome.volumeShare)}
                </td>
                <td className="py-4 pr-6 font-mono text-xs text-slate-200">
                  {(outcome.vwap * 100).toFixed(1)}%
                </td>
                <td className="py-4 pr-6 font-mono text-xs text-slate-200">
                  {outcome.lastPrice != null
                    ? `${numberFormatter.format(outcome.lastPrice * 100)}%`
                    : "—"}
                </td>
                <td className="py-4">
                  <ScoreBadge score={outcome.score} label={outcome.labelText} size="sm" />
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </SectionCard>
  );
}

