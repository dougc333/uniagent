#!/usr/bin/env python3
"""Rewrite generated rows for direct, unsandboxed execution in a Colab VM."""

from __future__ import annotations

import argparse
import copy
import json
import shlex
from pathlib import Path

EXAMPLE_ROOT = Path(__file__).resolve().parent


def rebuild_base_parquets(dataset_cls, generated_root: Path) -> None:
    """Rebuild git-ignored Parquet files from the bundled generated assets."""
    from generate_dataset import tar_gz_bytes

    data_dir = generated_root / "data"
    tasks_path = data_dir / "tasks.jsonl"
    manifest_path = generated_root / "manifest.json"
    if not tasks_path.is_file():
        raise FileNotFoundError(
            f"Missing both base Parquet data and {tasks_path}. "
            "Upload the complete examples/mixed_code_react/generated directory."
        )

    previews = [
        json.loads(line)
        for line in tasks_path.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]
    if len(previews) != 20:
        raise ValueError(f"Expected 20 task previews in {tasks_path}, found {len(previews)}")

    manifest = {}
    if manifest_path.is_file():
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    source_revision = manifest.get("source_revision") or ""

    samples_by_split: dict[str, list[dict]] = {"train": [], "test": []}
    all_samples: list[dict] = []
    for preview in previews:
        split = preview["split"]
        if split not in samples_by_split:
            raise ValueError(f"Unexpected split {split!r} for {preview['task_id']}")

        task_id = preview["task_id"]
        task_type = preview["task_type"]
        grading_dir = generated_root / "grading" / task_id
        solution_dir = grading_dir / "solution"
        tests_dir = grading_dir / "tests"
        if not solution_dir.is_dir() or not tests_dir.is_dir():
            raise FileNotFoundError(
                f"Missing bundled grading assets for {task_id}; "
                "upload the complete generated directory."
            )

        setup_commands = [
            "mkdir -p /workspace",
            f"cp -a /opt/tasks/{task_id}/. /workspace/",
        ]
        if task_type == "react":
            setup_commands.append("ln -sfn /opt/react-runtime/node_modules /workspace/node_modules")
        setup_commands.append("cd /workspace")

        metadata = {
            "task_id": task_id,
            "title": preview["title"],
            "task_type": task_type,
            "source_path": preview["source_path"],
            "source_revision": source_revision,
            "workdir": "/workspace",
            "task_config": {
                "agent": {"timeout_sec": 120.0},
                "verifier": {"timeout_sec": 120.0},
            },
            "solution_archive": tar_gz_bytes(solution_dir),
            "tests_archive": tar_gz_bytes(tests_dir),
            "solve_relpath": "solve.sh",
            "test_relpath": "test.sh",
        }
        sample = {
            "prompt": preview["prompt"],
            "agent_name": preview["agent_name"],
            "extra_info": {
                "task_id": task_id,
                "task_type": task_type,
                "data_source": "cssbenchmark-aks-mixed",
                "source_root": "bundled-generated-assets",
                "source_path": preview["source_path"],
                "tools_kwargs": {
                    "env": {"post_setup_cmd": " && ".join(setup_commands)},
                    "reward": {
                        "name": "terminal_bench_v2",
                        "eval_timeout": 120.0,
                        "metadata": metadata,
                    },
                },
            },
        }
        all_samples.append(sample)
        samples_by_split[split].append(sample)

    expected = {"all": 20, "train": 16, "test": 4}
    datasets = {
        "all": all_samples,
        "train": samples_by_split["train"],
        "test": samples_by_split["test"],
    }
    data_dir.mkdir(parents=True, exist_ok=True)
    for split, rows in datasets.items():
        if len(rows) != expected[split]:
            raise AssertionError(f"{split}: expected {expected[split]} rows, found {len(rows)}")
        destination = data_dir / f"{split}.parquet"
        dataset_cls.from_list(rows).to_parquet(str(destination))
        print(f"Rebuilt {len(rows)} rows at {destination}", flush=True)


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
    missing_sources = [
        source_dir / f"{split}.parquet"
        for split in expected
        if not (source_dir / f"{split}.parquet").is_file()
    ]
    if missing_sources:
        print(
            "Base Parquet files are absent (they may have been omitted by .gitignore); "
            "rebuilding them from bundled generated assets.",
            flush=True,
        )
        rebuild_base_parquets(Dataset, source_dir.parent)

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
