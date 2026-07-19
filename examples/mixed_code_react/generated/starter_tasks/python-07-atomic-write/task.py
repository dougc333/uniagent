from pathlib import Path


def atomic_write(path: Path, text: str) -> None:
    path.write_text(text)
