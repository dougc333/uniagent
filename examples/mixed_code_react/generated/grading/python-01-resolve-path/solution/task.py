from pathlib import Path


def resolve_path(root: Path, relative_path: str) -> Path:
    root = root.resolve()
    path = (root / relative_path).resolve()
    if path != root and root not in path.parents:
        raise ValueError(f"Path escapes benchmark root: {relative_path}")
    return path
