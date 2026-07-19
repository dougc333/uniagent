import json
from pathlib import Path


def load_entries(path: Path) -> list[dict]:
    return [json.loads(path.read_text(encoding="utf-8"))]
