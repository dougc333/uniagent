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
