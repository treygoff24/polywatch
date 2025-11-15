from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List, Optional, Sequence

from .api import PolymarketClient
from .models import EventScore, Trade
from .render import event_score_to_dict
from .scoring import analyze_event
from .utils import rolling_minutes, unix_to_iso, vwap_by_minute

ReportPayload = Dict[str, object]
ReportSummary = Dict[str, object]


def _market_overview(trades: Sequence[Trade]) -> Dict[str, object]:
    total_trades = len(trades)
    total_size = sum(trade.size for trade in trades)
    total_notional = sum(trade.size * trade.price for trade in trades)
    avg_size = total_size / total_trades if total_trades else 0.0
    avg_notional = total_notional / total_trades if total_trades else 0.0
    largest_by_size = max(trades, key=lambda t: t.size, default=None)
    largest_by_notional = max(trades, key=lambda t: t.size * t.price, default=None)

    wallet_counts: Dict[str, int] = {}
    wallet_notional: Dict[str, float] = {}
    missing_wallets = 0
    for trade in trades:
        wallet = trade.proxy_wallet
        if wallet:
            wallet_counts[wallet] = wallet_counts.get(wallet, 0) + 1
            wallet_notional[wallet] = wallet_notional.get(wallet, 0.0) + trade.size * trade.price
        else:
            missing_wallets += 1

    total_wallet_trades = sum(wallet_counts.values())
    total_wallet_notional = sum(wallet_notional.values())

    def share(values: Sequence[float], total: float, top: int) -> float:
        if total <= 0:
            return 0.0
        return sum(sorted(values, reverse=True)[:top]) / total

    overview: Dict[str, object] = {
        "totalTrades": total_trades,
        "totalSize": total_size,
        "totalNotional": total_notional,
        "averageSize": avg_size,
        "averageNotional": avg_notional,
        "walletCoverage": {
            "uniqueWallets": len(wallet_counts),
            "missingWallets": missing_wallets,
            "missingShare": (missing_wallets / total_trades) if total_trades else 0.0,
        },
        "topWallets": {
            "tradesTop1": share(wallet_counts.values(), total_wallet_trades, 1),
            "tradesTop3": share(wallet_counts.values(), total_wallet_trades, 3),
            "notionalTop1": share(wallet_notional.values(), total_wallet_notional, 1),
            "notionalTop3": share(wallet_notional.values(), total_wallet_notional, 3),
        },
    }

    if largest_by_size:
        overview["largestBySize"] = {
            "size": largest_by_size.size,
            "price": largest_by_size.price,
            "wallet": largest_by_size.proxy_wallet,
            "timestamp": largest_by_size.timestamp,
        }
    if largest_by_notional:
        overview["largestByNotional"] = {
            "notional": largest_by_notional.size * largest_by_notional.price,
            "size": largest_by_notional.size,
            "price": largest_by_notional.price,
            "wallet": largest_by_notional.proxy_wallet,
            "timestamp": largest_by_notional.timestamp,
        }

    return overview


def _outcome_analytics(report: EventScore) -> List[Dict[str, object]]:
    total_notional = sum(trade.size * trade.price for trade in report.trades)
    outcomes: List[Dict[str, object]] = []

    for outcome in report.per_outcome:
        trades = list(outcome.trades)
        trade_count = len(trades)
        notional = sum(t.size * t.price for t in trades)
        total_size = sum(t.size for t in trades)
        vwap = (sum(t.price * t.size for t in trades) / total_size) if total_size else 0.0
        last_price = trades[-1].price if trades else None
        outcomes.append(
            {
                "label": outcome.outcome_label,
                "conditionId": outcome.condition_id,
                "outcomeIndex": outcome.outcome_index,
                "tradeCount": trade_count,
                "notional": notional,
                "volumeShare": (notional / total_notional) if total_notional > 0 else 0.0,
                "vwap": vwap,
                "lastPrice": last_price,
                "score": outcome.score,
                "labelText": outcome.label,
                "heuristics": [
                    {
                        "name": h.name,
                        "triggered": h.triggered,
                        "intensity": h.intensity,
                        "summary": h.summary,
                    }
                    for h in outcome.heuristics
                ],
            }
        )
    return outcomes


def _timeseries(trades: Sequence[Trade]) -> Dict[str, List[Dict[str, object]]]:
    minutes, counts = rolling_minutes(trades)
    vwap_map = vwap_by_minute(trades)
    per_minute: List[Dict[str, object]] = []
    for minute, trade_count in zip(minutes, counts):
        timestamp = minute * 60
        per_minute.append(
            {
                "timestamp": timestamp,
                "iso": unix_to_iso(timestamp),
                "tradeCount": trade_count,
                "vwap": vwap_map.get(minute),
            }
        )
    return {"perMinute": per_minute}


