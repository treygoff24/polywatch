#!/usr/bin/env python3
from __future__ import annotations

import argparse
import logging
from pathlib import Path
from typing import Dict, List, Optional

import sys

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from polywatch.api import PolymarketClient
from polywatch.reporting import ReportBuilder, ReportStore
from polywatch.utils import parse_lookback


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


def _export_slug(
    builder: ReportBuilder,
    store: ReportStore,
    slug: str,
    lookback_seconds: int,
    page_limit: int,
    max_pages: int,
    sleep_seconds: float,
) -> Optional[Dict[str, object]]:
    envelope = builder.build(
        slug,
        lookback_seconds=lookback_seconds,
        page_limit=page_limit,
        max_pages=max_pages,
        sleep_seconds=sleep_seconds,
    )
    store.write_report(slug, envelope.payload)
    store.upsert_summary(envelope.summary, refresh_mode="scheduled")
    summary_with_mode = dict(envelope.summary)
    summary_with_mode["refreshMode"] = "scheduled"
    logging.info(
        "Exported %s (%d trades, lookback %.1fh)",
        slug,
        envelope.trade_count,
        envelope.lookback_seconds / 3600,
    )
    return summary_with_mode


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
    builder = ReportBuilder(client=client)
    store = ReportStore(args.output_dir, index_path=args.index_file)

    summaries: List[Dict[str, object]] = []
    for slug in slugs:
        try:
            summary = _export_slug(
                builder=builder,
                store=store,
                slug=slug,
                lookback_seconds=lookback_seconds,
                page_limit=args.limit,
                max_pages=args.max_pages,
                sleep_seconds=args.sleep,
            )
        except Exception as exc:  # noqa: BLE001 - exporter should log and continue
            logging.error("Failed to export %s: %s", slug, exc)
            continue
        if summary is not None:
            summaries.append(summary)

    store.write_index({"reports": summaries})
    if not summaries:
        logging.warning(
            "No reports were exported; the index is now empty to avoid stale entries."
        )

    return 0


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
