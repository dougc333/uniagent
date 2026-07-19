import unittest

from task import extract_css


class ExtractCssTests(unittest.TestCase):
    def test_plain_css(self):
        self.assertEqual(extract_css("  body { color: red; }  "), "body { color: red; }\n")

    def test_fenced_css(self):
        response = "comment\n```CSS\nbody { margin: 0; }\n```\nmore"
        self.assertEqual(extract_css(response), "body { margin: 0; }\n")

    def test_leading_introduction(self):
        self.assertEqual(extract_css("Here's the CSS: body{}"), "body{}\n")

    def test_empty_is_rejected(self):
        with self.assertRaises(ValueError):
            extract_css("```css\n \n```")


if __name__ == "__main__":
    unittest.main()
