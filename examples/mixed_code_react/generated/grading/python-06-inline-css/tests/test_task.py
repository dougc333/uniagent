import unittest

from task import html_with_inline_css


class InlineCssTests(unittest.TestCase):
    def test_replaces_double_quoted_link(self):
        html = '<head><link rel="stylesheet" href="x.css"></head>'
        rendered = html_with_inline_css(html, "body{}")
        self.assertNotIn("<link", rendered)
        self.assertIn("<style>\nbody{}\n</style>", rendered)

    def test_replaces_single_quoted_self_closing_link(self):
        html = "<link rel='stylesheet' href='x.css' />"
        self.assertIn("<style>", html_with_inline_css(html, "a{}"))

    def test_missing_link_is_rejected(self):
        with self.assertRaises(ValueError):
            html_with_inline_css("<main></main>", "a{}")

    def test_multiple_links_are_rejected(self):
        html = (
            '<link rel="stylesheet" href="a.css">'
            '<link rel="stylesheet" href="b.css">'
        )
        with self.assertRaises(ValueError):
            html_with_inline_css(html, "a{}")


if __name__ == "__main__":
    unittest.main()
