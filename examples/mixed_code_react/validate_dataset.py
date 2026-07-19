#!/usr/bin/env python3
"""Validate generated task assets, Parquet rows, and gold solutions."""

from __future__ import annotations

import argparse
import json
import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

EXAMPLE_ROOT = Path(__file__).resolve().parent


def run_python_gold(task_id: str, generated_root: Path) -> None:
    starter = generated_root / "starter_tasks" / task_id
    grading = generated_root / "grading" / task_id
    with tempfile.TemporaryDirectory() as tmp:
        workspace = Path(tmp) / "workspace"
        shutil.copytree(starter, workspace)
        shutil.copy2(grading / "solution" / "task.py", workspace / "task.py")
        env = dict(os.environ)
        env["PYTHONPATH"] = str(workspace)
        subprocess.run(
            ["python3", str(grading / "tests" / "test_task.py")],
            cwd=workspace,
            env=env,
            check=True,
        )


def run_react_gold(task_id: str, generated_root: Path, image: str) -> None:
    starter = (generated_root / "starter_tasks" / task_id).resolve()
    grading = (generated_root / "grading" / task_id).resolve()
    with tempfile.TemporaryDirectory() as tmp:
        temp_root = Path(tmp).resolve()
        workspace = temp_root / "workspace"
        logs = temp_root / "logs"
        shutil.copytree(starter, workspace)
        logs.mkdir()
        command = [
            "docker",
            "run",
            "--rm",
            "-v",
            f"{workspace}:/workspace",
            "-v",
            f"{grading / 'tests'}:/tests:ro",
            "-v",
            f"{grading / 'solution'}:/solution:ro",
            "-v",
            f"{logs}:/logs/verifier",
            image,
            "bash",
            "-lc",
            (
                "ln -sfn /opt/react-runtime/node_modules /workspace/node_modules && "
                "cp /solution/styles.css /workspace/src/styles.css && "
                "python3 /tests/grade_react.py --workspace /workspace "
                "--reference /tests/reference.png --screenshot /logs/verifier/candidate.png"
            ),
        ]
        subprocess.run(command, check=True)
        payload = json.loads((logs / "reward.json").read_text(encoding="utf-8"))
        if float(payload["reward"]) < 0.99:
            raise AssertionError(f"{task_id} gold visual reward was {payload['reward']}, expected >= 0.99")


def run_react_gold_host(
    task_id: str,
    generated_root: Path,
    node_modules: Path,
    browser_channel: str,
) -> None:
    starter = generated_root / "starter_tasks" / task_id
    grading = generated_root / "grading" / task_id
    with tempfile.TemporaryDirectory(prefix="uni-agent-react-host-") as tmp:
        temp_root = Path(tmp)
        workspace = temp_root / "workspace"
        logs = temp_root / "logs"
        shutil.copytree(starter, workspace)
        shutil.copy2(grading / "solution" / "styles.css", workspace / "src" / "styles.css")
        (workspace / "node_modules").symlink_to(node_modules, target_is_directory=True)
        command = [
            sys.executable,
            str(grading / "tests" / "grade_react.py"),
            "--workspace",
            str(workspace),
            "--reference",
            str(grading / "tests" / "reference.png"),
            "--screenshot",
            str(logs / "candidate.png"),
            "--log-dir",
            str(logs),
            "--browser-channel",
            browser_channel,
        ]
        subprocess.run(command, check=True)
        payload = json.loads((logs / "reward.json").read_text(encoding="utf-8"))
        if float(payload["reward"]) < 0.99:
            raise AssertionError(f"{task_id} gold visual reward was {payload['reward']}, expected >= 0.99")


def validate_parquet(generated_root: Path) -> None:
    try:
        from datasets import load_dataset
    except ImportError as exc:
        raise RuntimeError("Install `datasets` to validate Parquet files") from exc

    expected = {"all.parquet": 20, "train.parquet": 16, "test.parquet": 4}
    with tempfile.TemporaryDirectory(prefix="uni-agent-hf-cache-") as cache_dir:
        for name, expected_rows in expected.items():
            path = generated_root / "data" / name
            dataset = load_dataset(
                "parquet",
                data_files=str(path),
                split="train",
                cache_dir=cache_dir,
            )
            if len(dataset) != expected_rows:
                raise AssertionError(f"{name}: expected {expected_rows} rows, found {len(dataset)}")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--generated-root", type=Path, default=EXAMPLE_ROOT / "generated")
    visual_group = parser.add_mutually_exclusive_group()
    visual_group.add_argument("--docker", action="store_true", help="Run React graders in Docker")
    visual_group.add_argument("--host-react", action="store_true", help="Run React graders on this host")
    parser.add_argument("--image", default="uni-agent-mixed-code-react:latest")
    parser.add_argument("--node-modules", type=Path, help="React runtime node_modules for --host-react")
    parser.add_argument("--browser-channel", default="chrome", help="Playwright channel for --host-react")
    parser.add_argument("--skip-parquet", action="store_true")
    args = parser.parse_args()

    generated_root = args.generated_root.expanduser().resolve()
    manifest = json.loads((generated_root / "manifest.json").read_text(encoding="utf-8"))
    if manifest["task_count"] != 20:
        raise AssertionError(f"Expected 20 tasks, found {manifest['task_count']}")
    if manifest["python_task_count"] != 10 or manifest["react_task_count"] != 10:
        raise AssertionError("Expected a 10 Python / 10 React balance")

    python_tasks = [task for task in manifest["tasks"] if task["task_type"] == "python"]
    for task in python_tasks:
        run_python_gold(task["task_id"], generated_root)

    if not args.skip_parquet:
        validate_parquet(generated_root)

    if args.docker:
        subprocess.run(["docker", "image", "inspect", args.image], check=True, stdout=subprocess.DEVNULL)
        react_tasks = [task for task in manifest["tasks"] if task["task_type"] == "react"]
        for task in react_tasks:
            run_react_gold(task["task_id"], generated_root, args.image)
    elif args.host_react:
        if args.node_modules is None:
            parser.error("--host-react requires --node-modules")
        node_modules = args.node_modules.expanduser().resolve()
        if not node_modules.is_dir():
            parser.error(f"node_modules directory does not exist: {node_modules}")
        react_tasks = [task for task in manifest["tasks"] if task["task_type"] == "react"]
        for task in react_tasks:
            run_react_gold_host(
                task["task_id"],
                generated_root,
                node_modules,
                args.browser_channel,
            )

    suffix = " plus 10 React gold visual rewards" if args.docker or args.host_react else ""
    print(f"Validated 20 task records, 10 Python gold solutions{suffix}.", flush=True)


if __name__ == "__main__":
    main()
