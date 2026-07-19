import json
import tempfile
import unittest
from pathlib import Path

from task import load_entries


class LoadEntriesTests(unittest.TestCase):
    def test_loads_records_and_skips_blanks(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "data.jsonl"
            path.write_text('{"id": 1}\n  \n{"id": 2}\n', encoding="utf-8")
            self.assertEqual(load_entries(path), [{"id": 1}, {"id": 2}])

    def test_empty_file(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "data.jsonl"
            path.write_text("", encoding="utf-8")
            self.assertEqual(load_entries(path), [])

    def test_invalid_json_raises(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "data.jsonl"
            path.write_text("nope\n", encoding="utf-8")
            with self.assertRaises(json.JSONDecodeError):
                load_entries(path)


if __name__ == "__main__":
    unittest.main()
