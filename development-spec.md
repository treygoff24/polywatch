Below is a tight, developer‑ready plan for a small CLI program that inspects the **Honduras Presidential Election** event on Polymarket and flags unusual or bot‑like activity using only Polymarket’s public APIs. It’s intentionally simple, dependency‑light, and easy to extend.

---

## 1) What we’re building

A command‑line tool that:

1. Resolves the **event slug** `honduras-presidential-election` to its numeric `event.id` and enumerates the underlying markets/outcomes. ([Polymarket Documentation][1])
2. Pulls recent **trades** for that event via the **Data API** (`/trades`) using `eventId=` and paginates client‑side. ([Polymarket Documentation][2])
3. Computes a handful of **microstructure heuristics** from the trade stream (wallet concentration, trade size patterns vs min size, inter‑trade timing regularity, ping‑ponging, rapid round‑trips, etc.).
4. Produces a **single suspicion score (0–100)** plus a short, human‑readable explanation and per‑outcome detail, then exits with code `0` (normal) or `2` (suspicious) for easy scripting/cron use.

The **scope** is deliberately narrow: trades only (no order cancellations), short lookback (default 24h), and thresholds tuned for practical signal, not perfection. All API usage stays within Polymarket’s published endpoints and rate limits. ([Polymarket Documentation][3])

---

## 2) Data sources and key fields

- **Event by slug**: `GET https://gamma-api.polymarket.com/events/slug/{slug}` → returns `event.id` and a `markets[]` array; each market includes `conditionId`, `orderMinSize`, `orderPriceMinTickSize`, `outcomes`, and other metadata. We’ll use this to map outcomes and to know min size / tick. ([Polymarket Documentation][1])

- **Trades (Data API)**: `GET https://data-api.polymarket.com/trades?eventId={id}&limit={n}&offset={m}`. Returned items include (among others):
  `proxyWallet` (taker address), `side`, `conditionId`, `size`, `price`, `timestamp`, `eventSlug`, `outcome`, `outcomeIndex`, `transactionHash`. Default `takerOnly=true`. We’ll paginate with `offset` and filter by `timestamp` client‑side to a given lookback window. ([Polymarket Documentation][2])

- Notes:

  - You can filter trades **by `eventId`** or **by `market` (conditionId list)**. We’ll prefer the single `eventId` call to cover all outcomes at once. ([Polymarket Documentation][2])
  - **Rate limits** exist; for Data API `/trades` the published limit is **75 requests / 10s**. We’ll batch with large `limit` (e.g., 10,000) and backoff to stay well inside limits. ([Polymarket Documentation][4])
  - “Slug” is officially supported and is the fastest path to a specific event/market. ([Polymarket Documentation][5])

---

## 3) Heuristics (the simple, useful ones)

All are computed **per event** and also **per outcome**. A market flagged by multiple independent heuristics will typically be worth investigating.

1. **Wallet concentration**
   Compute each `proxyWallet`’s share of taker trade **count** and **USDC notional** (size×price) in the lookback. Flag if:

   - Top‑1 wallet ≥ 60% of trades **and** ≥ 40% of notional, or
   - Top‑3 wallets ≥ 85% of trades.
     Rationale: one bot or a small bot set dominating flow is unusual for healthy, retail‑heavy markets.

2. **Min‑size spamming**
   Using `orderMinSize` from the market metadata, compute the share of trades with `size ≤ 1.5×orderMinSize`. Flag if **> 75%** of trades are at (or near) min‑size **and** there are ≥ 100 trades in the window. (A lot of tiny taker prints looks like pinging/quote‑nibbling bots.) ([Polymarket Documentation][6])

3. **Inter‑trade timing regularity**
   Compute inter‑arrival times (seconds between consecutive trades per outcome). If **coefficient of variation (CV) < 0.35** while trades/minute > the event’s 24h median by **≥ 3σ**, flag. Rationale: inorganic periodicity at elevated rates.

4. **Ping‑pong sequences**
   For each wallet×outcome, detect alternating `BUY`/`SELL` sequences with gaps ≤ 60s and size within ±20% of prior trade size. If **≥ 20%** of that wallet’s trades on an outcome are in ping‑pong sequences, mark that wallet; if marked wallets account for **≥ 40%** of the outcome’s trades, flag.

