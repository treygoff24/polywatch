'use client';

import { ReportIndexEntry } from "@/lib/types";
import clsx from "clsx";
import Fuse from "fuse.js";
import { Loader2, Search } from "lucide-react";
import { useCallback, useEffect, useMemo, useState } from "react";
import { useRouter } from "next/navigation";
import ScoreBadge from "./ScoreBadge";

interface MarketSearchBarProps {
  markets: ReportIndexEntry[];
  className?: string;
}

interface SearchResult {
  slug: string;
  title: string;
  status?: string;
  cachedReport?: ReportIndexEntry;
}

export default function MarketSearchBar({
  markets,
  className
}: MarketSearchBarProps) {
  const router = useRouter();
  const [query, setQuery] = useState("");
  const [focused, setFocused] = useState(false);
  const [remoteResults, setRemoteResults] = useState<SearchResult[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [refreshingSlug, setRefreshingSlug] = useState<string | null>(null);

  const fuse = useMemo(
    () =>
      new Fuse(markets, {
        keys: ["title", "slug"],
        threshold: 0.3
      }),
    [markets]
  );

  const fallbackResults = useMemo<SearchResult[]>(
    () =>
      markets.slice(0, 6).map((entry) => ({
        slug: entry.slug,
        title: entry.title,
        cachedReport: entry
      })),
    [markets]
  );
  const marketMap = useMemo(() => {
    const map = new Map<string, ReportIndexEntry>();
    for (const entry of markets) {
      map.set(entry.slug, entry);
    }
    return map;
  }, [markets]);

  const localSearch = useCallback(
    (term: string): SearchResult[] => {
      if (!term) {
        return [];
      }
      return fuse
        .search(term)
        .slice(0, 6)
        .map((result) => ({
          slug: result.item.slug,
          title: result.item.title,
          cachedReport: result.item
        }));
    },
    [fuse]
  );

  useEffect(() => {
    const trimmed = query.trim();
    if (trimmed.length < 2) {
      setRemoteResults([]);
      setLoading(false);
      return;
    }
    const controller = new AbortController();
    setRemoteResults(localSearch(trimmed));
    setLoading(true);
    setError(null);
    fetch(`/api/search?q=${encodeURIComponent(trimmed)}&limit=8`, {
      signal: controller.signal
    })
      .then(async (response) => {
        const payload = await response.json();
        if (!response.ok) {
          throw new Error(payload.error ?? "Search failed");
        }
        setRemoteResults(payload.results ?? []);
      })
      .catch((reason: DOMException | Error) => {
        if (reason.name === "AbortError") {
          return;
        }
        setError(reason.message ?? "Search failed");
        setRemoteResults(localSearch(trimmed));
      })
      .finally(() => setLoading(false));
    return () => controller.abort();
  }, [localSearch, query]);

  const visibleResults = query.trim().length === 0
    ? fallbackResults
    : remoteResults.length > 0
      ? remoteResults
      : localSearch(query.trim());

  async function handleSelect(slug: string) {
    setRefreshingSlug(slug);
    setError(null);
    try {
      const response = await fetch(`/api/live-reports/${slug}`, {
        method: "POST",
        headers: { "Content-Type": "application/json" }
      });
      if (!response.ok) {
        const payload = await response.json().catch(() => ({}));
        throw new Error(payload.error ?? "Failed to refresh report");
      }
      router.push(`/markets/${slug}`);
    } catch (refreshError) {
      const message = (refreshError as Error).message;
      setError(message);
      if (marketMap.has(slug)) {
        router.push(`/markets/${slug}`);
      }
    } finally {
      setRefreshingSlug(null);
    }
  }

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
        {loading ? <Loader2 className="h-4 w-4 animate-spin text-white" /> : null}
      </div>
      {(focused || query.trim().length > 0) ? (
        <div className="absolute left-0 right-0 z-30 mt-3 space-y-2 rounded-3xl border border-white/10 bg-night-900/95 p-4 shadow-neon backdrop-blur-xl">
          {error ? (
            <p className="text-sm text-red-300">{error}</p>
          ) : null}
          {visibleResults.length === 0 && !error ? (
            <p className="text-sm text-slate-300">
              {loading ? "Searching…" : "No matching markets yet."}
            </p>
          ) : null}
          <ul className="space-y-2">
            {visibleResults.map((entry) => {
              const score = entry.cachedReport?.score ?? null;
              const label = entry.cachedReport?.label ?? null;
              const isRefreshing = refreshingSlug === entry.slug;
              return (
                <li key={entry.slug}>
                  <button
                    data-testid="market-search-result"
                    type="button"
                    disabled={isRefreshing}
                    onMouseDown={(event) => event.preventDefault()}
                    onClick={() => handleSelect(entry.slug)}
                    className="flex w-full items-center justify-between gap-4 rounded-2xl border border-white/5 bg-white/5 px-4 py-3 text-left transition hover:border-neon-cyan hover:bg-neon-cyan/10 disabled:opacity-70"
                  >
                    <div>
                      <p className="text-sm font-semibold text-white">
                        {entry.title}
                      </p>
                      <p className="text-xs font-mono text-slate-400">
                        {entry.slug}
                      </p>
                      {entry.status ? (
                        <p className="text-xs text-slate-400">
                          Status: {entry.status}
                        </p>
                      ) : null}
                    </div>
                    <div className="flex items-center gap-2">
                      {isRefreshing ? (
                        <Loader2 className="h-4 w-4 animate-spin text-neon-cyan" />
                      ) : score !== null && label ? (
                        <ScoreBadge score={score} label={label} size="sm" />
                      ) : null}
                    </div>
                  </button>
                </li>
              );
            })}
          </ul>
        </div>
      ) : null}
    </div>
  );
}
