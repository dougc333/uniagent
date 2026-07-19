def build_prompt(case: dict, html: str) -> str:
    return f"""You are completing a deterministic CSS benchmark.

Write the complete contents of `{case["css_filename"]}` for the immutable HTML
below. Follow the visual specification exactly.

Rules:
- Return CSS only, without Markdown fences or commentary.
- Do not change or repeat the HTML.
- Do not use JavaScript, data URLs, external images, @import, or network fonts.
- The viewport is exactly 800px by 600px with devicePixelRatio 1.
- Avoid horizontal and vertical overflow.

VISUAL SPECIFICATION
{case["description"]}

HTML
{html}
"""
