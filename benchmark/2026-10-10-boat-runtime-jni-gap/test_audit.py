import json
import subprocess
import tempfile
import unittest
from pathlib import Path

import audit


class ExactArtifactsTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        scanner = audit.load_module("test_jni_scan", audit.WORKSPACES / "westlake-harness/benchmark/2026-09-29-static-wall-prediction/scan_jni.py")
        records = json.loads((audit.HERE / "results.json").read_text())["artifacts"]
        cls.elfs = {tag: scanner.ELF(Path(row["path"].replace("$WORKSPACES", str(audit.WORKSPACES)))) for tag, row in records.items()}
        for tag, record in records.items():
            if audit.digest(cls.elfs[tag].path) != audit.EXPECTED[tag]:
                raise ValueError("test input SHA differs")

    def test_sqlite_dispatch_points_to_noop_only_in_boat(self):
        for tag, elf in self.elfs.items():
            rows = [row for row in audit.dispatch(elf) if "SQLite" in row["registrar"] or "CursorWindow" in row["registrar"]]
            self.assertEqual(len(rows), 4)
            self.assertEqual(sum(row["body_prefix"] == "e0031f2ac0035fd6" for row in rows), 4 if tag == "boat" else 0)

    def test_registration_entry_is_not_jni_onload(self):
        for elf in self.elfs.values():
            self.assertNotIn("JNI_OnLoad", elf.exports)
            self.assertIn("_ZN7android14AndroidRuntime8startRegEP7_JNIEnv", elf.exports)

    def test_sqlite_native_open_absent_from_boat(self):
        for tag, elf in self.elfs.items():
            rows = [row for row in elf.tables() if row["method"] == "nativeOpen" and row["signature"] == "(Ljava/lang/String;ILjava/lang/String;ZZII)J"]
            self.assertEqual(len(rows), 1 if tag == "u13" else 0)

    def test_sqlite_translation_units_not_linked_in_boat(self):
        for tag, elf in self.elfs.items():
            files = {symbol["name"] for symbol in elf.symbols if symbol["type"] == 4}
            self.assertEqual("android_database_SQLiteConnection.cpp" in files, tag == "u13")
            self.assertEqual("sqlite3.c" in files, tag == "u13")

    def test_wrong_artifact_rejected(self):
        with tempfile.TemporaryDirectory() as directory:
            wrong = Path(directory) / "wrong.so"
            wrong.write_bytes(b"not the signed ELF")
            process = subprocess.run(["python3", str(audit.HERE / "audit.py"), "--u13", str(wrong)], capture_output=True, text=True)
            self.assertNotEqual(process.returncode, 0)
            self.assertIn("wrong artifact: u13", process.stderr)

    def test_assembled_libandroid_alias_and_patch(self):
        record = json.loads((audit.HERE / "libandroid-origin.json").read_text())
        self.assertTrue(record["alias_identical"])
        self.assertEqual(record["changed_bytes"], 49)
        self.assertEqual(record["changed_executable_bytes"], 47)
        self.assertTrue(record["exports_identical"])
        self.assertTrue(record["jni_tables_identical"])
        self.assertTrue(record["dispatch_identical"])

    def test_boundary_portable_path(self):
        path = audit.WORKSPACES / "westlake-harness-tools-inventory/benchmark/file"
        self.assertEqual(audit.portable(path), "$WORKSPACES/westlake-harness-tools-inventory/benchmark/file")


if __name__ == "__main__":
    unittest.main()
