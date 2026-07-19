# ruff: noqa: E501
"""Create 10 Python and 10 React tasks for a Uni-Agent + veRL example.

The Python tasks are small bug-fix exercises adapted from utilities in
``cssbenchmark-aks``. The React tasks preserve the ten benchmark designs,
reference screenshots, and exact CSS specifications while expressing the
original HTML as React components.

The generated Parquet rows use Uni-Agent's normal ``swe_agent`` schema and
the existing ``terminal_bench_v2`` reward contract. Python tasks receive a
binary unit-test reward; React tasks receive the benchmark's continuous
visual-composite reward.
"""

from __future__ import annotations

import argparse
import gzip
import json
import shutil
import subprocess
import tarfile
from dataclasses import dataclass
from io import BytesIO
from pathlib import Path
from textwrap import dedent
from typing import Any

EXAMPLE_ROOT = Path(__file__).resolve().parent
DEFAULT_OUTPUT_DIR = EXAMPLE_ROOT / "generated"
CSS_BENCHMARK_CANDIDATES = (
    Path("/Users/dc/cssbenchmarks-aks"),
    Path("/Users/dc/cssbenchmark-aks"),
)

SYSTEM_PROMPT = """
You are a coding agent working in /workspace. Inspect the existing files, make
the smallest correct implementation change, run any useful local checks, and
call the submit tool when the task is complete. Do not modify hidden tests.
""".strip()

PYTHON_USER_PROMPT = """
Fix the Python implementation described below.

<task>
{description}
</task>

The starter module is /workspace/task.py. Work only in /workspace, preserve
the documented public API, and use Python's standard library only.
""".strip()

REACT_USER_PROMPT = """
Implement the React design described below.

<task>
{description}
</task>

The React/Vite project is in /workspace. The component markup is in
src/App.jsx and the stylesheet to implement is src/styles.css. A reference
screenshot is available at /workspace/reference.png. The grader renders at
exactly 800x600 CSS pixels with devicePixelRatio 1 and calculates a continuous
visual similarity reward. Do not use external assets, network fonts,
JavaScript animation, CSS animation, transitions, or transforms.
""".strip()


@dataclass(frozen=True)
class PythonTask:
    task_id: str
    title: str
    description: str
    source_path: str
    starter: str
    solution: str
    tests: str


