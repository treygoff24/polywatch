from __future__ import annotations

from typing import Callable, Dict, List, Optional, Sequence, Tuple

from . import heuristics
from .models import EventMeta, EventScore, HeuristicResult, OutcomeMeta, OutcomeScore, Trade
from .utils import group_trades_by_outcome

HEURISTIC_WEIGHTS = {
    "wallet_concentration": 0.25,
    "min_size_spam": 0.20,
    "timing_regular": 0.20,
    "ping_pong": 0.15,
    "round_trips": 0.10,
    "price_whips": 0.10,
}


def label_for_score(score: float) -> str:
    if score >= 60:
        return "suspicious"
    if score >= 35:
        return "watch"
    return "normal"


def _component_value(result: HeuristicResult) -> float:
    base = 1.0 if result.triggered else 0.0
    return 0.7 * base + 0.3 * max(0.0, min(1.0, result.intensity))


def _compute_score(results: List[HeuristicResult]) -> float:
    total = 0.0
    for result in results:
        weight = HEURISTIC_WEIGHTS.get(result.name, 0.0)
        total += weight * _component_value(result)
    return total * 100.0


def _build_meta_lookup(event: EventMeta) -> Dict[Tuple[str, Optional[int]], OutcomeMeta]:
    lookup: Dict[Tuple[str, Optional[int]], OutcomeMeta] = {}
    for condition_id, market in event.markets.items():
        if market.outcomes:
            for idx, _ in enumerate(market.outcomes):
                lookup[(condition_id, idx)] = event.outcome_meta(condition_id, idx)
        lookup[(condition_id, None)] = event.outcome_meta(condition_id, None)
    return lookup


def _order_lookup_factory(meta_lookup: Dict[Tuple[str, Optional[int]], OutcomeMeta]) -> Callable[[Trade], float]:
    def lookup(trade: Trade) -> float:
        meta = meta_lookup.get((trade.condition_id, trade.outcome_index))
        if not meta:
            meta = meta_lookup.get((trade.condition_id, None))
        return meta.order_min_size if meta else 0.0

    return lookup


def _tick_lookup_factory(meta_lookup: Dict[Tuple[str, Optional[int]], OutcomeMeta]) -> Callable[[Trade], float]:
    def lookup(trade: Trade) -> float:
        meta = meta_lookup.get((trade.condition_id, trade.outcome_index))
        if not meta:
            meta = meta_lookup.get((trade.condition_id, None))
        return meta.tick_size if meta else 0.01

    return lookup


def _outcome_label(
    condition_id: str,
    outcome_index: Optional[int],
    meta_lookup: Dict[Tuple[str, Optional[int]], OutcomeMeta],
) -> str:
    meta = meta_lookup.get((condition_id, outcome_index))
    if not meta:
        meta = meta_lookup.get((condition_id, None))
    if meta:
        base = meta.market_question
        if meta.outcome:
            return f"{base} ({meta.outcome})"
        return base
    if outcome_index is None:
        return condition_id
    return f"{condition_id}#{outcome_index}"


def _evaluate(trades: Sequence[Trade], order_lookup: Callable[[Trade], float], tick_lookup: Callable[[Trade], float]) -> List[HeuristicResult]:
    return [
        heuristics.wallet_concentration(trades),
        heuristics.min_size_spam(trades, order_lookup),
        heuristics.timing_regularity(trades),
        heuristics.ping_pong_sequences(trades),
        heuristics.round_trips(trades, tick_lookup),
        heuristics.price_whips(trades),
    ]


def analyze_event(event: EventMeta, trades: Sequence[Trade]) -> EventScore:
    meta_lookup = _build_meta_lookup(event)

    order_lookup = _order_lookup_factory(meta_lookup)
    tick_lookup = _tick_lookup_factory(meta_lookup)

    # Enrich trade outcome labels for reporting consistency
    for trade in trades:
        label = _outcome_label(trade.condition_id, trade.outcome_index, meta_lookup)
        if trade.outcome is None:
            trade.outcome = label

    event_results = _evaluate(trades, order_lookup, tick_lookup)
    event_score_value = _compute_score(event_results)
    event_label = label_for_score(event_score_value)
    rationale = [res.summary for res in event_results if res.triggered][:4]
    if not rationale:
        rationale = [res.summary for res in sorted(event_results, key=lambda r: r.intensity, reverse=True)[:2]]

    grouped = group_trades_by_outcome(trades)
    outcome_scores: List[OutcomeScore] = []
    for (condition_id, outcome_index), outcome_trades in grouped.items():
        meta = meta_lookup.get((condition_id, outcome_index)) or meta_lookup.get((condition_id, None))
        order_lookup_fn = heuristics.constant_lookup(meta.order_min_size if meta else 0.0)
        tick_lookup_fn = heuristics.constant_lookup((meta.tick_size if meta else 0.01) or 0.01)
        results = _evaluate(outcome_trades, order_lookup_fn, tick_lookup_fn)
        score_value = _compute_score(results)
        label = label_for_score(score_value)
        outcome_scores.append(
            OutcomeScore(
                outcome_label=_outcome_label(condition_id, outcome_index, meta_lookup),
                condition_id=condition_id,
                outcome_index=outcome_index,
                trades=tuple(outcome_trades),
                heuristics=results,
                score=score_value,
                label=label,
            )
        )

    outcome_scores.sort(key=lambda o: o.score, reverse=True)

    return EventScore(
        event=event,
        trades=tuple(trades),
        heuristics=event_results,
        score=event_score_value,
        label=event_label,
        rationale=rationale,
        per_outcome=outcome_scores,
    )
