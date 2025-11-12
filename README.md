# Polywatch CLI

Polywatch is a dependency-light command-line tool that inspects individual Polymarket events for bot-like or inorganic trading behavior. It pulls trades from the public `gamma` and `data` APIs, runs a suite of heuristics, and produces both human-readable and machine-friendly summaries so you can monitor specific markets or wire the tool into automation.

## Requirements

- Python 3.9+ with `venv`
- Network access to `https://gamma-api.polymarket.com` and `https://data-api.polymarket.com`

## Installation

```bash
python3 -m venv .venv
source .venv/bin/activate        # On Windows use .venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
```

## Running the Analyzer

```bash
python -m polywatch.cli \
  --slug honduras-presidential-election \
  --lookback 24h \
  --json-out reports/honduras.json \
  --log-level INFO
```

## Exporting Cached Reports

The frontend consumes cached JSON built with the exporter script. Generate snapshots for one or more slugs:

```bash
python scripts/export_report.py \
  --slug honduras-presidential-election \
  --lookback 24h \
  --output-dir docs/reports \
  --index-file docs/reports/index.json
```

The exporter reuses the CLI’s client, honours the same rate-limit defaults (5k rows/page, 0.3 s sleep) and writes both `docs/reports/<slug>.json` and a searchable `docs/reports/index.json`. Add additional `--slug` flags to snapshot multiple markets in one run.

A GitHub Actions workflow (`.github/workflows/export-reports.yml`) refreshes these files every 15 minutes and pushes them to a `reports` branch. Adjust `POLYWATCH_SLUGS`, `POLYWATCH_LOOKBACK`, or the sleep/page parameters in the workflow environment to widen coverage without breaking Polymarket’s 75 req/10 s budget.

## Cyberpunk Web Frontend

The cyberpunk dashboard lives in `frontend/` (Next.js 15 App Router + Tailwind). It renders the cached reports with hero cards, market overview tiles, outcome tables, sparklines, and a fuzzy search launcher.

```bash
cd frontend
npm install
REPORTS_FILE_ROOT=../docs/reports npm run dev
```

- `REPORTS_FILE_ROOT` (default: `../docs/reports`) points the server to local JSON. In production, set `REPORTS_BASE_URL` (and `NEXT_PUBLIC_REPORTS_BASE_URL` for client-side fetches) to the hosted snapshots, e.g. a `reports` branch served over GitHub Pages.
- `npm run build` performs an ISR-ready production build, `npm run start` serves it.
- `npm run test:e2e` executes Playwright smoke tests against the dashboard, verifying the featured report renders and the search flow drills into `/markets/[slug]`.

### Key Flags

| Flag | Description |
| --- | --- |
| `--slug` | Polymarket event slug to inspect (defaults to `honduras-presidential-election`). |
| `--lookback` | Desired window (e.g., `12h`, `2d`, `90m`). If no trades exist, the client widens the window (up to 72h by default) and the report reflects the actual span. |
| `--limit` / `--max-pages` | Trade pagination limits; default to 5k rows per page and 100 pages. |
| `--sleep` | Delay between `/trades` requests (seconds). Helpful when rate limits tighten. |
| `--json-out` | Optional path for structured output; parent directories are created automatically. |
| `--log-level` | Python logging verbosity (`DEBUG`, `INFO`, …). |

Exit codes follow the spec: `0` for normal/watch, `2` for suspicious, `3` for configuration or data-fetch errors. This allows simple cron or CI alerting.

### Sample Output

