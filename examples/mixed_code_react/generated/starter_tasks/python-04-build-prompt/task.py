def build_prompt(case: dict, html: str) -> str:
    return f"Write CSS for this page:\n{html}"
