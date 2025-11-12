import unittest

from polywatch.cli import label_to_exit_code


class CliTest(unittest.TestCase):
    def test_label_to_exit_code_matches_spec(self) -> None:
        self.assertEqual(label_to_exit_code("normal"), 0)
        self.assertEqual(label_to_exit_code("watch"), 0)
        self.assertEqual(label_to_exit_code("suspicious"), 2)
        self.assertEqual(label_to_exit_code("SUSPICIOUS"), 2)


if __name__ == "__main__":  # pragma: no cover
    unittest.main()
