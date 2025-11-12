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
Event: Honduras Presidential Election (slug=honduras-presidential-election, id=74717) | Window: last 24.0h | Trades: 182
Overall suspicion score: 42.7 → watch
Rationale: wallet concentration top1=64% trades (45% notional), top3=89%; min-size trades share=82% over 182 trades
Top drivers: wallet concentration..., min-size trades...

By outcome:
- Will Mario Rivera... (Yes) score 71.5 → suspicious trades=104 | wallet concentration..., ping-pong...
```

The JSON file mirrors the same content (`score`, `label`, per-outcome scores, heuristics, `lookbackSeconds`) for downstream ingestion.

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
