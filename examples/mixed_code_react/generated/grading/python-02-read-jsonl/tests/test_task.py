import json
import tempfile
import unittest
from pathlib import Path

from task import read_jsonl_line


class ReadJsonlTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.path = Path(self.tmp.name) / "data.jsonl"
        self.path.write_text('{"id": 1}\n\n{"id": 2}\n', encoding="utf-8")

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
        self.path.write_text("not-json\n", encoding="utf-8")
        with self.assertRaises(json.JSONDecodeError):
            read_jsonl_line(self.path, 0)


if __name__ == "__main__":
    unittest.main()
