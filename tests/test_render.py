import unittest

from polywatch.models import EventMeta, EventScore, HeuristicResult, OutcomeScore, Trade
from polywatch.render import render_text_report


class RenderTest(unittest.TestCase):
    def test_render_text_report_includes_tables_and_metrics(self) -> None:
        event = EventMeta(event_id=99, title="Example Event", slug="example", markets={})
        trades = [
            Trade(timestamp=1, proxy_wallet="abc", side="BUY", condition_id="cid", outcome_index=0, outcome="Yes", size=10, price=0.6, tx_hash="t1"),
            Trade(timestamp=2, proxy_wallet="def", side="SELL", condition_id="cid", outcome_index=0, outcome="Yes", size=5, price=0.55, tx_hash="t2"),
            Trade(timestamp=3, proxy_wallet="abc", side="BUY", condition_id="cid", outcome_index=1, outcome="No", size=7, price=0.42, tx_hash="t3"),
        ]
        heuristics = [
            HeuristicResult(name="wallet_concentration", triggered=True, intensity=0.8, summary="wallet concentration test summary"),
            HeuristicResult(name="min_size_spam", triggered=False, intensity=0.1, summary="min size ok"),
        ]
        per_outcome = [
            OutcomeScore(
                outcome_label="Yes",
                condition_id="cid",
                outcome_index=0,
                trades=tuple(trades[:2]),
                heuristics=heuristics,
                score=62.5,
                label="suspicious",
            ),
            OutcomeScore(
                outcome_label="No",
                condition_id="cid",
                outcome_index=1,
                trades=tuple(trades[2:]),
                heuristics=heuristics,
                score=12.0,
                label="normal",
            ),
        ]
        report = EventScore(
            event=event,
            trades=tuple(trades),
            heuristics=heuristics,
            score=58.3,
            label="watch",
            rationale=["wallet concentration triggered"],
            per_outcome=per_outcome,
        )

        output = render_text_report(report, lookback_seconds=3600)

        self.assertIn("Market Overview", output)
        self.assertIn("Total trades", output)
        self.assertIn("Top wallet (notional)", output)
        self.assertIn("Outcome Snapshot", output)
        self.assertIn("Yes", output)
        self.assertIn("No", output)
        self.assertIn("Suspicion Indicators", output)
        self.assertIn("Wallet Concentration", output)
        self.assertIn("Top signals", output)


if __name__ == "__main__":  # pragma: no cover
    unittest.main()
