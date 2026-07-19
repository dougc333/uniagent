import unittest

from task import build_prompt


class BuildPromptTests(unittest.TestCase):
    def test_contains_all_task_material(self):
        prompt = build_prompt(
            {"css_filename": "button.css", "description": "Make it blue."},
            "<button>Go</button>",
        )
        self.assertIn("button.css", prompt)
        self.assertIn("Make it blue.", prompt)
        self.assertIn("<button>Go</button>", prompt)

    def test_contains_determinism_rules(self):
        prompt = build_prompt(
            {"css_filename": "x.css", "description": "x"},
            "<main></main>",
        ).lower()
        self.assertIn("css only", prompt)
        self.assertIn("800px by 600px", prompt)
        self.assertIn("external", prompt)
        self.assertIn("overflow", prompt)


if __name__ == "__main__":
    unittest.main()
