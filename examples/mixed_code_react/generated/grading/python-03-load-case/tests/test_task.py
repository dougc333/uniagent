import unittest

from task import load_case


class LoadCaseTests(unittest.TestCase):
    def test_returns_exact_match(self):
        cases = [{"id": "a", "value": 1}, {"id": "ab", "value": 2}]
        self.assertIs(load_case(cases, "a"), cases[0])

    def test_duplicate_returns_first(self):
        cases = [{"id": "a", "value": 1}, {"id": "a", "value": 2}]
        self.assertEqual(load_case(cases, "a")["value"], 1)

    def test_missing_raises_key_error(self):
        with self.assertRaisesRegex(KeyError, "missing"):
            load_case([{"id": "present"}], "missing")

    def test_input_is_not_mutated(self):
        cases = [{"id": "a"}]
        before = [dict(item) for item in cases]
        load_case(cases, "a")
        self.assertEqual(cases, before)


if __name__ == "__main__":
    unittest.main()
