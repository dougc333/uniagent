from pathlib import Path


def resolve_path(root: Path, relative_path: str) -> Path:
    return (root / relative_path).resolve()
