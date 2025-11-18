import fs from "node:fs/promises";
import path from "node:path";
import { backendFetch, isBackendConfigured } from "./backendClient";
import { ReportIndex, ReportIndexEntry, ReportPayload } from "./types";

type ErrnoException = NodeJS.ErrnoException;

const DEFAULT_REPORTS_DIR = path.resolve(process.cwd(), "..", "docs", "reports");

const REPORTS_FILE_ROOT = process.env.REPORTS_FILE_ROOT ?? DEFAULT_REPORTS_DIR;
const inferredReportsBase =
  process.env.REPORTS_BASE_URL ?? process.env.NEXT_PUBLIC_REPORTS_BASE_URL;
const repoOwner = process.env.VERCEL_GIT_REPO_OWNER;
const repoSlug = process.env.VERCEL_GIT_REPO_SLUG;
const reportsBranchUrl =
  inferredReportsBase ??
  (repoOwner && repoSlug
    ? `https://raw.githubusercontent.com/${repoOwner}/${repoSlug}/reports/docs/reports`
    : undefined);
const REPORTS_BASE_URL = reportsBranchUrl;
const REQUIRE_REMOTE_REPORTS =
  process.env.FORCE_REMOTE_REPORTS === "1" ||
  process.env.NODE_ENV === "production";
const EMPTY_REPORT_INDEX: ReportIndex = {
  generatedAt: new Date(0).toISOString(),
  reports: []
};
const LOCAL_INDEX_FILE = path.resolve(REPORTS_FILE_ROOT, "index.json");
const REMOTE_INDEX_TTL_MS = 30 * 1000;
export const DEFAULT_MARKET_SLUG =
  process.env.DEFAULT_MARKET_SLUG ?? "honduras-presidential-election";

export class ReportFetchError extends Error {
  status: number;

  constructor(message: string, status = 500) {
    super(message);
    this.name = "ReportFetchError";
    this.status = status;
  }
}

let cachedLocalIndex:
  | {
      data: ReportIndex;
      mtimeMs: number;
    }
  | null = null;
let cachedRemoteIndex:
  | {
      data: ReportIndex;
      expiresAt: number;
    }
  | null = null;

async function readLocalJson<T>(relative: string): Promise<T | null> {
  const filePath = path.resolve(REPORTS_FILE_ROOT, relative);
  try {
    const contents = await fs.readFile(filePath, "utf-8");
    return JSON.parse(contents) as T;
  } catch (error) {
    const err = error as ErrnoException;
    if (err.code === "ENOENT") {
      return null;
    }
    throw error;
  }
}

async function fetchRemoteJson<T>(relative: string): Promise<T> {
  if (!REPORTS_BASE_URL) {
    throw new Error(
      "Reports base URL not configured. Set REPORTS_BASE_URL or provide local data via REPORTS_FILE_ROOT."
    );
  }
  const trimmedBase = REPORTS_BASE_URL.replace(/\/+$/, "");
  const url = `${trimmedBase}/${relative}`;
  const res = await fetch(url, {
    headers: { "Accept": "application/json" },
    next: { revalidate: 300 }
  });
  if (!res.ok) {
    throw new Error(`Failed to fetch ${url}: ${res.status} ${res.statusText}`);
  }
  return (await res.json()) as T;
}

function ensureRemoteConfigured(): void {
  if (REQUIRE_REMOTE_REPORTS && !REPORTS_BASE_URL) {
    throw new Error(
      "Reports base URL must be configured for production builds. Set REPORTS_BASE_URL or NEXT_PUBLIC_REPORTS_BASE_URL."
    );
  }
}

async function fetchBackendIndex(): Promise<ReportIndex | null> {
  if (!isBackendConfigured()) {
    return null;
  }
  const response = await backendFetch("/reports/index");
  if (!response.ok) {
    throw new Error(
      `Backend index request failed: ${response.status} ${response.statusText}`
    );
  }
  return (await response.json()) as ReportIndex;
}

