#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import logging
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, Iterable, List, Optional, Sequence

from polywatch.api import PolymarketClient
from polywatch.models import EventScore, Trade
from polywatch.render import event_score_to_dict
from polywatch.scoring import analyze_event
from polywatch.utils import (
    parse_lookback,
    rolling_minutes,
    unix_to_iso,
    vwap_by_minute,
)


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Export Polywatch reports to JSON files plus a search index",
    )
    parser.add_argument(
        "--slug",
        action="append",
        dest="slugs",
        help="Event slug to export (repeat for multiple). Defaults to honduras-presidential-election.",
    )
    parser.add_argument(
        "--lookback",
        default="24h",
        help="Lookback window (e.g. 12h, 2d) used for trade fetching.",
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=5000,
        help="Trades page size per API call (max 5000).",
    )
    parser.add_argument(
        "--max-pages",
        type=int,
        default=50,
        help="Maximum number of pages to pull per slug.",
    )
    parser.add_argument(
        "--sleep",
        type=float,
        default=0.3,
        help="Seconds to sleep between paginated API calls.",
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=Path("docs/reports"),
        help="Directory where per-slug JSON reports are written.",
    )
    parser.add_argument(
        "--index-file",
        type=Path,
        default=Path("docs/reports/index.json"),
        help="Path for the search index file.",
    )
    parser.add_argument(
        "--log-level",
        default="INFO",
        help="Logging level to use (DEBUG, INFO, ...).",
    )
    return parser.parse_args()


def _ensure_output_paths(output_dir: Path, index_file: Path) -> None:
    output_dir.mkdir(parents=True, exist_ok=True)
    index_file.parent.mkdir(parents=True, exist_ok=True)


def _market_overview(trades: Sequence[Trade]) -> Dict[str, object]:
    total_trades = len(trades)
    total_size = sum(trade.size for trade in trades)
    total_notional = sum(trade.size * trade.price for trade in trades)
    avg_size = total_size / total_trades if total_trades else 0.0
    avg_notional = total_notional / total_trades if total_trades else 0.0
    largest_by_size = max(trades, key=lambda t: t.size, default=None)
    largest_by_notional = max(trades, key=lambda t: t.size * t.price, default=None)

    wallet_counts: Counter[str] = Counter()
    wallet_notional: Dict[str, float] = defaultdict(float)
    missing_wallets = 0
    for trade in trades:
        wallet = trade.proxy_wallet
        if wallet:
            wallet_counts[wallet] += 1
            wallet_notional[wallet] += trade.size * trade.price
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


def _export_slug(
    client: PolymarketClient,
    slug: str,
    lookback_seconds: int,
    page_limit: int,
    max_pages: int,
    sleep_seconds: float,
    output_dir: Path,
) -> Optional[Dict[str, object]]:
    event = client.get_event_by_slug(slug)
    trades, actual_lookback = client.fetch_with_fallback(
        event.event_id,
        lookback_seconds=lookback_seconds,
        page_limit=page_limit,
        max_pages=max_pages,
        sleep_seconds=sleep_seconds,
    )

    # Always analyse even if the trade list is empty to keep downstream JSON deterministic.
    report = analyze_event(event, trades)
    payload = event_score_to_dict(report, lookback_seconds=actual_lookback)

    payload["analytics"] = {
        "marketOverview": _market_overview(report.trades),
        "outcomes": _outcome_analytics(report),
        "timeseries": _timeseries(report.trades),
    }

    output_path = output_dir / f"{slug}.json"
    output_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    logging.info("Wrote %s (%d trades)", output_path, len(report.trades))

    last_trade_ts = report.trades[-1].timestamp if report.trades else None
    summary: Dict[str, object] = {
        "slug": slug,
        "eventId": event.event_id,
        "title": event.title,
        "label": report.label,
        "score": report.score,
        "updatedAt": datetime.now(timezone.utc).isoformat(),
        "lookbackSeconds": actual_lookback,
        "tradeCount": len(report.trades),
        "lastTradeTimestamp": last_trade_ts,
        "topSignals": list(report.rationale),
    }

    condensed_outcomes = [
        {
            "label": outcome.outcome_label,
            "score": outcome.score,
            "labelText": outcome.label,
        }
        for outcome in report.per_outcome
    ]
    summary["outcomes"] = condensed_outcomes

    return summary


def _write_index(index_file: Path, entries: Iterable[Dict[str, object]]) -> None:
    index_payload = {
        "generatedAt": datetime.now(timezone.utc).isoformat(),
        "reports": list(entries),
    }
    index_file.write_text(json.dumps(index_payload, indent=2), encoding="utf-8")
    logging.info("Wrote index %s", index_file)


def main() -> int:
    args = _parse_args()
    slugs = args.slugs or ["honduras-presidential-election"]

    try:
        lookback_seconds = parse_lookback(args.lookback)
    except ValueError as exc:
        logging.getLogger(__name__).error("Invalid lookback: %s", exc)
        return 2

    logging.basicConfig(
        level=getattr(logging, args.log_level.upper(), logging.INFO),
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    )

    _ensure_output_paths(args.output_dir, args.index_file)

    client = PolymarketClient()
    summaries: List[Dict[str, object]] = []

    for slug in slugs:
        try:
            summary = _export_slug(
                client=client,
                slug=slug,
                lookback_seconds=lookback_seconds,
                page_limit=args.limit,
                max_pages=args.max_pages,
                sleep_seconds=args.sleep,
                output_dir=args.output_dir,
            )
        except Exception as exc:  # noqa: BLE001 - exporter should log and continue
            logging.error("Failed to export %s: %s", slug, exc)
            continue
        if summary is not None:
            summaries.append(summary)

    if summaries:
        _write_index(args.index_file, summaries)
    else:
        logging.warning("No reports were exported; index not written.")

    return 0


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())

