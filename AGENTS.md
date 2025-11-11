# Repository Guidelines

## Project Structure & Module Organization
- `polywatch/` houses the CLI: `api.py` handles HTTP, `models.py` stores dataclasses, `heuristics.py`/`scoring.py` compute scores, `render.py` formats output, and `cli.py` orchestrates them.
- `tests/` mirrors core modules with deterministic unittest suites (`test_utils.py`, `test_heuristics.py`).
- `development-spec.md` is the canonical design document—consult it before touching heuristics or API thresholds.
- `docs/` is empty now; add narrative guides or sanitized sample reports there.

## Build, Test, and Development Commands
- `python -m venv .venv && source .venv/bin/activate && pip install -r requirements.txt` installs the lone dependency (`requests`).
- `python -m polywatch.cli --slug honduras-presidential-election --lookback 24h --json-out report.json` runs the analyzer locally and produces both console and JSON output.
- `python -m polywatch.cli --help` surfaces pagination, logging, and exit-code knobs—update the help text when introducing new flags.
- `pytest -q` runs the full suite; `python -m unittest discover tests` is an equivalent fallback.

## Coding Style & Naming Conventions
- Stick to PEP 8 with four-space indentation, keep the existing type hints, and favor short, pure helpers inside `heuristics.py` and `utils.py`.
- Use snake_case for functions and variables, PascalCase for dataclasses, and kebab-case for CLI flags to stay aligned with `argparse`.
- Route diagnostics through the logger configured in `cli.py`; user-facing text belongs in `render.py`.
- Keep docstrings concise and reserve inline comments for non-obvious heuristics or API quirks.

## Testing Guidelines
- Reuse `tests/test_heuristics.py::make_trade` to craft repeatable trade streams for new checks.
- Place new cases under `tests/test_<module>.py`, name classes `<Module>Test`, and assert both trigger and non-trigger paths.
- Target ≥90% branch coverage for fresh heuristics; `pytest -q -k heuristics` helps iterate quickly.

## Commit & Pull Request Guidelines
- With no bundled Git history, adopt imperative `area: action` commit subjects (e.g., `heuristics: relax timing variance`).
- PRs should link to issues, describe data sources touched, paste representative CLI or JSON output, and note any rate-limit implications.
- Keep commits narrowly scoped and call out automation impacts when exit codes, CLI defaults, or log formats change.

## Security & Configuration Tips
- Current Polymarket endpoints are public; if you add secrets, load them from environment variables and document the names.
- Respect `/trades` rate limits from `development-spec.md` by tuning `--sleep` or pagination arguments in `PolymarketClient.fetch_with_fallback`.
- Store JSON artifacts from `--json-out` inside the repo (root or `docs/`) and avoid checking in real customer data.