def python_tasks() -> list[PythonTask]:
    """Return ten bug-fix tasks adapted from cssbenchmark-aks utilities."""
    return [
        PythonTask(
            task_id="python-01-resolve-path",
            title="Keep benchmark paths inside their root",
            source_path="grader.py:resolve_path",
            description=(
                "resolve_path(root, relative_path) currently resolves paths without checking their boundary. "
                "Return the resolved Path only when it is root itself or a descendant of root. Raise ValueError "
                "for ../ traversal and absolute paths outside root."
            ),
            starter="""
                from pathlib import Path


                def resolve_path(root: Path, relative_path: str) -> Path:
                    return (root / relative_path).resolve()
            """,
            solution="""
                from pathlib import Path


                def resolve_path(root: Path, relative_path: str) -> Path:
                    root = root.resolve()
                    path = (root / relative_path).resolve()
                    if path != root and root not in path.parents:
                        raise ValueError(f"Path escapes benchmark root: {relative_path}")
                    return path
            """,
            tests="""
                import tempfile
                import unittest
                from pathlib import Path

                from task import resolve_path


                class ResolvePathTests(unittest.TestCase):
                    def test_child_is_allowed(self):
                        with tempfile.TemporaryDirectory() as tmp:
                            root = Path(tmp)
                            self.assertEqual(resolve_path(root, "cases/a.css"), (root / "cases/a.css").resolve())

                    def test_root_is_allowed(self):
                        with tempfile.TemporaryDirectory() as tmp:
                            root = Path(tmp)
                            self.assertEqual(resolve_path(root, "."), root.resolve())

                    def test_parent_escape_is_rejected(self):
                        with tempfile.TemporaryDirectory() as tmp:
                            root = Path(tmp) / "root"
                            root.mkdir()
                            with self.assertRaises(ValueError):
                                resolve_path(root, "../secret.txt")

                    def test_absolute_escape_is_rejected(self):
                        with tempfile.TemporaryDirectory() as tmp:
                            root = Path(tmp) / "root"
                            root.mkdir()
                            with self.assertRaises(ValueError):
                                resolve_path(root, "/etc/passwd")


                if __name__ == "__main__":
                    unittest.main()
            """,
        ),
        PythonTask(
            task_id="python-02-read-jsonl",
            title="Read indexed JSONL records",
            source_path="worker.py:read_jsonl_line",
            description=(
                "read_jsonl_line(path, index) must return the indexed non-empty JSON record. Blank lines do not "
                "count as records. Reject negative indexes and raise IndexError when the requested record is absent."
            ),
            starter="""
                import json
                from pathlib import Path


                def read_jsonl_line(path: Path, index: int) -> dict:
                    lines = path.read_text(encoding="utf-8").splitlines()
                    return json.loads(lines[index])
            """,
            solution="""
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
            """,
            tests="""
                import json
                import tempfile
                import unittest
                from pathlib import Path

                from task import read_jsonl_line


                class ReadJsonlTests(unittest.TestCase):
                    def setUp(self):
                        self.tmp = tempfile.TemporaryDirectory()
                        self.path = Path(self.tmp.name) / "data.jsonl"
                        self.path.write_text('{"id": 1}\\n\\n{"id": 2}\\n', encoding="utf-8")

                    def tearDown(self):
                        self.tmp.cleanup()

                    def test_reads_non_empty_record(self):
                        self.assertEqual(read_jsonl_line(self.path, 1), {"id": 2})

                    def test_rejects_negative_index(self):
                        with self.assertRaises(IndexError):
                            read_jsonl_line(self.path, -1)

                    def test_rejects_out_of_range_index(self):
                        with self.assertRaises(IndexError):
                            read_jsonl_line(self.path, 2)

                    def test_invalid_json_is_not_hidden(self):
                        self.path.write_text("not-json\\n", encoding="utf-8")
                        with self.assertRaises(json.JSONDecodeError):
                            read_jsonl_line(self.path, 0)


                if __name__ == "__main__":
                    unittest.main()
            """,
        ),
        PythonTask(
            task_id="python-03-load-case",
            title="Load a benchmark case by id",
            source_path="worker.py:load_case",
            description=(
                "load_case(cases, case_id) must return the first manifest object whose id exactly matches case_id. "
                "Raise KeyError with the missing id in the message when there is no match. Do not mutate cases."
            ),
            starter="""
                def load_case(cases: list[dict], case_id: str) -> dict | None:
                    for case in cases:
                        if case.get("id") == case_id:
                            return case
                    return None
            """,
            solution="""
                def load_case(cases: list[dict], case_id: str) -> dict:
                    for case in cases:
                        if case.get("id") == case_id:
                            return case
                    raise KeyError(f"Case {case_id!r} is missing from the manifest")
            """,
            tests="""
                import unittest

                from task import load_case


                class LoadCaseTests(unittest.TestCase):
                    def test_returns_exact_match(self):
                        cases = [{"id": "a", "value": 1}, {"id": "ab", "value": 2}]
                        self.assertIs(load_case(cases, "a"), cases[0])

                    def test_duplicate_returns_first(self):
                        cases = [{"id": "a", "value": 1}, {"id": "a", "value": 2}]
                        self.assertEqual(load_case(cases, "a")["value"], 1)

                    def test_missing_raises_key_error(self):
                        with self.assertRaisesRegex(KeyError, "missing"):
                            load_case([{"id": "present"}], "missing")

                    def test_input_is_not_mutated(self):
                        cases = [{"id": "a"}]
                        before = [dict(item) for item in cases]
                        load_case(cases, "a")
                        self.assertEqual(cases, before)


                if __name__ == "__main__":
                    unittest.main()
            """,
        ),
        PythonTask(
            task_id="python-04-build-prompt",
            title="Build a deterministic CSS prompt",
            source_path="worker.py:build_prompt",
            description=(
                "build_prompt(case, html) must include the CSS filename, visual description, and immutable HTML. "
                "It must explicitly instruct the model to return CSS only, avoid external assets, use an 800x600 "
                "viewport, and avoid overflow."
            ),
            starter="""
                def build_prompt(case: dict, html: str) -> str:
                    return f"Write CSS for this page:\\n{html}"
            """,
            solution='''
                def build_prompt(case: dict, html: str) -> str:
                    return f"""You are completing a deterministic CSS benchmark.

                Write the complete contents of `{case["css_filename"]}` for the immutable HTML
                below. Follow the visual specification exactly.

                Rules:
                - Return CSS only, without Markdown fences or commentary.
                - Do not change or repeat the HTML.
                - Do not use JavaScript, data URLs, external images, @import, or network fonts.
                - The viewport is exactly 800px by 600px with devicePixelRatio 1.
                - Avoid horizontal and vertical overflow.

                VISUAL SPECIFICATION
                {case["description"]}

                HTML
                {html}
                """
            ''',
            tests="""
                import unittest

                from task import build_prompt


                class BuildPromptTests(unittest.TestCase):
                    def test_contains_all_task_material(self):
                        prompt = build_prompt(
                            {"css_filename": "button.css", "description": "Make it blue."},
                            "<button>Go</button>",
                        )
                        self.assertIn("button.css", prompt)
                        self.assertIn("Make it blue.", prompt)
                        self.assertIn("<button>Go</button>", prompt)

                    def test_contains_determinism_rules(self):
                        prompt = build_prompt(
                            {"css_filename": "x.css", "description": "x"},
                            "<main></main>",
                        ).lower()
                        self.assertIn("css only", prompt)
                        self.assertIn("800px by 600px", prompt)
                        self.assertIn("external", prompt)
                        self.assertIn("overflow", prompt)


                if __name__ == "__main__":
                    unittest.main()
            """,
        ),
        PythonTask(
            task_id="python-05-extract-css",
            title="Extract CSS from a model response",
            source_path="worker.py:extract_css",
            description=(
                "extract_css(text) must accept plain CSS or the first ```css/``` fenced block, remove a leading "
                '"Here is...:" introduction, strip surrounding whitespace, reject an empty stylesheet with '
                "ValueError, and return exactly one trailing newline."
            ),
            starter="""
                def extract_css(text: str) -> str:
                    return text
            """,
            solution=r"""
                import re


                def extract_css(text: str) -> str:
                    fenced = re.search(r"```(?:css)?\s*(.*?)```", text, flags=re.I | re.S)
                    if fenced:
                        text = fenced.group(1)
                    text = re.sub(r"^\s*(?:Here(?:'s| is).*?:)\s*", "", text, flags=re.I)
                    css = text.strip()
                    if not css:
                        raise ValueError("Model returned an empty stylesheet")
                    return css + "\n"
            """,
            tests=r"""
                import unittest

                from task import extract_css


                class ExtractCssTests(unittest.TestCase):
                    def test_plain_css(self):
                        self.assertEqual(extract_css("  body { color: red; }  "), "body { color: red; }\n")

                    def test_fenced_css(self):
                        response = "comment\n```CSS\nbody { margin: 0; }\n```\nmore"
                        self.assertEqual(extract_css(response), "body { margin: 0; }\n")

                    def test_leading_introduction(self):
                        self.assertEqual(extract_css("Here's the CSS: body{}"), "body{}\n")

                    def test_empty_is_rejected(self):
                        with self.assertRaises(ValueError):
                            extract_css("```css\n \n```")


                if __name__ == "__main__":
                    unittest.main()
            """,
        ),
        PythonTask(
            task_id="python-06-inline-css",
            title="Inline exactly one stylesheet",
            source_path="grader.py:html_with_inline_css",
            description=(
                "html_with_inline_css(html, css) must replace exactly one link element whose rel is stylesheet "
                "with a style element containing css. Support single or double quotes and an optional self-closing "
                "slash. Raise ValueError unless exactly one stylesheet link was replaced."
            ),
            starter="""
                def html_with_inline_css(html: str, css: str) -> str:
                    return html + f"<style>{css}</style>"
            """,
            solution=r"""
                import re


                def html_with_inline_css(html: str, css: str) -> str:
                    pattern = r'<link\s+rel=["\']stylesheet["\']\s+href=["\'][^"\']+["\']\s*/?>'
                    rendered, replacements = re.subn(
                        pattern,
                        "<style>\n" + css + "\n</style>",
                        html,
                        flags=re.I,
                    )
                    if replacements != 1:
                        raise ValueError("Fixture must contain exactly one stylesheet link")
                    return rendered
            """,
            tests=r"""
                import unittest

                from task import html_with_inline_css


                class InlineCssTests(unittest.TestCase):
                    def test_replaces_double_quoted_link(self):
                        html = '<head><link rel="stylesheet" href="x.css"></head>'
                        rendered = html_with_inline_css(html, "body{}")
                        self.assertNotIn("<link", rendered)
                        self.assertIn("<style>\nbody{}\n</style>", rendered)

                    def test_replaces_single_quoted_self_closing_link(self):
                        html = "<link rel='stylesheet' href='x.css' />"
                        self.assertIn("<style>", html_with_inline_css(html, "a{}"))

                    def test_missing_link_is_rejected(self):
                        with self.assertRaises(ValueError):
                            html_with_inline_css("<main></main>", "a{}")

                    def test_multiple_links_are_rejected(self):
                        html = (
                            '<link rel="stylesheet" href="a.css">'
                            '<link rel="stylesheet" href="b.css">'
                        )
                        with self.assertRaises(ValueError):
                            html_with_inline_css(html, "a{}")


                if __name__ == "__main__":
                    unittest.main()
            """,
        ),
        PythonTask(
            task_id="python-07-atomic-write",
            title="Write result files atomically",
            source_path="grader.py:atomic_write",
            description=(
                "atomic_write(path, text) must create missing parent directories, write UTF-8 text to a temporary "
                "sibling, and atomically replace the destination with os.replace. It must leave no temporary file."
            ),
            starter="""
                from pathlib import Path


                def atomic_write(path: Path, text: str) -> None:
                    path.write_text(text)
            """,
            solution="""
                import os
                from pathlib import Path


                def atomic_write(path: Path, text: str) -> None:
                    path.parent.mkdir(parents=True, exist_ok=True)
                    temporary = path.with_name(f".{path.name}.{os.getpid()}.tmp")
                    temporary.write_text(text, encoding="utf-8")
                    os.replace(temporary, path)
            """,
            tests="""
                import tempfile
                import unittest
                from pathlib import Path

                from task import atomic_write


                class AtomicWriteTests(unittest.TestCase):
                    def test_creates_parents_and_writes_utf8(self):
                        with tempfile.TemporaryDirectory() as tmp:
                            path = Path(tmp) / "nested" / "result.txt"
                            atomic_write(path, "café")
                            self.assertEqual(path.read_text(encoding="utf-8"), "café")

                    def test_replaces_existing_content(self):
                        with tempfile.TemporaryDirectory() as tmp:
                            path = Path(tmp) / "result.txt"
                            path.write_text("old", encoding="utf-8")
                            atomic_write(path, "new")
                            self.assertEqual(path.read_text(encoding="utf-8"), "new")

                    def test_leaves_no_temp_file(self):
                        with tempfile.TemporaryDirectory() as tmp:
                            path = Path(tmp) / "result.txt"
                            atomic_write(path, "done")
                            self.assertEqual([item.name for item in Path(tmp).iterdir()], ["result.txt"])


                if __name__ == "__main__":
                    unittest.main()
            """,
        ),
        PythonTask(
            task_id="python-08-load-entries",
            title="Load non-empty benchmark entries",
            source_path="grader.py:load_entries",
            description=(
                "load_entries(path) must parse each non-empty UTF-8 JSONL line in order and return a list of "
                "dictionaries. Ignore whitespace-only lines, return [] for an empty file, and do not suppress "
                "JSON decoding errors."
            ),
            starter="""
                import json
                from pathlib import Path


                def load_entries(path: Path) -> list[dict]:
                    return [json.loads(path.read_text(encoding="utf-8"))]
            """,
            solution="""
                import json
                from pathlib import Path


                def load_entries(path: Path) -> list[dict]:
                    return [
                        json.loads(line)
                        for line in path.read_text(encoding="utf-8").splitlines()
                        if line.strip()
                    ]
            """,
            tests="""
                import json
                import tempfile
                import unittest
                from pathlib import Path

                from task import load_entries


                class LoadEntriesTests(unittest.TestCase):
                    def test_loads_records_and_skips_blanks(self):
                        with tempfile.TemporaryDirectory() as tmp:
                            path = Path(tmp) / "data.jsonl"
                            path.write_text('{"id": 1}\\n  \\n{"id": 2}\\n', encoding="utf-8")
                            self.assertEqual(load_entries(path), [{"id": 1}, {"id": 2}])

                    def test_empty_file(self):
                        with tempfile.TemporaryDirectory() as tmp:
                            path = Path(tmp) / "data.jsonl"
                            path.write_text("", encoding="utf-8")
                            self.assertEqual(load_entries(path), [])

                    def test_invalid_json_raises(self):
                        with tempfile.TemporaryDirectory() as tmp:
                            path = Path(tmp) / "data.jsonl"
                            path.write_text("nope\\n", encoding="utf-8")
                            with self.assertRaises(json.JSONDecodeError):
                                load_entries(path)


                if __name__ == "__main__":
                    unittest.main()
            """,
        ),
        PythonTask(
            task_id="python-09-normalize-weights",
            title="Validate and normalize visual weights",
            source_path="visual_metrics.py:_normalized_weights",
            description=(
                "normalized_weights(defaults, overrides=None) must copy defaults, reject unknown override names, "
                "reject negative values, require a positive total, and return weights normalized to sum to 1. "
                "Do not mutate either input mapping."
            ),
            starter="""
                def normalized_weights(defaults: dict[str, float], overrides=None) -> dict[str, float]:
                    defaults.update(overrides or {})
                    return defaults
            """,
            solution="""
                def normalized_weights(
                    defaults: dict[str, float],
                    overrides: dict[str, float] | None = None,
                ) -> dict[str, float]:
                    weights = {name: float(value) for name, value in defaults.items()}
                    if overrides:
                        unknown = set(overrides) - set(weights)
                        if unknown:
                            raise ValueError(f"Unknown visual metric weights: {sorted(unknown)}")
                        weights.update({name: float(value) for name, value in overrides.items()})
                    if any(value < 0 for value in weights.values()):
                        raise ValueError("Visual metric weights must be non-negative")
                    total = sum(weights.values())
                    if total <= 0:
                        raise ValueError("At least one visual metric weight must be positive")
                    return {name: value / total for name, value in weights.items()}
            """,
            tests="""
                import unittest

                from task import normalized_weights


                class NormalizeWeightsTests(unittest.TestCase):
                    def test_normalizes_and_applies_override(self):
                        result = normalized_weights({"a": 1, "b": 1}, {"a": 3})
                        self.assertAlmostEqual(result["a"], 0.75)
                        self.assertAlmostEqual(result["b"], 0.25)
                        self.assertAlmostEqual(sum(result.values()), 1.0)

                    def test_rejects_unknown(self):
                        with self.assertRaises(ValueError):
                            normalized_weights({"a": 1}, {"b": 1})

                    def test_rejects_negative_and_zero_total(self):
                        with self.assertRaises(ValueError):
                            normalized_weights({"a": -1})
                        with self.assertRaises(ValueError):
                            normalized_weights({"a": 0, "b": 0})

                    def test_does_not_mutate_inputs(self):
                        defaults = {"a": 1, "b": 2}
                        overrides = {"a": 2}
                        normalized_weights(defaults, overrides)
                        self.assertEqual(defaults, {"a": 1, "b": 2})
                        self.assertEqual(overrides, {"a": 2})


                if __name__ == "__main__":
                    unittest.main()
            """,
        ),
        PythonTask(
            task_id="python-10-retry-delays",
            title="Calculate bounded retry delays",
            source_path="worker.py:call_model retry loop",
            description=(
                "retry_delays(max_retries, base_seconds=5, cap_seconds=60) returns the delays used between attempts. "
                "There is no delay after the final attempt, so return max_retries-1 values. Use exponential backoff "
                "base_seconds * 2**attempt_index capped at cap_seconds. Reject max_retries < 1 and non-positive base/cap."
            ),
            starter="""
                def retry_delays(max_retries: int, base_seconds: int = 5, cap_seconds: int = 60) -> list[int]:
                    return [base_seconds] * max_retries
            """,
            solution="""
                def retry_delays(
                    max_retries: int,
                    base_seconds: int = 5,
                    cap_seconds: int = 60,
                ) -> list[int]:
                    if max_retries < 1:
                        raise ValueError("max_retries must be at least 1")
                    if base_seconds <= 0 or cap_seconds <= 0:
                        raise ValueError("base_seconds and cap_seconds must be positive")
                    return [
                        min(cap_seconds, base_seconds * (2**attempt_index))
                        for attempt_index in range(max_retries - 1)
                    ]
            """,
            tests="""
                import unittest

                from task import retry_delays


                class RetryDelayTests(unittest.TestCase):
                    def test_default_backoff(self):
                        self.assertEqual(retry_delays(5), [5, 10, 20, 40])

                    def test_cap_is_applied(self):
                        self.assertEqual(retry_delays(6, base_seconds=10, cap_seconds=25), [10, 20, 25, 25, 25])

                    def test_one_attempt_has_no_delay(self):
                        self.assertEqual(retry_delays(1), [])

                    def test_invalid_arguments(self):
                        for args in [(0, 5, 60), (2, 0, 60), (2, 5, 0)]:
                            with self.subTest(args=args), self.assertRaises(ValueError):
                                retry_delays(*args)


                if __name__ == "__main__":
                    unittest.main()
            """,
        ),
    ]


