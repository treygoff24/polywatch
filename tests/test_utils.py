import unittest

from polywatch.models import Trade
from polywatch.utils import normalize_price, parse_lookback, top_k_trade_share


class UtilsTest(unittest.TestCase):
    def test_parse_lookback_parses_units(self) -> None:
        self.assertEqual(parse_lookback("15m"), 900)
        self.assertEqual(parse_lookback("2h"), 7200)
        self.assertEqual(parse_lookback("1d"), 86400)

    def test_normalize_price_handles_percentages(self) -> None:
        self.assertAlmostEqual(normalize_price(0.42), 0.42)
        self.assertAlmostEqual(normalize_price(42.0), 0.42)
        self.assertEqual(normalize_price(101.0), 1.0)
        self.assertEqual(normalize_price(-3.0), 0.0)

    def test_top_k_trade_share_handles_missing_wallets(self) -> None:
        trades = [
            Trade(
                timestamp=1,
                proxy_wallet=None,
                side="BUY",
                condition_id="cid",
                outcome_index=0,
                outcome="Yes",
                size=1.0,
                price=0.5,
                tx_hash="a",
            ),
            Trade(
                timestamp=2,
                proxy_wallet=None,
                side="SELL",
                condition_id="cid",
                outcome_index=0,
                outcome="Yes",
                size=1.0,
                price=0.5,
                tx_hash="b",
            ),
            Trade(
                timestamp=3,
                proxy_wallet="wallet-x",
                side="BUY",
                condition_id="cid",
                outcome_index=0,
                outcome="Yes",
                size=1.0,
                price=0.5,
                tx_hash="c",
            ),
        ]
        share = top_k_trade_share(trades, 1)
        self.assertGreaterEqual(share, 1 / 3)
        self.assertLess(share, 1.0)


if __name__ == "__main__":  # pragma: no cover
    unittest.main()
