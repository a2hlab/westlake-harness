import copy
import importlib.util
from pathlib import Path
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[5]
SOURCE = ROOT / "sources/api-implementations/shared-native-production"
sys.path.insert(0, str(SOURCE / "revisions/archive-merge-r2"))
from restore_provider_inputs_r2 import verify_external_overlap, verify_restored_duplicate


class ExactMergeTests(unittest.TestCase):
    def record(self):
        return {"target": "platform-link/file", "sha256": "0" * 64, "metadata": {"type": "0", "mode": 0o644, "uid": 501, "gid": 20, "mtime": 123, "size": 4, "linkname": ""}}

    def test_exact_duplicate_permitted(self):
        record = self.record()
        rows = verify_external_overlap({record["target"]: record}, {record["target"]: copy.deepcopy(record)})
        self.assertEqual(rows[0]["decision"], "SKIP_EXACT_IDENTICAL")

    def test_each_metadata_difference_rejected(self):
        for key, value in [("type", "2"), ("mode", 0o755), ("uid", 0), ("gid", 0), ("mtime", 124), ("size", 5), ("linkname", "different")]:
            with self.subTest(key=key):
                original = self.record()
                changed = copy.deepcopy(original)
                changed["metadata"][key] = value
                with self.assertRaisesRegex(ValueError, "DIFFERENT_EXTERNAL"):
                    verify_external_overlap({original["target"]: original}, {changed["target"]: changed})

    def test_changed_bytes_rejected(self):
        original = self.record()
        changed = copy.deepcopy(original)
        changed["sha256"] = "1" * 64
        with self.assertRaisesRegex(ValueError, "DIFFERENT_EXTERNAL"):
            verify_external_overlap({original["target"]: original}, {changed["target"]: changed})

    def test_unknown_new_target_rejected(self):
        record = self.record()
        with self.assertRaisesRegex(ValueError, "UNDECLARED_NEW"):
            verify_external_overlap({}, {record["target"]: record})

    def test_restored_file_tamper_rejected(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "platform-link").mkdir()
            (root / "platform-link/file").write_bytes(b"bad!")
            with self.assertRaisesRegex(ValueError, "SHA_MISMATCH"):
                verify_restored_duplicate(root, self.record())

    def test_restored_symlink_rejected(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "platform-link").mkdir()
            (root / "platform-link/file").symlink_to("missing")
            with self.assertRaisesRegex(ValueError, "SYMLINK"):
                verify_restored_duplicate(root, self.record())


if __name__ == "__main__":
    unittest.main()
