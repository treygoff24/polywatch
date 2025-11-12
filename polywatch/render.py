from __future__ import annotations

import textwrap
from collections import Counter, defaultdict
from typing import Dict, List, Optional, Sequence

from .models import EventScore, HeuristicResult, OutcomeScore, Trade


def _format_table(headers: Sequence[str], rows: Sequence[Sequence[str]]) -> str:
    if not rows:
        return ""
    normalized = []
    widths = [len(header) for header in headers]
    for row in rows:
        cells = []
        for idx, cell in enumerate(row):
            text = str(cell)
            lines = text.splitlines() or [""]
            widths[idx] = max(widths[idx], max(len(line) for line in lines))
            cells.append(lines)
        normalized.append(cells)
    header_line = "| " + " | ".join(header.ljust(widths[idx]) for idx, header in enumerate(headers)) + " |"
    divider = "+" + "+".join("-" * (width + 2) for width in widths) + "+"

    def _render_row(row_cells: Sequence[List[str]]) -> List[str]:
        height = max(len(cell) for cell in row_cells)
        rendered_lines = []
        for line_idx in range(height):
            pieces = []
            for col_idx, lines in enumerate(row_cells):
                value = lines[line_idx] if line_idx < len(lines) else ""
                pieces.append(value.ljust(widths[col_idx]))
            rendered_lines.append("| " + " | ".join(pieces) + " |")
        return rendered_lines

    lines = [divider, header_line, divider]
    for row_cells in normalized:
        lines.extend(_render_row(row_cells))
        lines.append(divider)
    return "\n".join(lines)


def _format_percent(value: float, digits: int = 0) -> str:
    return f"{value * 100:.{digits}f}%"


def _format_currency(value: float) -> str:
    return f"${value:,.2f}"


def _wrap(text: str, width: int = 68) -> str:
    return textwrap.fill(text, width=width)


def _wallet_distribution(trades: Sequence[Trade]) -> Dict[str, float]:
    counts: Counter[str] = Counter()
    notionals: Dict[str, float] = defaultdict(float)
    for trade in trades:
        if not trade.proxy_wallet:
            continue
        counts[trade.proxy_wallet] += 1
        notionals[trade.proxy_wallet] += trade.size * trade.price
    total_trades = sum(counts.values())
    total_notional = sum(notionals.values())

    def share(values: Dict[str, float], total: float, top: int) -> float:
        if total <= 0:
            return 0.0
        top_values = sorted(values.values(), reverse=True)[:top]
        return sum(top_values) / total if top_values else 0.0

    return {
        "top1_trades": share(counts, total_trades, 1),
        "top3_trades": share(counts, total_trades, 3),
        "top1_notional": share(notionals, total_notional, 1),
        "top3_notional": share(notionals, total_notional, 3),
        "unique_wallets": len(counts),
    }


def _market_overview_rows(trades: Sequence[Trade]) -> List[List[str]]:
    total_trades = len(trades)
    total_size = sum(trade.size for trade in trades)
    total_notional = sum(trade.size * trade.price for trade in trades)
    avg_size = total_size / total_trades if total_trades else 0.0
    avg_notional = total_notional / total_trades if total_trades else 0.0
    largest_by_size = max(trades, key=lambda t: t.size, default=None)
    largest_by_notional = max(trades, key=lambda t: t.size * t.price, default=None)
    missing_wallets = sum(1 for trade in trades if not trade.proxy_wallet)
    dist = _wallet_distribution(trades)
    rows = [
        ["Total trades", f"{total_trades:,}"],
        ["Total size (shares)", f"{total_size:,.2f}"],
        ["Total notional (USDC)", _format_currency(total_notional)],
        ["Average trade size", f"{avg_size:,.2f} shares"],
        ["Average notional", _format_currency(avg_notional)],
    ]
    if largest_by_size:
        rows.append(
            [
                "Largest trade (shares)",
                f"{largest_by_size.size:,.2f} by {largest_by_size.proxy_wallet or 'unknown'} "
                f"@ {largest_by_size.price*100:.1f}%",
            ]
        )
    if largest_by_notional:
        rows.append(
            [
                "Largest trade (USDC)",
                f"{_format_currency(largest_by_notional.size * largest_by_notional.price)} by "
                f"{largest_by_notional.proxy_wallet or 'unknown'}",
            ]
        )
    if total_trades:
        missing_share = missing_wallets / total_trades
        rows.append(
            [
                "Wallet coverage",
                f"{dist['unique_wallets']:,} wallets | missing {_format_percent(missing_share, 1)}",
            ]
        )
    rows.extend(
        [
            ["Top wallet (trades)", _format_percent(dist["top1_trades"], 1)],
            ["Top 3 wallets (trades)", _format_percent(dist["top3_trades"], 1)],
            ["Top wallet (notional)", _format_percent(dist["top1_notional"], 1)],
            ["Top 3 wallets (notional)", _format_percent(dist["top3_notional"], 1)],
        ]
    )
    return rows