5. **Fast round‑trips**
   For each wallet×outcome, if the wallet **reverses** within 10 minutes (BUY→SELL or SELL→BUY) with little price drift (≤ 1 tick), count as a round‑trip. If **round‑trips / total trades ≥ 0.33** for the wallet and such wallets account for **≥ 30%** of outcome trades, flag. (Rough proxy for inventory‑neutral, latency‑style bots; still catches organic MM to a lesser degree.)

6. **Price whip with reversion** (simple form)
   Compute 1‑minute price deltas from trades; a “whip” is |Δp| ≥ 5 percentage points in ≤ 1 minute followed by ≥ 80% reversion within 5 minutes, with ≥ 10 trades in the episode and ≥ 70% of episode prints initiated by ≤ 3 wallets. If ≥ 2 such episodes in the window, flag.

These are thresholded defaults; expose them via CLI flags for easy tuning.

---

## 4) Scoring and classification

- Score each heuristic **Hᵢ ∈ {0,1}** (untriggered/triggered) and **intensity** (scaled 0–1 from how far past threshold).
- Combine:
  `Score = 25%*WalletConc + 20%*MinSize + 20%*Timing + 15%*PingPong + 10%*RoundTrip + 10%*Whip`
- Map to label:

  - **0–34** → “normal”
  - **35–59** → “watch”
  - **60–100** → “suspicious”

- Output a short rationale listing the top 2–4 drivers.

---

## 5) Program flow (high level)

1. **Resolve event**
   `GET /events/slug/honduras-presidential-election` → capture `event.id`, `markets[]` (name/slug, `conditionId`, `orderMinSize`, `orderPriceMinTickSize`, outcomes). ([Polymarket Documentation][1])

2. **Fetch trades**
   `GET /trades?eventId={id}&limit=10000&offset={k}` until either:

   - No more results, or
   - Oldest `timestamp` is older than the lookback window (default 24h).
     Respect Data API limits (sleep/backoff if needed). ([Polymarket Documentation][2])

3. **Normalize & join**

   - Convert `timestamp` (seconds) to UTC datetimes; drop outside window.
   - Join trades to outcome metadata via `conditionId`+`outcomeIndex`; fall back to `outcome` string from the trade payload when present (it usually is). ([Polymarket Documentation][2])

4. **Compute features & score**
   Calculate per‑outcome and event‑level stats, evaluate heuristics, aggregate to score.

5. **Render**
   Print a single event summary + per‑outcome lines; optional `--json` to write a machine‑readable report to disk.

---

## 6) CLI design (example)

```
$ polywatch --slug honduras-presidential-election \
            --lookback 24h \
            --limit 10000 \
            --thresholds default \
            --json out.json

Event: Honduras Presidential Election (id=12345)  Window: last 24h  Trades: 3,241
Overall suspicion score: 68  →  suspicious
Top drivers: wallet concentration (71%), min-size spamming (82%), timing regularity (CV=0.28 @ +3.6σ)

By outcome:
- Rixi Moncada          score 63  | top1 wallet 58% trades (44% notional) | 79% ≤ 1.5×min-size | ping-pong 24%
- Salvador Nasralla     score 52  | top3 wallets 86% trades               | 66% ≤ 1.5×min-size | timing CV 0.33
- Nasry Asfura          score 31  | normal
Exit code: 2
```

---

## 7) Minimal tech stack

- **Language**: Python 3.10+
- **Deps**: `requests` (HTTP), `pydantic` (schema), `pandas` (metrics) — all optional but convenient.
- **Runtime**: single file or small package; no DB required.

---

## 8) API contracts the code relies on (with examples)

- **Get event by slug**
  `GET https://gamma-api.polymarket.com/events/slug/honduras-presidential-election`
  Returns `id` and `markets[]` with fields including `conditionId`, `orderMinSize`, `orderPriceMinTickSize`, etc. ([Polymarket Documentation][1])

- **Get trades by event**
  `GET https://data-api.polymarket.com/trades?eventId={EVENT_ID}&limit=10000&offset=0`
  Response items include `proxyWallet`, `side`, `conditionId`, `size`, `price`, `timestamp`, `outcome`, `outcomeIndex`. Default `takerOnly=true`. Paginate with `offset`. ([Polymarket Documentation][2])

