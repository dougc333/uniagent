from __future__ import annotations

import json
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import generate_dataset


class MixedDatasetGeneratorTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.css_root = generate_dataset.default_css_root()

    def test_defines_ten_python_tasks(self):
        tasks = generate_dataset.python_tasks()
        self.assertEqual(len(tasks), 10)
        self.assertEqual(len({task.task_id for task in tasks}), 10)
        self.assertTrue(all(task.source_path for task in tasks))

    def test_react_mapping_matches_source_cases(self):
        cases_path = self.css_root / "benchmark" / "cases.json"
        cases = json.loads(cases_path.read_text(encoding="utf-8"))
        self.assertEqual(set(generate_dataset.REACT_COMPONENTS), {case["id"] for case in cases})

    def test_deterministic_archives(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "a.txt").write_text("hello", encoding="utf-8")
            first = generate_dataset.tar_gz_bytes(root)
            second = generate_dataset.tar_gz_bytes(root)
            self.assertEqual(first, second)

    def test_generates_balanced_assets_without_parquet(self):
        with tempfile.TemporaryDirectory() as tmp:
            output = Path(tmp) / "generated"
            manifest = generate_dataset.generate(self.css_root, output, skip_parquet=True)
            self.assertEqual(manifest["task_count"], 20)
            self.assertEqual(manifest["python_task_count"], 10)
            self.assertEqual(manifest["react_task_count"], 10)
            self.assertEqual(manifest["train_count"], 16)
            self.assertEqual(manifest["test_count"], 4)
            self.assertEqual(len(list((output / "starter_tasks").iterdir())), 20)
            self.assertEqual(len(list((output / "grading").iterdir())), 20)
            self.assertEqual(len((output / "data" / "tasks.jsonl").read_text().splitlines()), 20)


if __name__ == "__main__":
    unittest.main()