REACT_COMPONENTS = {
    "01-primary-button": """
        export default function App() {
          return (
            <main className="stage">
              <button className="primary-button" type="button">Create account</button>
            </main>
          );
        }
    """,
    "02-text-input": """
        export default function App() {
          return (
            <main className="stage">
              <div className="field">
                <label htmlFor="email">Email address</label>
                <input id="email" type="email" placeholder="you@example.com" />
                <p>We will never share your email.</p>
              </div>
            </main>
          );
        }
    """,
    "03-profile-card": """
        export default function App() {
          return (
            <main className="stage">
              <article className="profile-card">
                <div className="avatar" aria-hidden="true">ML</div>
                <h1>Maya Lin</h1>
                <p>Product Designer</p>
                <button type="button">Follow</button>
              </article>
            </main>
          );
        }
    """,
    "04-header-nav": """
        export default function App() {
          return (
            <header className="site-header">
              <a className="brand" href="#">Northstar</a>
              <nav aria-label="Primary">
                <a className="active" href="#">Product</a>
                <a href="#">Solutions</a>
                <a href="#">Pricing</a>
              </nav>
              <button type="button">Get started</button>
            </header>
          );
        }
    """,
    "05-sidebar-nav": """
        export default function App() {
          return (
            <aside className="sidebar">
              <div className="logo">Orbit</div>
              <nav aria-label="Workspace">
                <a className="active" href="#">Overview</a>
                <a href="#">Projects</a>
                <a href="#">Calendar</a>
                <a href="#">Settings</a>
              </nav>
              <div className="user">
                <span className="avatar">AR</span>
                <span><strong>Alex Reed</strong><small>Admin</small></span>
              </div>
            </aside>
          );
        }
    """,
    "06-feature-grid": """
        const features = [
          ["⚡", "Fast setup", "Launch your workspace in just a few minutes."],
          ["✓", "Clear tasks", "Keep ownership and priorities visible."],
          ["↗", "Live reports", "Understand progress with simple reporting."],
        ];

        export default function App() {
          return (
            <main className="features">
              <h1>Everything you need</h1>
              <p className="subtitle">Simple tools for productive teams.</p>
              <section className="card-grid">
                {features.map(([icon, title, description]) => (
                  <article className="card" key={title}>
                    <div className="icon">{icon}</div>
                    <h2>{title}</h2>
                    <p>{description}</p>
                  </article>
                ))}
              </section>
            </main>
          );
        }
    """,
    "07-sign-in": """
        export default function App() {
          return (
            <main className="stage">
              <section className="panel">
                <h1>Welcome back</h1>
                <p className="subtitle">Sign in to continue to your account.</p>
                <form>
                  <div className="form-group">
                    <label htmlFor="email">Email</label>
                    <input id="email" type="email" placeholder="you@example.com" />
                  </div>
                  <div className="form-group">
                    <label htmlFor="password">Password</label>
                    <input id="password" type="password" placeholder="••••••••" />
                  </div>
                  <button type="submit">Sign in</button>
                </form>
                <p className="help">Need an account? <a href="#">Create one</a></p>
              </section>
            </main>
          );
        }
    """,
    "08-hero": """
        export default function App() {
          return (
            <main className="hero">
              <div className="pill">NEW RELEASE</div>
              <h1>Build better products, together.</h1>
              <p>Plan, create, and ship meaningful work with one calm workspace for your entire team.</p>
              <div className="actions">
                <button className="primary" type="button">Start for free</button>
                <button className="secondary" type="button">View demo</button>
              </div>
            </main>
          );
        }
    """,
    "09-footer": """
        export default function App() {
          return (
            <footer>
              <div className="top-row">
                <a className="brand" href="#">Acme</a>
                <nav aria-label="Footer">
                  <a href="#">Product</a>
                  <a href="#">Company</a>
                  <a href="#">Resources</a>
                  <a href="#">Contact</a>
                </nav>
              </div>
              <div className="divider" />
              <div className="bottom-row">
                <small>© 2026 Acme, Inc. All rights reserved.</small>
                <div className="socials">
                  <a href="#" aria-label="X">X</a>
                  <a href="#" aria-label="LinkedIn">in</a>
                  <a href="#" aria-label="GitHub">gh</a>
                </div>
              </div>
            </footer>
          );
        }
    """,
    "10-dashboard": """
        const stats = [
          ["Revenue", "$24,800", "+12.5%"],
          ["Orders", "1,429", "+8.2%"],
          ["Customers", "892", "+5.1%"],
        ];

        export default function App() {
          return (
            <>
              <aside className="sidebar">
                <div className="logo">Pulse</div>
                <nav aria-label="Dashboard">
                  <a className="active" href="#">Overview</a>
                  <a href="#">Analytics</a>
                  <a href="#">Customers</a>
                  <a href="#">Settings</a>
                </nav>
              </aside>
              <main>
                <header>
                  <div>
                    <h1>Overview</h1>
                    <p>Here is what is happening today.</p>
                  </div>
                  <div className="avatar">DC</div>
                </header>
                <section className="stats" aria-label="Statistics">
                  {stats.map(([label, value, change]) => (
                    <article key={label}><span>{label}</span><strong>{value}</strong><small>{change}</small></article>
                  ))}
                </section>
                <section className="activity">
                  <h2>Weekly activity</h2>
                  {[88, 72, 60, 44].map((width) => (
                    <div className="bar" key={width}><i style={{ width: `${width}%` }} /></div>
                  ))}
                </section>
              </main>
            </>
          );
        }
    """,
}

