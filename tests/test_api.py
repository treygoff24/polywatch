import unittest
from typing import List
from unittest.mock import MagicMock

from polywatch.api import PolymarketClient
from polywatch.models import Trade


class FetchFallbackTest(unittest.TestCase):
    def test_fetch_with_fallback_returns_actual_window(self) -> None:
        sample_trade = Trade(
            timestamp=1,
            proxy_wallet="wallet",
            side="BUY",
            condition_id="cid",
            outcome_index=0,
            outcome="Yes",
            size=1.0,
            price=0.5,
            tx_hash="abc",
        )

        class DummyClient(PolymarketClient):
            def __init__(self, responses: List[List[Trade]]):
                super().__init__(session=MagicMock())
                self.responses = responses
                self.lookbacks: List[int] = []

            def fetch_trades(self, event_id: int, lookback_seconds: int, **kwargs):
                self.lookbacks.append(lookback_seconds)
                return self.responses.pop(0)

        client = DummyClient([[], [sample_trade]])
        trades, window = client.fetch_with_fallback(
            event_id=1,
            lookback_seconds=3600,
            fallback_seconds=7200,
        )

        self.assertEqual(window, 7200)
        self.assertEqual(client.lookbacks, [3600, 7200])
        self.assertEqual(trades, [sample_trade])


if __name__ == "__main__":  # pragma: no cover
    unittest.main()
