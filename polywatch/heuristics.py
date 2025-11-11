from __future__ import annotations

import math
from collections import Counter, defaultdict
from statistics import median
from typing import Callable, DefaultDict, List, Sequence

from .models import HeuristicResult, Trade
from .utils import rolling_minutes, top_k_trade_share, vwap_by_minute


def _share_top(values: Sequence[int], top: int, total: int) -> float:
    if total == 0:
        return 0.0
    return sum(sorted(values, reverse=True)[:top]) / total


def _format_pct(value: float) -> str:
    return f"{value * 100:.0f}%"


def wallet_concentration(trades: Sequence[Trade]) -> HeuristicResult:
    total = len(trades)
    counts: Counter[str] = Counter()
    notionals: DefaultDict[str, float] = defaultdict(float)
    for trade in trades:
        counts[trade.proxy_wallet] += 1
        notionals[trade.proxy_wallet] += trade.size * trade.price
    if not counts:
        return HeuristicResult("wallet_concentration", False, 0.0, "insufficient trades")
    top1_ct = max(counts.values()) / total
    top1_notional = max(notionals.values()) / max(1e-9, sum(notionals.values()))
    top3_ct = _share_top(list(counts.values()), 3, total)
    triggered = (top1_ct >= 0.60 and top1_notional >= 0.40) or (top3_ct >= 0.85)
    intensity = min(1.0, max(top1_ct, top3_ct))
    summary = (
        f"wallet concentration top1={_format_pct(top1_ct)} trades ({_format_pct(top1_notional)} notional), "
        f"top3={_format_pct(top3_ct)}"
    )
    return HeuristicResult("wallet_concentration", triggered, intensity, summary)


def min_size_spam(trades: Sequence[Trade], order_min_lookup: Callable[[Trade], float]) -> HeuristicResult:
    if not trades:
        return HeuristicResult("min_size_spam", False, 0.0, "no trades")
    evaluated = 0
    near_min = 0
    for trade in trades:
        min_size = order_min_lookup(trade)
        if min_size <= 0:
            continue
        evaluated += 1
        if trade.size <= 1.5 * min_size:
            near_min += 1
    if evaluated == 0:
        return HeuristicResult("min_size_spam", False, 0.0, "no min-size metadata")
    share = near_min / evaluated
    triggered = len(trades) >= 100 and share > 0.75
    summary = f"min-size trades share={_format_pct(share)} over {len(trades)} trades"
    return HeuristicResult("min_size_spam", triggered, min(1.0, share), summary)


def _cv(values: Sequence[float]) -> float:
    if not values:
        return 0.0
    mean_value = sum(values) / len(values)
    if mean_value == 0:
        return 0.0
    variance = sum((x - mean_value) ** 2 for x in values) / len(values)
    return math.sqrt(variance) / mean_value


def _mad(values: Sequence[int], med: float) -> float:
    deviations = [abs(v - med) for v in values]
    if not deviations:
        return 0.0
    return median(deviations)


def timing_regularity(trades: Sequence[Trade]) -> HeuristicResult:
    if len(trades) < 15:
        return HeuristicResult("timing_regular", False, 0.0, "not enough trades")
    timestamps = sorted(t.timestamp for t in trades)
    gaps = [b - a for a, b in zip(timestamps, timestamps[1:])]
    gaps = [gap for gap in gaps if gap > 0]
    if len(gaps) < 10:
        return HeuristicResult("timing_regular", False, 0.0, "insufficient gaps")
    cv = _cv(gaps)
    minutes, per_minute = rolling_minutes(trades)
    if not per_minute:
        return HeuristicResult("timing_regular", False, 0.0, "no minute buckets")
    current = per_minute[-1]
    med = median(per_minute)
    mad = _mad(per_minute, med)
    sigma = 1.4826 * mad if mad > 0 else 1.0
    z = (current - med) / sigma if sigma else 0.0
    triggered = cv < 0.35 and z >= 3.0
    cv_component = max(0.0, min(1.0, (0.35 - cv) / 0.35))
    z_component = max(0.0, min(1.0, (z - 3.0) / 3.0))
    intensity = max(cv_component, z_component)
    summary = f"timing CV={cv:.2f}, z-score={z:.1f}"
    return HeuristicResult("timing_regular", triggered, intensity, summary)


