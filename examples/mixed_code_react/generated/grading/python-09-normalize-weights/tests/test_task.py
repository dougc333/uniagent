import unittest

from task import normalized_weights


class NormalizeWeightsTests(unittest.TestCase):
    def test_normalizes_and_applies_override(self):
        result = normalized_weights({"a": 1, "b": 1}, {"a": 3})
        self.assertAlmostEqual(result["a"], 0.75)
        self.assertAlmostEqual(result["b"], 0.25)
        self.assertAlmostEqual(sum(result.values()), 1.0)

    def test_rejects_unknown(self):
        with self.assertRaises(ValueError):
            normalized_weights({"a": 1}, {"b": 1})

    def test_rejects_negative_and_zero_total(self):
        with self.assertRaises(ValueError):
            normalized_weights({"a": -1})
        with self.assertRaises(ValueError):
            normalized_weights({"a": 0, "b": 0})

    def test_does_not_mutate_inputs(self):
        defaults = {"a": 1, "b": 2}
        overrides = {"a": 2}
        normalized_weights(defaults, overrides)
        self.assertEqual(defaults, {"a": 1, "b": 2})
        self.assertEqual(overrides, {"a": 2})


if __name__ == "__main__":
    unittest.main()
