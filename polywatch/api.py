from __future__ import annotations

import json
import logging
import warnings
import time
from typing import List, Optional

warnings.filterwarnings("ignore", message="urllib3 v2 only supports OpenSSL 1.1.1+")

import requests

from .models import EventMeta, MarketMeta, Trade
from .utils import normalize_price

GAMMA_BASE = "https://gamma-api.polymarket.com"
DATA_BASE = "https://data-api.polymarket.com"

logger = logging.getLogger(__name__)


class PolymarketClient:
    def __init__(self, session: Optional[requests.Session] = None,
                 gamma_base: str = GAMMA_BASE,
                 data_base: str = DATA_BASE) -> None:
        self.session = session or requests.Session()
        self.gamma_base = gamma_base.rstrip("/")
        self.data_base = data_base.rstrip("/")

    def get_event_by_slug(self, slug: str) -> EventMeta:
        url = f"{self.gamma_base}/events/slug/{slug}"
        resp = self.session.get(url, timeout=20)
        resp.raise_for_status()
        payload = resp.json()
        markets_payload = payload.get("markets") or []
        markets = {}
        for raw in markets_payload:
            try:
                cid = raw["conditionId"]
            except KeyError as exc:
                logger.warning("market missing conditionId: %s", exc)
                continue
            order_min = float(raw.get("orderMinSize") or 0.0)
            tick = float(raw.get("orderPriceMinTickSize") or 0.01)
            outcomes_raw = raw.get("outcomes") or []
            if isinstance(outcomes_raw, str):
                try:
                    parsed = json.loads(outcomes_raw)
                    outcomes = [str(item) for item in parsed]
                except json.JSONDecodeError:
                    outcomes = [outcomes_raw]
            else:
                outcomes = [str(item) for item in outcomes_raw]
            market = MarketMeta(
                condition_id=cid,
                question=raw.get("question") or raw.get("slug") or cid,
                order_min_size=order_min,
                tick_size=tick,
                outcomes=outcomes,
                slug=raw.get("slug"),
            )
            markets[cid] = market
        if not markets:
            raise RuntimeError("event has no markets to inspect")
        return EventMeta(
            event_id=int(payload["id"]),
            title=payload.get("title") or payload.get("question") or slug,
            slug=slug,
            markets=markets,
        )

    def fetch_trades(self, event_id: int, lookback_seconds: int, page_limit: int = 10000,
                     max_pages: int = 100, sleep_seconds: float = 0.2) -> List[Trade]:
        now = int(time.time())
        cutoff = now - lookback_seconds
        trades: List[Trade] = []
        seen = set()
        offset = 0
        pages = 0
        while pages < max_pages:
            url = f"{self.data_base}/trades?eventId={event_id}&limit={page_limit}&offset={offset}"
            resp = self.session.get(url, timeout=30)
            resp.raise_for_status()
            batch = resp.json()
            if not batch:
                break
            stop = False
            for raw in batch:
                ts = int(raw.get("timestamp", 0))
                if ts < cutoff:
                    stop = True
                    break
                key = (
                    raw.get("transactionHash"),
                    raw.get("conditionId"),
                    raw.get("outcomeIndex"),
                    raw.get("size"),
                    raw.get("price"),
                    ts,
                )
                if key in seen:
                    continue
                seen.add(key)
                price = normalize_price(float(raw.get("price", 0.0)))
                trade = Trade(
                    timestamp=ts,
                    proxy_wallet=(raw.get("proxyWallet") or "").lower(),
                    side=raw.get("side") or "BUY",
                    condition_id=raw.get("conditionId") or "",
                    outcome_index=self._safe_int(raw.get("outcomeIndex")),
                    outcome=raw.get("outcome"),
                    size=float(raw.get("size") or 0.0),
                    price=price,
                    tx_hash=raw.get("transactionHash"),
                )
                trades.append(trade)
            pages += 1
            if stop:
                break
            offset += page_limit
            time.sleep(sleep_seconds)
        trades.sort(key=lambda t: t.timestamp)
        return trades

    def fetch_with_fallback(
        self,
        event_id: int,
        lookback_seconds: int,
        fallback_seconds: int = 72 * 3600,
        page_limit: int = 10000,
        max_pages: int = 100,
        sleep_seconds: float = 0.2,
    ) -> List[Trade]:
        trades = self.fetch_trades(
            event_id,
            lookback_seconds,
            page_limit=page_limit,
            max_pages=max_pages,
            sleep_seconds=sleep_seconds,
        )
        if trades or lookback_seconds >= fallback_seconds:
            return trades
        logger.info("no trades found, widening lookback to %s", fallback_seconds)
        return self.fetch_trades(
            event_id,
            fallback_seconds,
            page_limit=page_limit,
            max_pages=max_pages,
            sleep_seconds=sleep_seconds,
        )

    @staticmethod
    def _safe_int(value: Optional[int]) -> Optional[int]:
        if value is None:
            return None
        try:
            return int(value)
        except (TypeError, ValueError):
            return None
