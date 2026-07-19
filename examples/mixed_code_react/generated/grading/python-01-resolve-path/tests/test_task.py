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
