import json
from pathlib import Path


def read_jsonl_line(path: Path, index: int) -> dict:
    lines = path.read_text(encoding="utf-8").splitlines()
    return json.loads(lines[index])
