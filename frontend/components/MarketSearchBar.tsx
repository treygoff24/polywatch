'use client';

import { ReportIndexEntry } from "@/lib/types";
import Fuse from "fuse.js";
import { useMemo, useState } from "react";
import { useRouter } from "next/navigation";
import { Search } from "lucide-react";
import clsx from "clsx";
import ScoreBadge from "./ScoreBadge";

interface MarketSearchBarProps {
  markets: ReportIndexEntry[];
  className?: string;
}

export default function MarketSearchBar({
  markets,
  className
}: MarketSearchBarProps) {
  const router = useRouter();
  const [query, setQuery] = useState("");
  const [focused, setFocused] = useState(false);

  const fuse = useMemo(
    () =>
      new Fuse(markets, {
        keys: ["title", "slug"],
        threshold: 0.3
      }),
    [markets]
  );

  const results =
    query.trim().length === 0
      ? markets.slice(0, 6)
      : fuse.search(query).slice(0, 6).map((result) => result.item);

  return (
    <div className={clsx("relative", className)}>
      <div className="flex items-center gap-3 rounded-full border border-white/15 bg-white/5 px-5 py-3 backdrop-blur-md focus-within:border-neon-cyan">
        <Search className="h-5 w-5 text-neon-cyan" />
        <input
          value={query}
          onChange={(event) => setQuery(event.target.value)}
          onFocus={() => setFocused(true)}
          onBlur={() => setTimeout(() => setFocused(false), 120)}
          type="search"
          placeholder="Search Polymarket slugs…"
          className="w-full bg-transparent text-sm text-white outline-none placeholder:text-slate-400"
        />
      </div>
      {focused && results.length > 0 ? (
        <ul className="absolute left-0 right-0 z-30 mt-3 space-y-2 rounded-3xl border border-white/10 bg-night-900/95 p-4 shadow-neon backdrop-blur-xl">
          {results.map((entry) => (
            <li key={entry.slug}>
              <button
                type="button"
                onMouseDown={(event) => event.preventDefault()}
                onClick={() => router.push(`/markets/${entry.slug}`)}
                className="flex w-full items-center justify-between gap-4 rounded-2xl border border-white/5 bg-white/5 px-4 py-3 text-left transition hover:border-neon-cyan hover:bg-neon-cyan/10"
              >
                <div>
                  <p className="text-sm font-semibold text-white">
                    {entry.title}
                  </p>
                  <p className="text-xs font-mono text-slate-400">{entry.slug}</p>
                </div>
                <ScoreBadge score={entry.score} label={entry.label} size="sm" />
              </button>
            </li>
          ))}
        </ul>
      ) : null}
    </div>
  );
}

