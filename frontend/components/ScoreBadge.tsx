import clsx from "clsx";

interface ScoreBadgeProps {
  score: number;
  label: string;
  className?: string;
  size?: "sm" | "md" | "lg";
}

function badgeColor(label: string) {
  switch (label.toLowerCase()) {
    case "suspicious":
      return "from-neon-magenta to-rose-500 text-white";
    case "watch":
      return "from-amber-400 to-orange-500 text-slate-900";
    default:
      return "from-emerald-400 to-teal-500 text-slate-900";
  }
}

export default function ScoreBadge({
  score,
  label,
  className,
  size = "md"
}: ScoreBadgeProps) {
  const sizing =
    size === "lg"
      ? "px-5 py-2 text-lg"
      : size === "sm"
        ? "px-2.5 py-1 text-xs"
        : "px-4 py-1.5 text-sm";

  return (
    <span
      className={clsx(
        "inline-flex items-center gap-2 rounded-full bg-gradient-to-r font-semibold uppercase tracking-widest",
        "shadow-[0_0_25px_rgba(255,0,255,0.35)]",
        badgeColor(label),
        sizing,
        className
      )}
    >
      <span>{label}</span>
      <span className="font-display text-white drop-shadow-lg">{score.toFixed(1)}</span>
    </span>
  );
}

