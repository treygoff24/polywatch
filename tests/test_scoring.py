import unittest

from polywatch.models import EventMeta, MarketMeta, Trade
from polywatch.scoring import analyze_event


class ScoringTest(unittest.TestCase):
    def test_analyze_event_does_not_mutate_input_trades(self) -> None:
        market = MarketMeta(
            condition_id="cid",
            question="Who wins?",
            order_min_size=5.0,
            tick_size=0.01,
            outcomes=["Yes", "No"],
            slug="cid-yes",
        )
        event = EventMeta(event_id=1, title="Test Event", slug="test-event", markets={"cid": market})
        trade = Trade(
            timestamp=1,
            proxy_wallet="wallet",
            side="BUY",
            condition_id="cid",
            outcome_index=0,
            outcome=None,
            size=10.0,
            price=0.5,
            tx_hash="abc",
        )
        trades = [trade]

        report = analyze_event(event, trades)

        self.assertIsNone(trades[0].outcome)
        self.assertEqual(report.trades[0].outcome, "Who wins? (Yes)")


if __name__ == "__main__":  # pragma: no cover
    unittest.main()