def _summary_from_report(report: EventScore, slug: str, lookback_seconds: int) -> ReportSummary:
    last_trade_ts = report.trades[-1].timestamp if report.trades else None
    summary: ReportSummary = {
        "slug": slug,
        "eventId": report.event.event_id,
        "title": report.event.title,
        "label": report.label,
        "score": report.score,
        "updatedAt": datetime.now(timezone.utc).isoformat(),
        "lookbackSeconds": lookback_seconds,
        "tradeCount": len(report.trades),
        "lastTradeTimestamp": last_trade_ts,
        "topSignals": list(report.rationale),
    }
    summary["outcomes"] = [
        {
            "label": outcome.outcome_label,
            "score": outcome.score,
            "labelText": outcome.label,
        }
        for outcome in report.per_outcome
    ]
    return summary


@dataclass
class ReportEnvelope:
    slug: str
    payload: ReportPayload
    summary: ReportSummary
    trade_count: int
    lookback_seconds: int


class ReportBuilder:
    """Builds per-slug reports without worrying about persistence."""

    def __init__(self, client: Optional[PolymarketClient] = None):
        self.client = client or PolymarketClient()

    def build(
        self,
        slug: str,
        lookback_seconds: int,
        *,
        page_limit: int = 10000,
        max_pages: int = 100,
        sleep_seconds: float = 0.2,
    ) -> ReportEnvelope:
        event = self.client.get_event_by_slug(slug)
        trades, actual_lookback = self.client.fetch_with_fallback(
            event.event_id,
            lookback_seconds=lookback_seconds,
            page_limit=page_limit,
            max_pages=max_pages,
            sleep_seconds=sleep_seconds,
        )
        report = analyze_event(event, trades)
        payload = event_score_to_dict(report, lookback_seconds=actual_lookback)
        payload["analytics"] = {
            "marketOverview": _market_overview(report.trades),
            "outcomes": _outcome_analytics(report),
            "timeseries": _timeseries(report.trades),
        }
        summary = _summary_from_report(report, slug, actual_lookback)
        return ReportEnvelope(
            slug=slug,
            payload=payload,
            summary=summary,
            trade_count=len(report.trades),
            lookback_seconds=actual_lookback,
        )


class ReportStore:
    """Persists report payloads and maintains the search index."""

    def __init__(self, root: Path, index_path: Optional[Path] = None):
        self.root = root
        self.root.mkdir(parents=True, exist_ok=True)
        self.index_path = index_path or (self.root / "index.json")

    def report_path(self, slug: str) -> Path:
        return self.root / f"{slug}.json"

    def read_report(self, slug: str) -> Optional[ReportPayload]:
        path = self.report_path(slug)
        if not path.exists():
            return None
        return json.loads(path.read_text(encoding="utf-8"))

    def write_report(self, slug: str, payload: ReportPayload) -> None:
        path = self.report_path(slug)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(payload, indent=2), encoding="utf-8")

    def read_index(self) -> Dict[str, object]:
        if not self.index_path.exists():
            return {"generatedAt": datetime.now(timezone.utc).isoformat(), "reports": []}
        return json.loads(self.index_path.read_text(encoding="utf-8"))

    def write_index(self, index_payload: Dict[str, object]) -> None:
        self.index_path.parent.mkdir(parents=True, exist_ok=True)
        index_payload["generatedAt"] = datetime.now(timezone.utc).isoformat()
        self.index_path.write_text(json.dumps(index_payload, indent=2), encoding="utf-8")

    def upsert_summary(
        self,
        summary: ReportSummary,
        *,
        refresh_mode: str,
    ) -> None:
        if refresh_mode not in {"scheduled", "on-demand"}:
            raise ValueError("refresh_mode must be 'scheduled' or 'on-demand'")
        index_payload = self.read_index()
        reports: List[ReportSummary] = index_payload.get("reports", [])
        summary_with_mode = dict(summary)
        summary_with_mode["refreshMode"] = refresh_mode
        updated = False
        for idx, existing in enumerate(reports):
            if existing.get("slug") == summary["slug"]:
                reports[idx] = summary_with_mode
                updated = True
                break
        if not updated:
            reports.append(summary_with_mode)
        index_payload["reports"] = reports
        self.write_index(index_payload)

    def list_reports(self) -> List[ReportSummary]:
        payload = self.read_index()
        return payload.get("reports", [])
