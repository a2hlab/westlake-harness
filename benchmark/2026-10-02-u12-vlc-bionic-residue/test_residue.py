import hashlib
import json
from pathlib import Path
import subprocess
import tempfile
import unittest

HERE = Path(__file__).resolve().parent


class Residue(unittest.TestCase):
    def test_real_conversions_nested_pop_and_thread_exit_model(self):
        with tempfile.TemporaryDirectory() as temporary:
            executable = Path(temporary) / "test_adapter"
            subprocess.run(["clang", "-std=c11", "-O2", "-pthread", HERE / "test_adapter.c", "-o", executable], check=True)
            subprocess.run([executable], check=True)

    def test_exact_repeat_and_only_four_export_delta(self):
        receipt = json.loads((HERE / "build-receipt.json").read_text())
        self.assertTrue(receipt["baseline_reproduced"])
        self.assertEqual(receipt["repeated"][0], receipt["repeated"][1])
        self.assertEqual(receipt["repeated"][0]["baseline"], "015aa3a632eabe057bd8d6ce0e0ff181209da7dcab8de22409a79addc0a56d58")
        report = json.loads((HERE / "evidence/abi.json").read_text())
        self.assertEqual(report["added"], ["__pthread_cleanup_pop", "__pthread_cleanup_push", "strtoll_l", "strtoull_l"])
        for name in ["removed", "drift", "call_diffs", "consumer_breaks"]:
            self.assertEqual(report[name], [])
        for row in receipt["source_and_object_inputs"]:
            if "$REPO/benchmark/2026-10-02-u12-vlc-bionic-residue/inputs/" in row["path"]:
                relative = row["path"].split("/inputs/", 1)[1]
                self.assertEqual(hashlib.sha256((HERE / "inputs" / relative).read_bytes()).hexdigest(), row["sha256"])

    def test_scope_and_test_double_are_not_hidden(self):
        result = json.loads((HERE / "results.json").read_text())
        self.assertFalse(result["execution_enabled"])
        self.assertEqual(result["standalone_u12_first_fatal_move"], 0)
        self.assertEqual(result["conditional_after_scope_fix"], ["vlc"])
        self.assertEqual(result["t20"], "unknown")
        gate = json.loads((HERE / "namespace-gates.json").read_text())
        self.assertTrue(gate["n2_findings_identical"])
        self.assertEqual(gate["n1_new"], [])
        self.assertFalse(gate["exception_rebinding_approved"])


if __name__ == "__main__":
    unittest.main()
