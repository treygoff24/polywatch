from __future__ import annotations

import re
from collections import defaultdict
from datetime import datetime, timezone
from typing import DefaultDict, Dict, List, Optional, Sequence, Tuple

from .models import Trade

_DURATION_RE = re.compile(r"^(?P<value>\d+)(?P<unit>[smhd])$")


def parse_lookback(value: str) -> int:
    match = _DURATION_RE.match(value.strip())
    if not match:
        raise ValueError("lookback must be like 15m, 2h, 1d")
    amount = int(match.group("value"))
    unit = match.group("unit")
    multiplier = {"s": 1, "m": 60, "h": 3600, "d": 86400}[unit]
    return amount * multiplier


def normalize_price(value: float) -> float:
    if value > 1.0:
        if value <= 100.0:
            value = value / 100.0
        else:
            value = 1.0
    if value < 0.0:
        value = 0.0
    if value > 1.0:
        value = 1.0
    return value


def unix_to_iso(ts: int) -> str:
    return datetime.fromtimestamp(ts, tz=timezone.utc).isoformat()


def group_trades_by_outcome(trades: Sequence[Trade]) -> Dict[Tuple[str, Optional[int]], List[Trade]]:
    groups: DefaultDict[Tuple[str, Optional[int]], List[Trade]] = defaultdict(list)
    for trade in trades:
        groups[(trade.condition_id, trade.outcome_index)].append(trade)
    return groups


def rolling_minutes(trades: Sequence[Trade]) -> Tuple[List[int], List[int]]:
    if not trades:
        return [], []
    counts: DefaultDict[int, int] = defaultdict(int)
    for trade in trades:
        minute = trade.timestamp // 60
        counts[minute] += 1
    minutes = sorted(counts.keys())
    values = [counts[m] for m in minutes]
    return minutes, values


def vwap_by_minute(trades: Sequence[Trade]) -> Dict[int, float]:
    buckets: DefaultDict[int, List[Tuple[float, float]]] = defaultdict(list)
    for trade in trades:
        minute = trade.timestamp // 60
        buckets[minute].append((trade.price, trade.size))
    vwap: Dict[int, float] = {}
    for minute, values in buckets.items():
        total_size = sum(size for _, size in values)
        if total_size == 0:
            continue
        vwap[minute] = sum(price * size for price, size in values) / total_size
    return vwap


def top_k_trade_share(trades: Sequence[Trade], k: int) -> float:
    if not trades:
        return 0.0
    counts: DefaultDict[str, int] = defaultdict(int)
    for trade in trades:
        counts[trade.proxy_wallet] += 1
    shares = sorted(counts.values(), reverse=True)
    return sum(shares[:k]) / len(trades)