def ping_pong_sequences(trades: Sequence[Trade]) -> HeuristicResult:
    if len(trades) < 10:
        return HeuristicResult("ping_pong", False, 0.0, "small sample")
    by_wallet: DefaultDict[str, List[Trade]] = defaultdict(list)
    for trade in trades:
        by_wallet[trade.proxy_wallet].append(trade)
    marked_wallets = set()
    for wallet, seq in by_wallet.items():
        seq.sort(key=lambda t: t.timestamp)
        marked_indices = set()
        prev = None
        prev_idx = None
        for idx, trade in enumerate(seq):
            if prev is None:
                prev = trade
                prev_idx = idx
                continue
            size_ratio = abs(trade.size - prev.size) / max(prev.size, trade.size, 1e-9)
            if (
                trade.side != prev.side
                and trade.timestamp - prev.timestamp <= 60
                and size_ratio <= 0.20
            ):
                marked_indices.add(idx)
                if prev_idx is not None:
                    marked_indices.add(prev_idx)
            prev = trade
            prev_idx = idx
        if seq and len(marked_indices) / len(seq) >= 0.20:
            marked_wallets.add(wallet)
    if not marked_wallets:
        return HeuristicResult("ping_pong", False, 0.0, "no alternating sequences")
    total_trades = len(trades)
    marked_trades = sum(len(by_wallet[w]) for w in marked_wallets)
    share = marked_trades / total_trades
    triggered = share >= 0.40
    summary = f"ping-pong wallets share={_format_pct(share)} of trades"
    return HeuristicResult("ping_pong", triggered, min(1.0, share), summary)


def round_trips(trades: Sequence[Trade], tick_lookup: Callable[[Trade], float]) -> HeuristicResult:
    if len(trades) < 10:
        return HeuristicResult("round_trips", False, 0.0, "small sample")
    by_wallet: DefaultDict[str, List[Trade]] = defaultdict(list)
    for trade in trades:
        by_wallet[trade.proxy_wallet].append(trade)
    marked_wallets = set()
    for wallet, seq in by_wallet.items():
        seq.sort(key=lambda t: t.timestamp)
        rt = 0
        for idx in range(1, len(seq)):
            current = seq[idx]
            prev = seq[idx - 1]
            if current.side == prev.side:
                continue
            if current.timestamp - prev.timestamp > 600:
                continue
            tick = max(tick_lookup(current), tick_lookup(prev), 0.01)
            price_diff = abs(current.price - prev.price)
            if price_diff <= tick:
                rt += 1
        if seq and rt / len(seq) >= 0.33:
            marked_wallets.add(wallet)
    if not marked_wallets:
        return HeuristicResult("round_trips", False, 0.0, "no rapid reversals")
    total_trades = len(trades)
    marked_trades = sum(len(by_wallet[w]) for w in marked_wallets)
    share = marked_trades / total_trades
    triggered = share >= 0.30
    summary = f"round-trip wallets share={_format_pct(share)} of trades"
    return HeuristicResult("round_trips", triggered, min(1.0, share), summary)


def price_whips(trades: Sequence[Trade]) -> HeuristicResult:
    if len(trades) < 20:
        return HeuristicResult("price_whips", False, 0.0, "small sample")
    vwap = vwap_by_minute(trades)
    minutes = sorted(vwap.keys())
    if not minutes:
        return HeuristicResult("price_whips", False, 0.0, "no minute bars")
    minute_trades: DefaultDict[int, List[Trade]] = defaultdict(list)
    for trade in trades:
        minute_trades[trade.timestamp // 60].append(trade)
    episodes = 0
    idx = 0
    while idx < len(minutes):
        start_minute = minutes[idx]
        start_price = vwap[start_minute]
        j = idx + 1
        candidate_found = False
        while j < len(minutes) and minutes[j] - start_minute <= 1:
            delta = vwap[minutes[j]] - start_price
            if abs(delta) >= 0.05:
                candidate_found = True
                break
            j += 1
        if not candidate_found:
            idx += 1
            continue
        move_minute = minutes[j]
        end_limit = move_minute + 5
        reverted = False
        k = j + 1
        next_idx = idx + 1
        while k < len(minutes) and minutes[k] <= end_limit:
            revert_price = vwap[minutes[k]]
            if abs(revert_price - start_price) <= 0.2 * abs(vwap[move_minute] - start_price):
                episode_trades = []
                for minute in range(start_minute, minutes[k] + 1):
                    episode_trades.extend(minute_trades.get(minute, []))
                if len(episode_trades) >= 10:
                    top_share = top_k_trade_share(episode_trades, 3)
                    if top_share >= 0.70:
                        episodes += 1
                        reverted = True
                        next_idx = k + 1
                        break
            k += 1
        if not reverted:
            idx += 1
        else:
            idx = next_idx
    triggered = episodes >= 2
    intensity = min(1.0, episodes / 3)
    summary = f"price whips detected={episodes}"
    return HeuristicResult("price_whips", triggered, intensity, summary)


def constant_lookup(value: float) -> Callable[[Trade], float]:
    return lambda _trade: value