export async function getReportIndex(): Promise<ReportIndex> {
  ensureRemoteConfigured();
  if (REPORTS_BASE_URL) {
    try {
      return await fetchRemoteIndex();
    } catch (error) {
      if (REQUIRE_REMOTE_REPORTS) {
        throw error;
      }
      // fall back to local cache while developing
    }
  }

  const local = await readLocalIndex();
  if (local) {
    return local;
  }

  return { ...EMPTY_REPORT_INDEX };
}

export async function getReportIndexEntry(
  slug: string
): Promise<ReportIndexEntry | null> {
  const { index } = await getResolvedReportIndex();
  return index.reports.find((entry) => entry.slug === slug) ?? null;
}

export async function getResolvedReportIndex(): Promise<{
  index: ReportIndex;
  source: "backend" | "static";
}> {
  try {
    const backendIndex = await fetchBackendIndex();
    if (backendIndex) {
      return { index: backendIndex, source: "backend" };
    }
  } catch (error) {
    if (process.env.NODE_ENV !== "production") {
      console.warn("Falling back to static index:", error);
    }
  }
  const fallback = await getReportIndex();
  return { index: fallback, source: "static" };
}

export async function getReport(slug: string): Promise<ReportPayload> {
  ensureRemoteConfigured();
  if (REPORTS_BASE_URL) {
    try {
      return await fetchRemoteJson<ReportPayload>(`${slug}.json`);
    } catch (error) {
      if (REQUIRE_REMOTE_REPORTS) {
        throw error;
      }
      // fall back to local cache while developing
    }
  }

  const local = await readLocalJson<ReportPayload>(`${slug}.json`);
  if (local) {
    return local;
  }

  throw new Error(
    REPORTS_BASE_URL
      ? `Report ${slug} not found remotely or locally.`
      : `Report ${slug} not found locally. Run the exporter or set REPORTS_BASE_URL.`
  );
}

export async function getLiveReport(slug: string): Promise<ReportPayload> {
  try {
    const response = await backendFetch(`/reports/${slug}`);
    if (!response.ok) {
      throw new ReportFetchError(
        `Backend report ${slug} failed: ${response.status} ${response.statusText}`,
        response.status || 500
      );
    }
    return (await response.json()) as ReportPayload;
  } catch (error) {
    if (error instanceof ReportFetchError) {
      throw error;
    }
    throw new ReportFetchError(
      `Backend report ${slug} failed: ${(error as Error).message}`,
      502
    );
  }
}

export async function getFeaturedReport(): Promise<{
  entry: ReportIndexEntry | null;
  report: ReportPayload | null;
  index: ReportIndex;
}> {
  const { index, source } = await getResolvedReportIndex();
  if (index.reports.length === 0) {
    return { entry: null, report: null, index };
  }
  const sorted = [...index.reports].sort(
    (a, b) => b.score - a.score || b.tradeCount - a.tradeCount
  );
  const entry =
    index.reports.find((item) => item.slug === DEFAULT_MARKET_SLUG) ??
    sorted[0];
  const report =
    source === "backend" ? await getLiveReport(entry.slug) : await getReport(entry.slug);
  return { entry, report, index };
}

async function readLocalIndex(): Promise<ReportIndex | null> {
  try {
    const stats = await fs.stat(LOCAL_INDEX_FILE);
    if (cachedLocalIndex && cachedLocalIndex.mtimeMs === stats.mtimeMs) {
      return cachedLocalIndex.data;
    }
    const contents = await fs.readFile(LOCAL_INDEX_FILE, "utf-8");
    const parsed = JSON.parse(contents) as ReportIndex;
    cachedLocalIndex = { data: parsed, mtimeMs: stats.mtimeMs };
    return parsed;
  } catch (error) {
    const err = error as ErrnoException;
    if (err.code === "ENOENT") {
      cachedLocalIndex = null;
      return null;
    }
    throw error;
  }
}

async function fetchRemoteIndex(): Promise<ReportIndex> {
  const now = Date.now();
  if (cachedRemoteIndex && cachedRemoteIndex.expiresAt > now) {
    return cachedRemoteIndex.data;
  }
  const data = await fetchRemoteJson<ReportIndex>("index.json");
  cachedRemoteIndex = { data, expiresAt: now + REMOTE_INDEX_TTL_MS };
  return data;
}
