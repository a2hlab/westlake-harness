import hashlib
import json
from pathlib import Path
import unittest

HERE = Path(__file__).resolve().parent


class AnalysisTests(unittest.TestCase):
    def test_eight_real_attempts_are_bound(self):
        report = json.loads((HERE / "observations.json").read_text())
        self.assertEqual(report["source_commit"], "2aa6c49df0")
        self.assertEqual(len(report["rows"]), 8)
        for row in report["rows"]:
            self.assertIn("signo(6)", row["terminal"]["message"])
            self.assertEqual(row["terminal"]["pid"], row["pid"])
            self.assertTrue(row["root_runtime_hashes_verified"])
            self.assertTrue(row["run_apk_identity_verified"])
            self.assertTrue(row["build_id_verified"])
            self.assertEqual(row["abort_message"], "not captured")
            self.assertEqual(row["faultlogs"], [])
            self.assertTrue(row["frames"])

    def test_seven_actual_callers_not_signal_family_guess(self):
        report = json.loads((HERE / "observations.json").read_text())
        rows = [row for row in report["rows"] if row["key"] != "subwaysurfers"]
        self.assertEqual(len(rows), 7)
        for row in rows:
            source = (HERE / row["disassembly"]["evidence"]).read_text()
            self.assertIn(row["caller_pc"][2:] + ":", source)
            self.assertIn("AAssetManager_fromJava@plt", source)
        for name in ["libandroid.so", "liboh_android_runtime.so"]:
            self.assertIn("br\tx3", (HERE / ("evidence/converter-" + name + ".txt")).read_text())

    def test_unity_loader_and_no_fabricated_unlock(self):
        result = json.loads((HERE / "results.json").read_text())
        self.assertEqual([row["affected_keys"] for row in result["clusters"]], [7, 1])
        self.assertEqual(result["clusters"][1]["required_media_import_count"], 50)
        self.assertIsNone(result["clusters"][1]["donor_commit"])
        text = (HERE / "evidence/subwaysurfers-load-path.txt").read_text()
        self.assertIn("4df4:", text)
        self.assertIn("b\t0x4db8", text)
        self.assertIn("dlopen@plt", text)
        self.assertEqual(result["newly_lit_prediction_supported"], [])
        for row in result["predictions"]:
            self.assertEqual(row["next_exact_fatal"], "unknown")
        providers = json.loads((HERE / "providers.json").read_text())
        for row in providers["upstream_snapshots"]:
            self.assertEqual(hashlib.sha256((HERE / row["snapshot"]).read_bytes()).hexdigest(), row["sha256"])


if __name__ == "__main__":
    unittest.main()
