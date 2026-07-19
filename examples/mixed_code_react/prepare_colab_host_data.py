#!/usr/bin/env python3
"""Rewrite generated rows for direct, unsandboxed execution in a Colab VM."""

from __future__ import annotations

import argparse
import copy
import shlex
from pathlib import Path

EXAMPLE_ROOT = Path(__file__).resolve().parent


def host_setup_command(task_id: str, repo_root: Path, node_modules: Path) -> str:
    starter = repo_root / "examples" / "mixed_code_react" / "generated" / "starter_tasks" / task_id
    commands = [
        # Each episode shares the same machine, so remove all state left by the
        # previous episode before exposing the next task.
        "pkill -f '/workspace/node_modules/.bin/vite' >/dev/null 2>&1 || true",
        "rm -rf /workspace /tests /solution /logs/verifier",
        "mkdir -p /workspace /logs/agent",
        f"cp -a {shlex.quote(str(starter))}/. /workspace/",
    ]
    if task_id.startswith("react-"):
        commands.append(f"ln -sfn {shlex.quote(str(node_modules))} /workspace/node_modules")
    commands.extend(
        [
            # Reduce accidental secret exposure. This is not a security
            # boundary: an unsandboxed agent can still inspect the host.
            ("unset HF_TOKEN HUGGING_FACE_HUB_TOKEN WANDB_API_KEY NGROK_AUTHTOKEN GOOGLE_APPLICATION_CREDENTIALS"),
            "cd /workspace",
        ]
    )
    return " && ".join(commands)


def rewrite_rows(dataset, repo_root: Path, node_modules: Path):
    rows = []
    for source_row in dataset:
        row = copy.deepcopy(source_row)
        task_id = row["extra_info"]["task_id"]
        row["extra_info"]["tools_kwargs"]["env"]["post_setup_cmd"] = host_setup_command(
            task_id,
            repo_root,
            node_modules,
        )
        row["extra_info"]["tools_kwargs"]["reward"]["metadata"]["workdir"] = "/workspace"
        rows.append(row)
    return rows


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--repo-root", type=Path, default=EXAMPLE_ROOT.parents[1])
    parser.add_argument(
        "--node-modules",
        type=Path,
        default=Path("/content/uniagent-react-runtime/node_modules"),
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=EXAMPLE_ROOT / "generated" / "data",
    )
    args = parser.parse_args()

    try:
        from datasets import Dataset
    except ImportError as exc:
        raise RuntimeError("Install `datasets` before preparing Colab data") from exc

    repo_root = args.repo_root.expanduser().resolve()
    node_modules = args.node_modules.expanduser().resolve()
    output_dir = args.output_dir.expanduser().resolve()
    source_dir = repo_root / "examples" / "mixed_code_react" / "generated" / "data"

    if not (repo_root / "uni_agent").is_dir():
        raise FileNotFoundError(f"Not a Uni-Agent repository: {repo_root}")
    if not node_modules.is_dir():
        raise FileNotFoundError(f"React runtime not installed at {node_modules}; run setup_colab_a100.sh first")

    output_dir.mkdir(parents=True, exist_ok=True)
    expected = {"all": 20, "train": 16, "test": 4}
    for split, expected_rows in expected.items():
        source = source_dir / f"{split}.parquet"
        dataset = Dataset.from_parquet(str(source))
        rows = rewrite_rows(dataset, repo_root, node_modules)
        if len(rows) != expected_rows:
            raise AssertionError(f"{split}: expected {expected_rows} rows, found {len(rows)}")
        destination = output_dir / f"{split}_colab_host.parquet"
        Dataset.from_list(rows).to_parquet(str(destination))
        print(f"Wrote {len(rows)} rows to {destination}", flush=True)


if __name__ == "__main__":
    main()