def _outcome_rows(report: EventScore) -> List[List[str]]:
    total_notional = sum(trade.size * trade.price for trade in report.trades) or 1.0
    rows: List[List[str]] = []
    for outcome in report.per_outcome:
        trades = list(outcome.trades)
        trade_count = len(trades)
        notional = sum(t.size * t.price for t in trades)
        total_size = sum(t.size for t in trades)
        vwap = (sum(t.price * t.size for t in trades) / total_size) if total_size else 0.0
        last_price = trades[-1].price if trades else 0.0
        rows.append(
            [
                outcome.outcome_label,
                f"{trade_count:,}",
                _format_currency(notional),
                _format_percent(notional / total_notional, 1),
                _format_percent(vwap, 1),
                _format_percent(last_price, 1),
                f"{outcome.score:.1f} ({outcome.label})",
            ]
        )
    return rows


def _indicator_rows(results: Sequence[HeuristicResult]) -> List[List[str]]:
    rows: List[List[str]] = []
    for heuristic in results:
        status = "TRIGGERED" if heuristic.triggered else "clear"
        rows.append(
            [
                heuristic.name.replace("_", " ").title(),
                status,
                f"{heuristic.intensity:.2f}",
                _wrap(heuristic.summary),
            ]
        )
    return rows


def render_text_report(report: EventScore, lookback_seconds: int) -> str:
    hours = lookback_seconds / 3600
    lines = []
    lines.append(
        f"Event: {report.event.title} (slug={report.event.slug}, id={report.event.event_id})"
    )
    lines.append(
        f"Window: last {hours:.1f}h | Trades evaluated: {len(report.trades):,} | "
        f"Score: {report.score:.1f} → {report.label}"
    )
    if report.rationale:
        lines.append("Top signals: " + "; ".join(report.rationale))
    lines.append("")
    lines.append("Market Overview")
    lines.append(_format_table(["Metric", "Value"], _market_overview_rows(report.trades)))
    lines.append("")
    lines.append("Outcome Snapshot")
    outcome_rows = _outcome_rows(report)
    if outcome_rows:
        lines.append(
            _format_table(
                ["Outcome", "Trades", "Notional", "Volume Share", "VWAP", "Last Price", "Suspicion"],
                outcome_rows,
            )
        )
    else:
        lines.append("No outcome-level activity recorded.")
    lines.append("")
    lines.append("Suspicion Indicators")
    indicator_rows = _indicator_rows(report.heuristics)
    if indicator_rows:
        lines.append(
            _format_table(
                ["Indicator", "Status", "Intensity", "Details"],
                indicator_rows,
            )
        )
    else:
        lines.append("No heuristics evaluated.")
    return "\n".join(lines)


def heuristic_to_dict(heuristic: HeuristicResult) -> Dict[str, object]:
    return {
        "name": heuristic.name,
        "triggered": heuristic.triggered,
        "intensity": heuristic.intensity,
        "summary": heuristic.summary,
    }


def event_score_to_dict(report: EventScore, lookback_seconds: Optional[int] = None) -> Dict[str, object]:
    data: Dict[str, object] = {
        "event": {
            "title": report.event.title,
            "slug": report.event.slug,
            "id": report.event.event_id,
        },
        "score": report.score,
        "label": report.label,
        "heuristics": [heuristic_to_dict(h) for h in report.heuristics],
        "outcomes": [
            {
                "label": outcome.outcome_label,
                "conditionId": outcome.condition_id,
                "outcomeIndex": outcome.outcome_index,
                "score": outcome.score,
                "labelText": outcome.label,
                "heuristics": [heuristic_to_dict(h) for h in outcome.heuristics],
            }
            for outcome in report.per_outcome
        ],
    }
    if lookback_seconds is not None:
        data["lookbackSeconds"] = lookback_seconds
    return data
