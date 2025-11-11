import unittest

from polywatch.utils import normalize_price, parse_lookback


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


if __name__ == "__main__":  # pragma: no cover
    unittest.main()