- **Rate limits**
  Data API `/trades`: **75 req / 10s**. Use a simple token bucket or fixed sleeps between pages. ([Polymarket Documentation][4])

- **Background** (not required, but useful references): endian endpoints overview and CLOB/RTDS index. ([Polymarket Documentation][3])

---

## 9) Data model (Python)

```python
from typing import List, Optional, Dict, Tuple
from pydantic import BaseModel

class MarketMeta(BaseModel):
    condition_id: str
    slug: str
    title: str
    order_min_size: float
    tick_size: float
    outcomes: List[str]

class Trade(BaseModel):
    proxy_wallet: str
    side: str  # 'BUY' or 'SELL'
    condition_id: str
    outcome_index: int
    outcome: Optional[str]
    size: float
    price: float  # in % (0–100) or 0–1? (Polymarket returns price in implied probability units)
    ts: int      # unix seconds
    tx: str
```

_(Developers: check whether `price` is 0–1 or 0–100 in your test run and normalize; the docs describe “implied probability” units — tick size is in implied probability units. Keep everything in 0–1 internally.)_ ([Polymarket Documentation][6])

---

## 10) Heuristic algorithms (concise pseudocode)

```python
def compute_wallet_concentration(trades):
    by_wallet = groupby(trades, key=lambda t: t.proxy_wallet)
    counts = [len(v) for v in by_wallet.values()]
    notionals = [sum(t.size * t.price for t in v) for v in by_wallet.values()]
    top1_ct = max(counts)/sum(counts)
    top1_nt = max(notionals)/sum(notionals)
    top3_ct = sum(sorted(counts, reverse=True)[:3])/sum(counts)
    h = 1 if (top1_ct >= 0.60 and top1_nt >= 0.40) or (top3_ct >= 0.85) else 0
    intensity = max(top1_ct, top3_ct)
    return h, intensity

def compute_min_size_spam(trades, order_min_size):
    frac = sum(t.size <= 1.5*order_min_size for t in trades) / max(1,len(trades))
    h = 1 if (len(trades) >= 100 and frac > 0.75) else 0
    return h, frac

def compute_timing_regular(trades):
    times = sorted(t.ts for t in trades)
    gaps = [t2-t1 for t1,t2 in zip(times, times[1:])]
    if len(gaps) < 10: return 0, 0.0
    cv = (np.std(gaps)/max(1e-6, np.mean(gaps)))
    # compute z-score of current trades/minute vs median across window
    rpm_series = resample_to_minute_count(times)
    z = (rpm_series[-1] - np.median(rpm_series)) / (1.4826*np.median(|rpm - median|))  # robust
    h = 1 if (cv < 0.35 and z >= 3.0) else 0
    return h, max(0, 3.0 if h else 0)  # crude intensity

def compute_ping_pong(trades):
    by_wallet = groupby(sorted(trades, key=lambda t: t.ts), key=lambda t: t.proxy_wallet)
    marked = set()
    for w, seq in by_wallet.items():
        alt = 0; prev=None
        for t in seq:
            if prev and t.ts - prev.ts <= 60 and t.side != prev.side and abs(t.size - prev.size)/max(prev.size,1e-6) <= 0.2:
                alt += 1
            prev = t
        if len(seq) and alt/len(seq) >= 0.20: marked.add(w)
    frac = sum(t.proxy_wallet in marked for t in trades)/max(1,len(trades))
    h = 1 if frac >= 0.40 else 0
    return h, frac

def compute_round_trips(trades):
    by_wallet = groupby(sorted(trades, key=lambda t: t.ts), key=lambda t: t.proxy_wallet)
    marked_frac = 0.0; total=len(trades)
    for w, seq in by_wallet.items():
        rt=0
        for a,b in zip(seq, seq[1:]):
            if b.ts-a.ts<=600 and a.side!=b.side and abs(b.price-a.price)<=tick_size:
                rt+=1
        if len(seq) and rt/len(seq)>=0.33:
            marked_frac += len(seq)
    frac = marked_frac/max(1,total)
    h = 1 if frac>=0.30 else 0
    return h, frac

def compute_whips(trades):
    # naive: minute buckets of VWAP → detect ±5pp spikes and 80% 5-min reversion
    vwap = minute_vwap_series(trades)
    episodes = detect_whips(vwap, min_jump=0.05, revert=0.8, horizon=5)
    # Require concentration by ≤3 wallets within episode window:
    count=0
    for ep in episodes:
        sub = [t for t in trades if ep.start <= t.ts <= ep.end]
        if len(sub)>=10 and top_k_share(sub, k=3) >= 0.70: count += 1
    h = 1 if count >= 2 else 0
    return h, count
```