REACT_MAIN = """
    import { StrictMode } from "react";
    import { createRoot } from "react-dom/client";
    import App from "./App.jsx";
    import "./styles.css";

    createRoot(document.getElementById("root")).render(
      <StrictMode>
        <App />
      </StrictMode>,
    );
"""

REACT_INDEX = """
    <!doctype html>
    <html lang="en">
      <head>
        <meta charset="UTF-8" />
        <meta name="viewport" content="width=device-width, initial-scale=1.0" />
        <title>Uni-Agent React task</title>
      </head>
      <body>
        <div id="root"></div>
        <script type="module" src="/src/main.jsx"></script>
      </body>
    </html>
"""

REACT_VITE_CONFIG = """
    import { defineConfig } from "vite";
    import react from "@vitejs/plugin-react";

    export default defineConfig({
      plugins: [react()],
    });
"""

REACT_PACKAGE = {
    "name": "uni-agent-react-task",
    "private": True,
    "version": "1.0.0",
    "type": "module",
    "scripts": {"dev": "vite"},
    "dependencies": {
        "vite": "7.0.6",
        "react": "19.1.0",
        "react-dom": "19.1.0",
        "@vitejs/plugin-react": "4.6.0",
    },
}

PYTHON_REWARD_SCRIPT = """#!/usr/bin/env bash
set +e
mkdir -p /logs/verifier
PYTHONPATH=/workspace python3 /tests/test_task.py
status=$?
if [ "$status" -eq 0 ]; then
  printf '{"reward": 1.0}\\n' > /logs/verifier/reward.json
else
  printf '{"reward": 0.0}\\n' > /logs/verifier/reward.json
fi
exit 0
"""

