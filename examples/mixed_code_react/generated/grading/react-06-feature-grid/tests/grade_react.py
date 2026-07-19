#!/usr/bin/env python3
"""Render one React task and write a continuous visual reward.

This file is copied into the hidden verifier archive by ``generate_dataset.py``.
It intentionally uses the same visual-composite metric as cssbenchmark-aks.
"""

from __future__ import annotations

import argparse
import json
import socket
import subprocess
import time
import urllib.request
from pathlib import Path

from playwright.sync_api import sync_playwright
from visual_metrics import visual_similarity


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--workspace", type=Path, default=Path("/workspace"))
    parser.add_argument("--reference", type=Path, default=Path("/tests/reference.png"))
    parser.add_argument("--screenshot", type=Path, default=Path("/logs/verifier/candidate.png"))
    parser.add_argument("--log-dir", type=Path, default=Path("/logs/verifier"))
    parser.add_argument("--browser-channel", help="Playwright browser channel, for example 'chrome'")
    parser.add_argument("--port", type=int, default=0, help="Vite port; zero chooses a free local port")
    return parser.parse_args()


def wait_until_ready(url: str, timeout: float = 30.0) -> None:
    deadline = time.monotonic() + timeout
    last_error: Exception | None = None
    while time.monotonic() < deadline:
        try:
            with urllib.request.urlopen(url, timeout=1.0) as response:
                if response.status == 200:
                    return
        except Exception as exc:
            last_error = exc
        time.sleep(0.25)
    raise TimeoutError(f"React development server did not become ready: {last_error}")


def choose_port(requested_port: int) -> int:
    if requested_port:
        return requested_port
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as server_socket:
        server_socket.bind(("127.0.0.1", 0))
        return int(server_socket.getsockname()[1])


def render(url: str, screenshot: Path, browser_channel: str | None) -> dict[str, bool]:
    screenshot.parent.mkdir(parents=True, exist_ok=True)
    with sync_playwright() as playwright:
        launch_options: dict = {
            "headless": True,
            "args": ["--disable-dev-shm-usage"],
        }
        if browser_channel:
            launch_options["channel"] = browser_channel
        browser = playwright.chromium.launch(
            **launch_options,
        )
        context = browser.new_context(
            viewport={"width": 800, "height": 600},
            device_scale_factor=1,
        )
        page = context.new_page()
        page.goto(url, wait_until="networkidle")
        page.add_style_tag(content="*,*::before,*::after{animation:none!important;transition:none!important}")
        page.evaluate("() => document.fonts.ready")
        overflow = page.evaluate(
            """() => ({
              horizontal: document.documentElement.scrollWidth > window.innerWidth,
              vertical: document.documentElement.scrollHeight > window.innerHeight
            })"""
        )
        page.screenshot(path=str(screenshot), full_page=False)
        context.close()
        browser.close()
        return overflow


def write_reward(payload: dict, log_dir: Path) -> None:
    log_dir.mkdir(parents=True, exist_ok=True)
    (log_dir / "reward.json").write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")


def main() -> None:
    args = parse_args()
    port = choose_port(args.port)
    url = f"http://127.0.0.1:{port}"
    server_log_path = args.log_dir / "vite.log"
    server_log_path.parent.mkdir(parents=True, exist_ok=True)

    with server_log_path.open("w", encoding="utf-8") as server_log:
        server = subprocess.Popen(
            [
                "npm",
                "run",
                "dev",
                "--",
                "--host",
                "127.0.0.1",
                "--port",
                str(port),
                "--strictPort",
            ],
            cwd=args.workspace,
            stdout=server_log,
            stderr=subprocess.STDOUT,
            text=True,
        )
        try:
            wait_until_ready(url)
            overflow = render(url, args.screenshot, args.browser_channel)
            metrics = visual_similarity(args.reference, args.screenshot)
            overflow_axes = int(overflow["horizontal"]) + int(overflow["vertical"])
            reward = float(metrics["composite_similarity"]) * (0.9**overflow_axes)
            payload = {
                "reward": round(reward, 6),
                "full_frame_similarity": round(float(metrics["full_frame_similarity"]), 6),
                "foreground_similarity": round(float(metrics["foreground_similarity"]), 6),
                "edge_similarity": round(float(metrics["edge_similarity"]), 6),
                "layout_similarity": round(float(metrics["layout_similarity"]), 6),
                "horizontal_overflow": bool(overflow["horizontal"]),
                "vertical_overflow": bool(overflow["vertical"]),
            }
            write_reward(payload, args.log_dir)
            print(json.dumps(payload, indent=2), flush=True)
        except Exception as exc:
            payload = {
                "reward": 0.0,
                "error": f"{type(exc).__name__}: {exc}",
            }
            write_reward(payload, args.log_dir)
            print(json.dumps(payload, indent=2), flush=True)
        finally:
            server.terminate()
            try:
                server.wait(timeout=5)
            except subprocess.TimeoutExpired:
                server.kill()
                server.wait(timeout=5)


if __name__ == "__main__":
    main()
