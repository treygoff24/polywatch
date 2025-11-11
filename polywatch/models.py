from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, List, Optional, Sequence


@dataclass
class MarketMeta:
    condition_id: str
    question: str
    order_min_size: float
    tick_size: float
    outcomes: List[str]
    slug: Optional[str] = None

    def outcome_name(self, index: Optional[int]) -> Optional[str]:
        if index is None:
            return None
        if 0 <= index < len(self.outcomes):
            return self.outcomes[index]
        return None


@dataclass
class OutcomeMeta:
    condition_id: str
    outcome_index: Optional[int]
    outcome: Optional[str]
    market_question: str
    order_min_size: float
    tick_size: float


@dataclass
class EventMeta:
    event_id: int
    title: str
    slug: str
    markets: Dict[str, MarketMeta] = field(default_factory=dict)

    def outcome_meta(self, condition_id: str, outcome_index: Optional[int]) -> OutcomeMeta:
        market = self.markets.get(condition_id)
        outcome = market.outcome_name(outcome_index) if market else None
        order_min_size = market.order_min_size if market else 0.0
        tick = market.tick_size if market else 0.01
        question = market.question if market else condition_id
        return OutcomeMeta(
            condition_id=condition_id,
            outcome_index=outcome_index,
            outcome=outcome,
            market_question=question,
            order_min_size=order_min_size,
            tick_size=tick,
        )


@dataclass
class Trade:
    timestamp: int
    proxy_wallet: str
    side: str
    condition_id: str
    outcome_index: Optional[int]
    outcome: Optional[str]
    size: float
    price: float
    tx_hash: Optional[str]


@dataclass
class HeuristicResult:
    name: str
    triggered: bool
    intensity: float
    summary: str


@dataclass
class OutcomeScore:
    outcome_label: str
    condition_id: str
    outcome_index: Optional[int]
    trades: Sequence[Trade]
    heuristics: List[HeuristicResult]
    score: float
    label: str


@dataclass
class EventScore:
    event: EventMeta
    trades: Sequence[Trade]
    heuristics: List[HeuristicResult]
    score: float
    label: str
    rationale: List[str]
    per_outcome: List[OutcomeScore]


@dataclass
class FetchOptions:
    slug: str
    lookback_seconds: int
    limit: int