```
Event: Honduras Presidential Election (slug=honduras-presidential-election, id=74717)
Window: last 24.0h | Trades evaluated: 58 | Score: 4.9 → normal
Top signals: min-size trades share=50% over 58 trades; wallet concentration top1=9% trades (22% notional), top3=22%

Market Overview
+--------------------------+--------------------------------------------------------------+
| Metric                   | Value                                                        |
+--------------------------+--------------------------------------------------------------+
| Total trades             | 58                                                           |
| Average trade size       | 73.28 shares                                                 |
| Largest trade (shares)   | 658.77 by 0x58b9… @ 39.8%                                    |
| Top wallet (notional)    | 21.9%                                                        |
| Top 3 wallets (notional) | 47.1%                                                        |
+--------------------------+--------------------------------------------------------------+

Outcome Snapshot
+------------------------------------------------------+--------+----------+--------------+-------+------------+---------------+
| Outcome                                              | Trades | Notional | Volume Share | VWAP  | Last Price | Suspicion     |
+------------------------------------------------------+--------+----------+--------------+-------+------------+---------------+
| Will Rixi Moncada win the 2025 Honduras election? No | 12     | $791.98  | 42.9%        | 39.1% | 39.5%      | 3.5 (normal)  |
| ...                                                  | ...    | ...      | ...          | ...   | ...        | ...           |
+------------------------------------------------------+--------+----------+--------------+-------+------------+---------------+

Suspicion Indicators
+----------------------+--------+-----------+--------------------------------------------------------------+
| Indicator            | Status | Intensity | Details                                                      |
+----------------------+--------+-----------+--------------------------------------------------------------+
| Wallet Concentration | clear  | 0.22      | wallet concentration top1=9% trades (22% notional), top3=22% |
| ...                  | ...    | ...       | ...                                                          |
+----------------------+--------+-----------+--------------------------------------------------------------+
```

The JSON file mirrors the same content (`score`, `label`, per-outcome scores, heuristics, `lookbackSeconds`) for downstream ingestion, while the terminal report now doubles as a market-health snapshot (totals, averages, VWAP/last trade per outcome, wallet coverage, etc.).

### Report Sections

- **Market Overview** – headline counts, notional totals, averages, largest trade callouts, and wallet concentration metrics (unique wallets, missing metadata share, top wallet dominance).
- **Outcome Snapshot** – per-contract trade counts, notional volume share, VWAP, last price, and localized suspicion score so you can see which legs drive activity.
- **Suspicion Indicators** – tabular rendering of every heuristic with trigger state, intensity, and wrapped summaries for quick scanning.

## Heuristics & Scoring

Each heuristic returns a trigger flag, intensity, and summary, and the weighted combination yields an overall 0–100 score:

- **Wallet concentration** – share of trades/notional dominated by a few wallets (missing wallets are ignored but counted in the summary).
- **Min-size spam** – prevalence of prints at or near the market’s minimum order size.
- **Timing regularity** – low coefficient of variation with statistically abnormal bursts.
- **Ping-pong sequences** – rapid alternating buys/sells within 60 seconds.
- **Round trips** – quick reversals within 10 minutes with ≤1 tick price drift.
- **Price whips** – per-outcome price spikes ≥5 points that revert ≥80% within 5 minutes.

Event-level scores drive the exit code; per-outcome scores help pinpoint specific contracts.

## Testing

Run the full suite before committing changes:

```bash
python -m pytest -q
```

Tests cover heuristics, API fallbacks, scoring immutability, and CLI exit semantics. Add new unit cases in `tests/test_<module>.py` when you tweak heuristics or client behavior.

## Raw-Data Spot Checks

When in doubt, inspect the trades directly:

```bash
python - <<'PY'
from polywatch.api import PolymarketClient
from polywatch.utils import unix_to_iso

client = PolymarketClient()
event = client.get_event_by_slug("honduras-presidential-election")
trades, window = client.fetch_with_fallback(event.event_id, lookback_seconds=6*3600)
print(f"{len(trades)} trades over {window/3600:.1f}h")
for trade in trades[:10]:
    print(unix_to_iso(trade.timestamp), trade.proxy_wallet, trade.side, trade.price, trade.size)
PY
```

This uses the same client and retry logic as the CLI, making it easy to gut-check inputs or craft fixture data.

## Troubleshooting

- **Missing virtualenv**: create it with `python3 -m venv .venv` before attempting `source .venv/bin/activate`.
- **Rate limits / 429s**: increase `--sleep`, lower `--limit`, or override `PolymarketClient` defaults in code.
- **Empty report**: the tool widens the lookback automatically; if you still see “No trades found,” extend `--lookback` or confirm the event is active.
- **Automation hooks**: watch for exit code `2` and parse the JSON artifact for structured signals.

For deeper implementation details or contributor guidance, see `AGENTS.md` and `development-spec.md`.
