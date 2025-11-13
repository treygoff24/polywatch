#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import List, Tuple

from polywatch.api import PolymarketClient
from polywatch.models import Trade
from polywatch.render import event_score_to_dict, render_text_report
from polywatch.scoring import analyze_event


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Run the Polywatch analyzer against a saved trades dump.",
    )
    parser.add_argument(
        "--trades-file",
        type=Path,
        default=Path("honduras-24h-trades.json"),
        help="Path to a JSON file with trades (defaults to honduras-24h-trades.json).",
    )
    parser.add_argument(
        "--json-out",
        type=Path,
        help="Optional path for the structured report output.",
    )
    return parser.parse_args()


def _load_trades(path: Path) -> Tuple[str, List[Trade], int]:
    payload = json.loads(path.read_text())
    event_payload = payload.get("event") or {}
    slug = event_payload.get("slug")
    if not slug:
        raise SystemExit("Trades file is missing event.slug metadata.")

    trades_raw = payload.get("trades") or []
    if not trades_raw:
        raise SystemExit("Trades file contains no trades.")

    trades: List[Trade] = []
    for raw in trades_raw:
        outcome_index = raw.get("outcomeIndex")
        if outcome_index is not None:
            try:
                outcome_index = int(outcome_index)
            except (TypeError, ValueError):
                outcome_index = None
        proxy_wallet = raw.get("proxyWallet")
        if isinstance(proxy_wallet, str):
            proxy_wallet = proxy_wallet.strip().lower() or None
        else:
            proxy_wallet = None
        trades.append(
            Trade(
                timestamp=int(raw["timestamp"]),
                proxy_wallet=proxy_wallet,
                side=(raw.get("side") or "BUY").upper(),
                condition_id=raw.get("conditionId") or "",
                outcome_index=outcome_index,
                outcome=raw.get("outcome"),
                size=float(raw.get("size") or 0.0),
                price=float(raw.get("price") or 0.0),
                tx_hash=raw.get("txHash"),
            )
        )
    trades.sort(key=lambda trade: trade.timestamp)

    lookback = payload.get("lookbackSeconds")
    if lookback is None:
        lookback = trades[-1].timestamp - trades[0].timestamp if len(trades) > 1 else 0

    return slug, trades, int(lookback)


def main() -> int:
    args = _parse_args()
    slug, trades, lookback_seconds = _load_trades(args.trades_file)

    client = PolymarketClient()
    event = client.get_event_by_slug(slug)
    report = analyze_event(event, trades)

    print(render_text_report(report, lookback_seconds))

    if args.json_out:
        args.json_out.parent.mkdir(parents=True, exist_ok=True)
        payload = event_score_to_dict(report, lookback_seconds)
        args.json_out.write_text(json.dumps(payload, indent=2))

    return 0


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
