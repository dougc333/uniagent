def html_with_inline_css(html: str, css: str) -> str:
    return html + f"<style>{css}</style>"
