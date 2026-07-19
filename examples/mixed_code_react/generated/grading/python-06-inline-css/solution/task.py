import re


def html_with_inline_css(html: str, css: str) -> str:
    pattern = r'<link\s+rel=["\']stylesheet["\']\s+href=["\'][^"\']+["\']\s*/?>'
    rendered, replacements = re.subn(
        pattern,
        "<style>\n" + css + "\n</style>",
        html,
        flags=re.I,
    )
    if replacements != 1:
        raise ValueError("Fixture must contain exactly one stylesheet link")
    return rendered
