import json
from pathlib import Path


def read_jsonl_line(path: Path, index: int) -> dict:
    if index < 0:
        raise IndexError(f"JSONL index {index} is outside {path}")
    current = 0
    with path.open("r", encoding="utf-8") as handle:
        for line in handle:
            if not line.strip():
                continue
            if current == index:
                return json.loads(line)
            current += 1
    raise IndexError(f"JSONL index {index} is outside {path}")
