from __future__ import annotations

import argparse
import json
import logging
import sys
from pathlib import Path
from typing import Optional

from .api import PolymarketClient
from .scoring import analyze_event
from .utils import parse_lookback
from . import __version__


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="polywatch",
        description="Inspect a Polymarket event for bot-like activity",
    )
    parser.add_argument("--slug", default="honduras-presidential-election", help="Event slug to inspect")
    parser.add_argument("--lookback", default="24h", help="Lookback window (e.g. 12h, 2d)")
    parser.add_argument("--limit", type=int, default=10000, help="Trades page size per API call")
    parser.add_argument("--max-pages", type=int, default=100, help="Maximum number of trade pages to pull")
    parser.add_argument("--sleep", type=float, default=0.2, help="Seconds to sleep between pagination calls")
    parser.add_argument("--json-out", default=None, help="Optional path to write JSON results")
    parser.add_argument("--log-level", default="WARNING", help="Logging level (DEBUG, INFO, ...)")
    parser.add_argument("--version", action="version", version=f"polywatch {__version__}")
    return parser


def label_to_exit_code(label: str) -> int:
    return 2 if label.lower() == "suspicious" else 0


def main(argv: Optional[list[str]] = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    logging.basicConfig(level=getattr(logging, args.log_level.upper(), logging.INFO),
                        format="%(asctime)s %(levelname)s %(name)s: %(message)s")

    try:
        lookback_seconds = parse_lookback(args.lookback)
    except ValueError as exc:
        parser.error(str(exc))
        return 3

    client = PolymarketClient()

    try:
        event = client.get_event_by_slug(args.slug)
        trades, actual_lookback = client.fetch_with_fallback(
            event.event_id,
            lookback_seconds=lookback_seconds,
            page_limit=args.limit,
            max_pages=args.max_pages,
            sleep_seconds=args.sleep,
        )
    except Exception as exc:  # noqa: BLE001 - CLI needs friendly errors
        logging.error("Failed to fetch data: %s", exc)
        return 3

    if not trades:
        window_hours = actual_lookback / 3600
        print(f"No trades found in the last {window_hours:.1f}h.")
        return 0

    report = analyze_event(event, trades)

    from .render import event_score_to_dict, render_text_report  # late import to avoid cycles

    print(render_text_report(report, actual_lookback))

    if args.json_out:
        path = Path(args.json_out)
        path.parent.mkdir(parents=True, exist_ok=True)
        payload = event_score_to_dict(report, lookback_seconds=actual_lookback)
        path.write_text(json.dumps(payload, indent=2))
        logging.info("Wrote JSON report to %s", path)

    return label_to_exit_code(report.label)


if __name__ == "__main__":  # pragma: no cover
    sys.exit(main())
