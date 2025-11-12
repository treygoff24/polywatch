import fs from "node:fs/promises";
import path from "node:path";
import { ReportIndex, ReportIndexEntry, ReportPayload } from "./types";

type ErrnoException = NodeJS.ErrnoException;

const DEFAULT_REPORTS_DIR = path.resolve(process.cwd(), "..", "docs", "reports");

const REPORTS_FILE_ROOT = process.env.REPORTS_FILE_ROOT ?? DEFAULT_REPORTS_DIR;
const REPORTS_BASE_URL =
  process.env.REPORTS_BASE_URL ?? process.env.NEXT_PUBLIC_REPORTS_BASE_URL;
const EMPTY_REPORT_INDEX: ReportIndex = {
  generatedAt: new Date(0).toISOString(),
  reports: []
};
const LOCAL_INDEX_FILE = path.resolve(REPORTS_FILE_ROOT, "index.json");
const REMOTE_INDEX_TTL_MS = 30 * 1000;

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

export async function getReportIndex(): Promise<ReportIndex> {
  if (REPORTS_BASE_URL) {
    try {
      return await fetchRemoteIndex();
    } catch {
      // fall back to local cache
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
  const index = await getReportIndex();
  return index.reports.find((entry) => entry.slug === slug) ?? null;
}

export async function getReport(slug: string): Promise<ReportPayload> {
  if (REPORTS_BASE_URL) {
    try {
      return await fetchRemoteJson<ReportPayload>(`${slug}.json`);
    } catch {
      // fall back to local cache
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

export async function getFeaturedReport(): Promise<{
  entry: ReportIndexEntry | null;
  report: ReportPayload | null;
  index: ReportIndex;
}> {
  const index = await getReportIndex();
  if (index.reports.length === 0) {
    return { entry: null, report: null, index };
  }
  const sorted = [...index.reports].sort(
    (a, b) => b.score - a.score || b.tradeCount - a.tradeCount
  );
  const entry = sorted[0];
  const report = await getReport(entry.slug);
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
