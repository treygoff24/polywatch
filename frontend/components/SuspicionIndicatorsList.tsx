import { Heuristic } from "@/lib/types";
import { AlertTriangle, CheckCircle2, Zap } from "lucide-react";
import SectionCard from "./SectionCard";

interface SuspicionIndicatorsListProps {
  heuristics: Heuristic[];
}

export default function SuspicionIndicatorsList({
  heuristics
}: SuspicionIndicatorsListProps) {
  return (
    <SectionCard
      title="Suspicion Indicators"
      subtitle="Thresholded heuristics with intensity scaling"
    >
      <ul className="flex flex-col gap-4">
        {heuristics.map((heuristic) => (
          <li
            key={heuristic.name}
            className="flex flex-col gap-2 rounded-2xl border border-white/10 bg-white/5 p-4"
          >
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-3">
                <BadgeIcon triggered={heuristic.triggered} />
                <p className="font-semibold uppercase tracking-[0.3em] text-slate-200">
                  {heuristic.name.replace(/_/g, " ")}
                </p>
              </div>
              <span className="font-mono text-xs text-neon-cyan">
                intensity {heuristic.intensity.toFixed(2)}
              </span>
            </div>
            <p className="text-sm text-slate-300">{heuristic.summary}</p>
            <div className="h-1 overflow-hidden rounded-full bg-black/40">
              <div
                className="h-full bg-gradient-to-r from-neon-magenta to-neon-cyan"
                style={{ width: `${Math.min(heuristic.intensity, 1) * 100}%` }}
              />
            </div>
          </li>
        ))}
      </ul>
    </SectionCard>
  );
}

function BadgeIcon({ triggered }: { triggered: boolean }) {
  const Icon = triggered ? AlertTriangle : CheckCircle2;
  const color = triggered ? "text-neon-magenta" : "text-emerald-400";
  return <Icon className={`h-5 w-5 ${color}`} strokeWidth={2.5} />;
}