Combine each `h,intensity` with the weights listed in §4 to produce the **event score** and **per‑outcome** scores.

---

## 11) Error handling & edge cases

- If `events/slug` 404s or returns no `markets`, exit with code `3` and a clear message. ([Polymarket Documentation][1])
- If `/trades` returns 200 but empty results for a fresh window, automatically widen lookback to 72h (once) before giving up. ([Polymarket Documentation][2])
- If you hit rate limits, backoff 2–4 seconds and resume. Published limit for `/trades` is 75/10s. ([Polymarket Documentation][4])
- Some trades are split across multiple “trade entities” at the CLOB level; the Data API already gives a single list. As a cheap dedupe, drop exact duplicate `(tx, conditionId, outcomeIndex, size, price, timestamp)` if ever observed. ([Polymarket Documentation][7])

---

## 12) Implementation checklist

- [ ] `EventClient.get_event_by_slug(slug)` → `EventMeta` with `id`, `markets[]` (`conditionId`, `orderMinSize`, `orderPriceMinTickSize`, `outcomes`). ([Polymarket Documentation][1])
- [ ] `TradesClient.get_trades(event_id, limit, lookback)` → paginated fetch with `offset` and `timestamp` filtering. ([Polymarket Documentation][2])
- [ ] Normalization layer for prices (convert to 0–1 float), sizes (float), timestamps (UTC).
- [ ] Feature calculators for the six heuristics.
- [ ] Scoring aggregator + labeler.
- [ ] Renderers: text and optional JSON.
- [ ] Exit codes (`0` normal, `1` watch, `2` suspicious, `3` runtime/API errors).
- [ ] Small unit tests for each heuristic (feed synthetic sequences).
- [ ] Fixture test: run against a calm market and a volatile market to see thresholds behave sensibly.

---

## 13) Example HTTP calls the program will make

**Get event meta**

```
GET https://gamma-api.polymarket.com/events/slug/honduras-presidential-election
```

→ parse `id`, iterate `markets[]` to read `conditionId`, `orderMinSize`, `orderPriceMinTickSize`, `outcomes`. ([Polymarket Documentation][1])

**Get trades for that event**

```
GET https://data-api.polymarket.com/trades?eventId={EVENT_ID}&limit=10000&offset=0
# loop offset by +10000 until oldest trade < now-lookback or no results
```

Fields used: `proxyWallet`, `side`, `conditionId`, `size`, `price`, `timestamp`, `outcome`, `outcomeIndex`, `transactionHash`. ([Polymarket Documentation][2])

**Notes on endpoints & rate limits**
Endpoints index and rate-limit table are documented here. Use sleeps/backoff to stay well inside the limits. ([Polymarket Documentation][3])

---

## 14) Skeleton code (single file)

