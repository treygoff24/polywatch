export interface Heuristic {
  name: string;
  triggered: boolean;
  intensity: number;
  summary: string;
}

export interface OutcomeSummary {
  label: string;
  conditionId: string;
  outcomeIndex: number | null;
  tradeCount: number;
  notional: number;
  volumeShare: number;
  vwap: number;
  lastPrice: number | null;
  score: number;
  labelText: string;
  heuristics: Heuristic[];
}

export interface MarketOverview {
  totalTrades: number;
  totalSize: number;
  totalNotional: number;
  averageSize: number;
  averageNotional: number;
  walletCoverage: {
    uniqueWallets: number;
    missingWallets: number;
    missingShare: number;
  };
  topWallets: {
    tradesTop1: number;
    tradesTop3: number;
    notionalTop1: number;
    notionalTop3: number;
  };
  largestBySize?: {
    size: number;
    price: number;
    wallet: string | null;
    timestamp: number;
  };
  largestByNotional?: {
    notional: number;
    size: number;
    price: number;
    wallet: string | null;
    timestamp: number;
  };
}

export interface TimeseriesPoint {
  timestamp: number;
  iso: string;
  tradeCount: number;
  vwap?: number;
}

export interface ReportAnalytics {
  marketOverview: MarketOverview;
  outcomes: OutcomeSummary[];
  timeseries: {
    perMinute: TimeseriesPoint[];
  };
}

export interface ReportPayload {
  event: {
    title: string;
    slug: string;
    id: number;
  };
  score: number;
  label: string;
  heuristics: Heuristic[];
  outcomes: {
    label: string;
    conditionId: string;
    outcomeIndex: number | null;
    score: number;
    labelText: string;
    heuristics: Heuristic[];
  }[];
  analytics: ReportAnalytics;
  lookbackSeconds?: number;
}

export interface ReportIndexEntry {
  slug: string;
  eventId: number;
  title: string;
  label: string;
  score: number;
  updatedAt: string;
  lookbackSeconds: number;
  tradeCount: number;
  lastTradeTimestamp: number | null;
  topSignals: string[];
  outcomes: Array<{
    label: string;
    score: number;
    labelText: string;
  }>;
}

export interface ReportIndex {
  generatedAt: string;
  reports: ReportIndexEntry[];
}

