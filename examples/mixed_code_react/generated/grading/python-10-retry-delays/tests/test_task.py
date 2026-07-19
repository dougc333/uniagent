import unittest

from task import retry_delays


class RetryDelayTests(unittest.TestCase):
    def test_default_backoff(self):
        self.assertEqual(retry_delays(5), [5, 10, 20, 40])

    def test_cap_is_applied(self):
        self.assertEqual(retry_delays(6, base_seconds=10, cap_seconds=25), [10, 20, 25, 25, 25])

    def test_one_attempt_has_no_delay(self):
        self.assertEqual(retry_delays(1), [])

    def test_invalid_arguments(self):
        for args in [(0, 5, 60), (2, 0, 60), (2, 5, 0)]:
            with self.subTest(args=args), self.assertRaises(ValueError):
                retry_delays(*args)


if __name__ == "__main__":
    unittest.main()