REACT_REWARD_SCRIPT = """#!/usr/bin/env bash
set +e
mkdir -p /logs/verifier
python3 /tests/grade_react.py \
  --workspace /workspace \
  --reference /tests/reference.png \
  --screenshot /logs/verifier/candidate.png
exit 0
"""


def clean_text(value: str) -> str:
    return dedent(value).strip() + "\n"


def write_text(path: Path, value: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(clean_text(value), encoding="utf-8")


def write_raw_text(path: Path, value: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(value, encoding="utf-8")


def tar_gz_bytes(source_dir: Path) -> bytes:
    """Return a deterministic archive containing source_dir's children."""
    buffer = BytesIO()
    with gzip.GzipFile(fileobj=buffer, mode="wb", mtime=0) as gzip_file:
        with tarfile.open(fileobj=gzip_file, mode="w", format=tarfile.PAX_FORMAT) as archive:
            for path in sorted(source_dir.rglob("*")):
                arcname = path.relative_to(source_dir).as_posix()
                info = archive.gettarinfo(str(path), arcname=arcname)
                info.uid = 0
                info.gid = 0
                info.uname = ""
                info.gname = ""
                info.mtime = 0
                if info.isfile():
                    with path.open("rb") as file_handle:
                        archive.addfile(info, file_handle)
                else:
                    archive.addfile(info)
    return buffer.getvalue()


def source_revision(css_root: Path) -> str | None:
    try:
        return subprocess.run(
            ["git", "-C", str(css_root), "rev-parse", "HEAD"],
            check=True,
            capture_output=True,
            text=True,
        ).stdout.strip()
    except (OSError, subprocess.CalledProcessError):
        return None


def build_python_assets(output_dir: Path) -> list[dict[str, Any]]:
    task_records: list[dict[str, Any]] = []
    for task in python_tasks():
        starter_dir = output_dir / "starter_tasks" / task.task_id
        grading_dir = output_dir / "grading" / task.task_id

        write_text(starter_dir / "task.py", task.starter)
        write_raw_text(starter_dir / "README.md", f"# {task.title}\n\n{task.description}\n")

        write_text(grading_dir / "tests" / "test_task.py", task.tests)
        write_raw_text(grading_dir / "tests" / "test.sh", PYTHON_REWARD_SCRIPT)
        write_text(grading_dir / "solution" / "task.py", task.solution)
        write_raw_text(
            grading_dir / "solution" / "solve.sh",
            "#!/usr/bin/env bash\nset -euo pipefail\ncp /solution/task.py /workspace/task.py\n",
        )

        task_records.append(
            {
                "task_id": task.task_id,
                "title": task.title,
                "task_type": "python",
                "description": task.description,
                "source_path": task.source_path,
                "starter_dir": starter_dir,
                "grading_dir": grading_dir,
            }
        )
    return task_records


def build_react_assets(css_root: Path, output_dir: Path) -> list[dict[str, Any]]:
    benchmark_root = css_root / "benchmark"
    cases = json.loads((benchmark_root / "cases.json").read_text(encoding="utf-8"))
    if len(cases) != 10:
        raise ValueError(f"Expected exactly 10 CSS cases, found {len(cases)}")
    if set(REACT_COMPONENTS) != {case["id"] for case in cases}:
        raise ValueError("React component mapping does not match cases.json")

    visual_metrics_source = css_root / "visual_metrics.py"
    if not visual_metrics_source.is_file():
        raise FileNotFoundError(f"Missing source visual metrics: {visual_metrics_source}")

    task_records: list[dict[str, Any]] = []
    for index, case in enumerate(cases, start=1):
        task_id = f"react-{index:02d}-{case['id'].split('-', 1)[1]}"
        source_case_dir = benchmark_root / "cases" / case["id"]
        starter_dir = output_dir / "starter_tasks" / task_id
        grading_dir = output_dir / "grading" / task_id
        (grading_dir / "tests").mkdir(parents=True, exist_ok=True)
        (grading_dir / "solution").mkdir(parents=True, exist_ok=True)

        write_raw_text(starter_dir / "package.json", json.dumps(REACT_PACKAGE, indent=2) + "\n")
        write_text(starter_dir / "index.html", REACT_INDEX)
        write_text(starter_dir / "vite.config.js", REACT_VITE_CONFIG)
        write_text(starter_dir / "src" / "main.jsx", REACT_MAIN)
        write_text(starter_dir / "src" / "App.jsx", REACT_COMPONENTS[case["id"]])
        write_raw_text(
            starter_dir / "src" / "styles.css",
            "/* Implement the visual specification in README.md. */\n#root { display: contents; }\n",
        )
        shutil.copy2(source_case_dir / "reference.png", starter_dir / "reference.png")
        write_raw_text(
            starter_dir / "README.md",
            f"# {case['title']}\n\n{case['description']}\n\n"
            "Implement `src/styles.css`. You may adjust `src/App.jsx` only if needed for semantic React markup.\n",
        )

        shutil.copy2(source_case_dir / "reference.png", grading_dir / "tests" / "reference.png")
        shutil.copy2(visual_metrics_source, grading_dir / "tests" / "visual_metrics.py")
        shutil.copy2(EXAMPLE_ROOT / "react_visual_reward.py", grading_dir / "tests" / "grade_react.py")
        write_raw_text(grading_dir / "tests" / "test.sh", REACT_REWARD_SCRIPT)

        gold_css = (source_case_dir / case["css_filename"]).read_text(encoding="utf-8")
        write_raw_text(
            grading_dir / "solution" / "styles.css",
            "#root { display: contents; }\n\n" + gold_css,
        )
        write_raw_text(
            grading_dir / "solution" / "solve.sh",
            "#!/usr/bin/env bash\nset -euo pipefail\ncp /solution/styles.css /workspace/src/styles.css\n",
        )

        task_records.append(
            {
                "task_id": task_id,
                "title": case["title"],
                "task_type": "react",
                "description": case["description"],
                "source_path": f"benchmark/cases/{case['id']}",
                "starter_dir": starter_dir,
                "grading_dir": grading_dir,
            }
        )
    return task_records


def sample_from_record(record: dict[str, Any], source_root: Path, revision: str | None) -> dict[str, Any]:
    task_id = record["task_id"]
    task_type = record["task_type"]
    grading_dir = record["grading_dir"]
    prompt_template = PYTHON_USER_PROMPT if task_type == "python" else REACT_USER_PROMPT

    setup_commands = [
        "mkdir -p /workspace",
        f"cp -a /opt/tasks/{task_id}/. /workspace/",
        "cd /workspace",
    ]
    if task_type == "react":
        setup_commands.insert(2, "ln -sfn /opt/react-runtime/node_modules /workspace/node_modules")

    metadata = {
        "task_id": task_id,
        "title": record["title"],
        "task_type": task_type,
        "source_path": record["source_path"],
        "source_revision": revision or "",
        "workdir": "/workspace",
        "task_config": {
            "agent": {"timeout_sec": 120.0},
            "verifier": {"timeout_sec": 120.0},
        },
        "solution_archive": tar_gz_bytes(grading_dir / "solution"),
        "tests_archive": tar_gz_bytes(grading_dir / "tests"),
        "solve_relpath": "solve.sh",
        "test_relpath": "test.sh",
    }

    return {
        "prompt": [
            {"role": "system", "content": SYSTEM_PROMPT},
            {
                "role": "user",
                "content": prompt_template.format(description=record["description"]),
            },
        ],
        "agent_name": "swe_agent",
        "extra_info": {
            "task_id": task_id,
            "task_type": task_type,
            "data_source": "cssbenchmark-aks-mixed",
            "source_root": str(source_root),
            "source_path": record["source_path"],
            "tools_kwargs": {
                "env": {
                    "post_setup_cmd": " && ".join(setup_commands),
                },
                "reward": {
                    "name": "terminal_bench_v2",
                    "eval_timeout": 120.0,
                    "metadata": metadata,
                },
            },
        },
    }


def preview_record(sample: dict[str, Any], split: str) -> dict[str, Any]:
    extra_info = sample["extra_info"]
    reward_metadata = extra_info["tools_kwargs"]["reward"]["metadata"]
    return {
        "task_id": extra_info["task_id"],
        "task_type": extra_info["task_type"],
        "title": reward_metadata["title"],
        "split": split,
        "agent_name": sample["agent_name"],
        "source_path": extra_info["source_path"],
        "prompt": sample["prompt"],
        "solution_archive_bytes": len(reward_metadata["solution_archive"]),
        "tests_archive_bytes": len(reward_metadata["tests_archive"]),
    }


def split_samples(samples: list[dict[str, Any]]) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    python_samples = [sample for sample in samples if sample["extra_info"]["task_type"] == "python"]
    react_samples = [sample for sample in samples if sample["extra_info"]["task_type"] == "react"]
    if len(python_samples) != 10 or len(react_samples) != 10:
        raise ValueError("Expected 10 Python and 10 React samples")
    train = python_samples[:8] + react_samples[:8]
    test = python_samples[8:] + react_samples[8:]
    return train, test


def write_parquet(samples: list[dict[str, Any]], path: Path) -> None:
    try:
        from datasets import Dataset
    except ImportError as exc:
        raise RuntimeError(
            "Parquet generation requires `datasets`. Install it with `pip install datasets` "
            "or pass --skip-parquet to generate fixtures and JSONL previews only."
        ) from exc
    path.parent.mkdir(parents=True, exist_ok=True)
    Dataset.from_list(samples).to_parquet(str(path))


def generate(css_root: Path, output_dir: Path, *, skip_parquet: bool = False) -> dict[str, Any]:
    css_root = css_root.expanduser().resolve()
    output_dir = output_dir.expanduser().resolve()
    if not (css_root / "benchmark" / "cases.json").is_file():
        raise FileNotFoundError(f"Not a cssbenchmark-aks checkout: {css_root}")

    if output_dir.exists():
        shutil.rmtree(output_dir)
    output_dir.mkdir(parents=True)

    revision = source_revision(css_root)
    records = build_python_assets(output_dir)
    records.extend(build_react_assets(css_root, output_dir))
    samples = [sample_from_record(record, css_root, revision) for record in records]
    train, test = split_samples(samples)

    data_dir = output_dir / "data"
    data_dir.mkdir(parents=True, exist_ok=True)
    preview_rows = [
        *(preview_record(sample, "train") for sample in train),
        *(preview_record(sample, "test") for sample in test),
    ]
    write_raw_text(
        data_dir / "tasks.jsonl",
        "".join(json.dumps(row, ensure_ascii=False) + "\n" for row in preview_rows),
    )

    manifest = {
        "source_root": str(css_root),
        "source_revision": revision,
        "task_count": len(samples),
        "python_task_count": sum(row["task_type"] == "python" for row in preview_rows),
        "react_task_count": sum(row["task_type"] == "react" for row in preview_rows),
        "train_count": len(train),
        "test_count": len(test),
        "container_image": "uni-agent-mixed-code-react:latest",
        "tasks": preview_rows,
    }
    write_raw_text(output_dir / "manifest.json", json.dumps(manifest, indent=2, ensure_ascii=False) + "\n")

    if not skip_parquet:
        write_parquet(samples, data_dir / "all.parquet")
        write_parquet(train, data_dir / "train.parquet")
        write_parquet(test, data_dir / "test.parquet")

    return manifest


def default_css_root() -> Path:
    for candidate in CSS_BENCHMARK_CANDIDATES:
        if candidate.exists():
            return candidate
    return CSS_BENCHMARK_CANDIDATES[0]


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--css-benchmark-root", type=Path, default=default_css_root())
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT_DIR)
    parser.add_argument("--skip-parquet", action="store_true")
    args = parser.parse_args()

    manifest = generate(
        args.css_benchmark_root,
        args.output_dir,
        skip_parquet=args.skip_parquet,
    )
    print(
        "Generated "
        f"{manifest['task_count']} tasks "
        f"({manifest['python_task_count']} Python, {manifest['react_task_count']} React) "
        f"under {args.output_dir.expanduser().resolve()}",
        flush=True,
    )


if __name__ == "__main__":
    main()
