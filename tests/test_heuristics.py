import unittest
from typing import List

from polywatch import heuristics
from polywatch.models import Trade

BASE_TS = 1_700_000_000


def make_trade(
    offset: int,
    wallet: str,
    side: str = "BUY",
    size: float = 1.0,
    price: float = 0.5,
    condition: str = "cid",
) -> Trade:
    return Trade(
        timestamp=BASE_TS + offset,
        proxy_wallet=wallet,
        side=side,
        condition_id=condition,
        outcome_index=0,
        outcome="Yes",
        size=size,
        price=price,
        tx_hash=None,
    )


class HeuristicsTest(unittest.TestCase):
    def test_wallet_concentration_flags_single_dominant_wallet(self) -> None:
        trades: List[Trade] = []
        trades.extend([make_trade(i * 30, "w-dominant", size=2.0, price=0.65) for i in range(80)])
        trades.extend([make_trade(2400 + i * 40, "w-2", size=1.0) for i in range(15)])
        trades.extend([make_trade(2600 + i * 50, "w-3", size=1.0) for i in range(5)])
        result = heuristics.wallet_concentration(trades)
        self.assertTrue(result.triggered)
        self.assertIn("top1", result.summary)

    def test_min_size_spam_counts_small_trades(self) -> None:
        trades = [make_trade(i * 20, f"w{i%3}", size=10.0) for i in range(120)]
        lookup = heuristics.constant_lookup(8.0)
        result = heuristics.min_size_spam(trades, lookup)
        self.assertTrue(result.triggered)
        self.assertGreater(result.intensity, 0.75)

    def test_timing_regular_detects_low_cv_and_high_z(self) -> None:
        trades: List[Trade] = []
        for i in range(200):
            trades.append(make_trade(i * 30, wallet=f"w{i%4}", price=0.4))
        burst_start = 200 * 30
        trades.extend(make_trade(burst_start + i, wallet="burst", price=0.45) for i in range(25))
        result = heuristics.timing_regularity(trades)
        self.assertTrue(result.triggered)
        self.assertGreater(result.intensity, 0.0)

    def test_ping_pong_sequences_mark_wallets(self) -> None:
        trades: List[Trade] = []
        for i in range(20):
            trades.append(
                make_trade(i * 20, "bot", side="BUY" if i % 2 == 0 else "SELL", size=10.0)
            )
        trades.extend(make_trade(1000 + i * 100, wallet="noise", size=3.0) for i in range(10))
        result = heuristics.ping_pong_sequences(trades)
        self.assertTrue(result.triggered)
        self.assertIn("ping-pong", result.summary)

    def test_round_trips_detect_reversals(self) -> None:
        trades: List[Trade] = []
        for i in range(15):
            side = "BUY" if i % 2 == 0 else "SELL"
            trades.append(make_trade(i * 40, "scalper", side=side, price=0.45 + (i % 2) * 0.005))
        trades.extend(make_trade(2000 + i * 200, wallet="noise", price=0.55) for i in range(5))
        result = heuristics.round_trips(trades, heuristics.constant_lookup(0.01))
        self.assertTrue(result.triggered)
        self.assertGreaterEqual(result.intensity, 0.30)

    def test_price_whips_counts_multiple_episodes(self) -> None:
        trades: List[Trade] = []

        def add_block(start_minute: int, prices: List[float]) -> None:
            for idx, price in enumerate(prices):
                minute = start_minute + idx
                for j in range(4):
                    trades.append(
                        make_trade(
                            minute * 60 + j,
                            wallet=f"whale{j%2}",
                            price=price,
                            side="BUY" if j % 2 == 0 else "SELL",
                        )
                    )

        add_block(0, [0.40, 0.47, 0.45, 0.41])
        add_block(10, [0.55, 0.48, 0.50, 0.56])
        add_block(14, [0.50])

        result = heuristics.price_whips(trades)
        self.assertTrue(result.triggered)
        self.assertIn("detected", result.summary)


if __name__ == "__main__":  # pragma: no cover
    unittest.main()