```python
#!/usr/bin/env python3
import argparse, time, math, json, sys
from collections import defaultdict, Counter
import requests
import pandas as pd

GAMMA_BASE = "https://gamma-api.polymarket.com"
DATA_BASE  = "https://data-api.polymarket.com"

def get_event_by_slug(slug):
    r = requests.get(f"{GAMMA_BASE}/events/slug/{slug}", timeout=20)
    r.raise_for_status()
    ev = r.json()
    markets = []
    for m in ev.get("markets", []):
        markets.append({
            "conditionId": m["conditionId"],
            "slug": m.get("slug"),
            "title": m.get("question") or m.get("slug"),
            "orderMinSize": float(m.get("orderMinSize") or 0),
            "tickSize": float(m.get("orderPriceMinTickSize") or 0),
            "outcomes": m.get("outcomes"),
        })
    return {"id": int(ev["id"]), "title": ev["title"], "markets": markets}

def fetch_trades_for_event(event_id, lookback_secs=86400, page_limit=10000):
    now = int(time.time())
    cutoff = now - lookback_secs
    offset = 0
    all_trades = []
    while True:
        url = f"{DATA_BASE}/trades?eventId={event_id}&limit={page_limit}&offset={offset}"
        r = requests.get(url, timeout=30)
        r.raise_for_status()
        batch = r.json()
        if not batch: break
        for t in batch:
            ts = int(t["timestamp"])
            if ts < cutoff:
                return all_trades
            all_trades.append({
                "ts": ts,
                "wallet": t["proxyWallet"].lower(),
                "side": t["side"],
                "cid": t["conditionId"],
                "out_idx": t.get("outcomeIndex"),
                "outcome": t.get("outcome"),
                "size": float(t["size"]),
                "price": float(t["price"]),  # normalize to 0..1 if needed
                "tx": t.get("transactionHash")
            })
        offset += page_limit
        time.sleep(0.15)  # be nice to rate limits
    return all_trades

# … add metric functions from §10, final aggregator, and a simple text/JSON renderer …

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--slug", required=True)
    ap.add_argument("--lookback", default="24h")
    ap.add_argument("--limit", type=int, default=10000)
    ap.add_argument("--json", default=None)
    args = ap.parse_args()

    lookback_map = {"h":3600, "d":86400}
    unit = args.lookback[-1]
    num = int(args.lookback[:-1])
    lookback_secs = num * lookback_map[unit]

    ev = get_event_by_slug(args.slug)
    trades = fetch_trades_for_event(ev["id"], lookback_secs, args.limit)

    # compute features per outcome and aggregate…
    # score, label, reasons = score_event(trades, ev["markets"])
    # print nicely; write JSON if requested; set exit code

if __name__ == "__main__":
    main()
```

This is intentionally terse: your developer drops in the feature calculators from §10 and the renderers, then tunes thresholds.

---

## 15) Validation plan

- **Dry‑run** the tool against the Honduras event today to confirm payload shapes and price units, and to capture a small JSON snapshot for deterministic unit tests. Event and trades endpoints and field shapes are documented in Polymarket’s official docs referenced above. ([Polymarket Documentation][1])
- **Threshold tuning**: run over a few known‑calm political events and a few high‑attention events, compare flags to intuition. Keep defaults conservative; Trey can loosen if he wants more alerts.

---

## 16) Extensions (optional, still simple)

- **Live mode**: poll every 30s and print deltas.
- **Orderbook context**: pull `/book` from the CLOB REST to estimate spread slippage around flagged bursts (obeys separate limits). ([Polymarket Documentation][4])
- **Wallet lookups**: top wallet drill‑down by re‑querying `/trades?user=0x…` to see behavior across events. ([Polymarket Documentation][2])
- **Slack webhook**: send a one‑liner alert when score crosses `watch` or `suspicious`.

---

### Why this is the right balance

It uses the **official slug→event→trades** path Polymarket recommends, relies on documented query parameters and response shapes, and stays within **published rate limits**. It avoids complex market‑maker inference but still catches the common bot signatures you’ll care about for triage. ([Polymarket Documentation][5])

If you want, I can turn the skeleton into a runnable script with argparse, JSON output, and unit tests next.

[1]: https://docs.polymarket.com/api-reference/events/get-event-by-slug "Get event by slug - Polymarket Documentation"
[2]: https://docs.polymarket.com/developers/CLOB/trades/trades-data-api "Get Trades (Data-API) - Polymarket Documentation"
[3]: https://docs.polymarket.com/developers/CLOB/endpoints "Endpoints - Polymarket Documentation"
[4]: https://docs.polymarket.com/quickstart/introduction/rate-limits "API Rate Limits - Polymarket Documentation"
[5]: https://docs.polymarket.com/developers/gamma-markets-api/fetch-markets-guide "How to Fetch Markets - Polymarket Documentation"
[6]: https://docs.polymarket.com/developers/gamma-markets-api/get-markets "Get Markets - Polymarket Documentation"
[7]: https://docs.polymarket.com/developers/CLOB/trades/trades-overview "Trades Overview - Polymarket Documentation"
