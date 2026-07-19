import re


def extract_css(text: str) -> str:
    fenced = re.search(r"```(?:css)?\s*(.*?)```", text, flags=re.I | re.S)
    if fenced:
        text = fenced.group(1)
    text = re.sub(r"^\s*(?:Here(?:'s| is).*?:)\s*", "", text, flags=re.I)
    css = text.strip()
    if not css:
        raise ValueError("Model returned an empty stylesheet")
    return css + "\n"
