from __future__ import annotations

from typing import Dict, List, Optional

from .models import EventScore, HeuristicResult, OutcomeScore


def _summarize_top_drivers(heuristics: List[HeuristicResult], limit: int = 4) -> str:
    top = sorted(heuristics, key=lambda h: (int(h.triggered), h.intensity), reverse=True)
    drivers = [h.summary for h in top if h.triggered]
    return ", ".join(drivers[:limit])


def render_text_report(report: EventScore, lookback_seconds: int) -> str:
    hours = lookback_seconds / 3600
    total_trades = len(report.trades)
    lines = []
    lines.append(
        f"Event: {report.event.title} (slug={report.event.slug}, id={report.event.event_id}) | "
        f"Window: last {hours:.1f}h | Trades: {total_trades}"
    )
    lines.append(
        f"Overall suspicion score: {report.score:.1f} → {report.label}"
    )
    if report.rationale:
        lines.append("Rationale: " + "; ".join(report.rationale))
    top_drivers = _summarize_top_drivers(report.heuristics)
    lines.append(f"Top drivers: {top_drivers or 'None'}")
    lines.append("")
    lines.append("By outcome:")
    for outcome in report.per_outcome:
        line = (
            f"- {outcome.outcome_label:<25} score {outcome.score:>5.1f} → {outcome.label:<10} "
            f"trades={len(outcome.trades):4d}"
        )
        drivers = _summarize_top_drivers(outcome.heuristics)
        if drivers:
            line += f" | {drivers}"
        lines.append(line)
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
