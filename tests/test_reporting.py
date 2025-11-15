from pathlib import Path
from typing import List, Tuple
import tempfile
from unittest import TestCase
from unittest.mock import MagicMock

from polywatch.api import PolymarketClient
from polywatch.models import EventMeta, MarketMeta, Trade
from polywatch.reporting import ReportBuilder, ReportEnvelope, ReportStore


class DummyClient(PolymarketClient):
    def __init__(self, trades: List[Trade], lookback: int = 3600):
        super().__init__(session=MagicMock())
        self._trades = trades
        self._lookback = lookback

    def get_event_by_slug(self, slug: str) -> EventMeta:
        market = MarketMeta(
            condition_id="cid",
            question="Will it rain?",
            order_min_size=1.0,
            tick_size=0.01,
            outcomes=["Yes", "No"],
            slug="market-slug",
        )
        return EventMeta(event_id=123, title="Test Event", slug=slug, markets={"cid": market})

    def fetch_with_fallback(
        self,
        event_id: int,
        lookback_seconds: int,
        **kwargs,
    ) -> Tuple[List[Trade], int]:
        return self._trades, self._lookback


class ReportBuilderTest(TestCase):
    def test_build_includes_analytics(self) -> None:
        trades = [
            Trade(
                timestamp=100,
                proxy_wallet="wallet-a",
                side="BUY",
                condition_id="cid",
                outcome_index=0,
                outcome="Yes",
                size=5,
                price=0.4,
                tx_hash="tx-1",
            ),
            Trade(
                timestamp=200,
                proxy_wallet="wallet-b",
                side="SELL",
                condition_id="cid",
                outcome_index=1,
                outcome="No",
                size=3,
                price=0.6,
                tx_hash="tx-2",
            ),
        ]
        builder = ReportBuilder(client=DummyClient(trades, lookback=7200))
        envelope = builder.build("test-slug", lookback_seconds=3600)

        self.assertIsInstance(envelope, ReportEnvelope)
        self.assertEqual(envelope.slug, "test-slug")
        self.assertEqual(envelope.lookback_seconds, 7200)
        self.assertEqual(envelope.trade_count, 2)
        analytics = envelope.payload["analytics"]
        self.assertIn("marketOverview", analytics)
        self.assertEqual(analytics["marketOverview"]["totalTrades"], 2)
        self.assertIn("outcomes", analytics)
        self.assertIn("timeseries", analytics)
        self.assertEqual(envelope.summary["slug"], "test-slug")
        self.assertEqual(envelope.summary["tradeCount"], 2)


class ReportStoreTest(TestCase):
    def test_store_persists_reports_and_index(self) -> None:
        with tempfile.TemporaryDirectory(prefix="polywatch-reporting-test-") as tmp_dir:
            tmp = Path(tmp_dir)
            store = ReportStore(tmp, index_path=tmp / "index.json")

            payload = {"event": {"title": "Test", "slug": "foo", "id": 1}, "analytics": {}}
            store.write_report("foo", payload)
            loaded = store.read_report("foo")
            self.assertEqual(loaded, payload)

            summary = {
                "slug": "foo",
                "eventId": 1,
                "title": "Test",
                "label": "normal",
                "score": 0.0,
                "updatedAt": "2024-01-01T00:00:00Z",
                "lookbackSeconds": 3600,
                "tradeCount": 0,
                "lastTradeTimestamp": None,
                "topSignals": [],
                "outcomes": [],
            }
            store.upsert_summary(summary, refresh_mode="on-demand")
            index_payload = store.read_index()
            self.assertEqual(len(index_payload["reports"]), 1)
            self.assertEqual(index_payload["reports"][0]["slug"], "foo")
            self.assertEqual(index_payload["reports"][0]["refreshMode"], "on-demand")
