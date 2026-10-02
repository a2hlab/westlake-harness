import hashlib
import json
from pathlib import Path
import unittest

HERE = Path(__file__).resolve().parent


class Scope(unittest.TestCase):
    def test_successful_resident_queries_are_not_relocation_proof(self):
        result = json.loads((HERE / "results.json").read_text())
        self.assertFalse(result["execution_enabled"])
        self.assertFalse(result["new_native_artifact"])
        self.assertEqual(result["runtime_variable_changed"], 0)
        self.assertEqual(result["proven_first_fatal_moved"], 0)
        for row in result["rows"]:
            self.assertEqual(len(row["preceding_owner_logs"]), 3)
            first_error = min(event["line"] for event in row["relocation_errors"])
            self.assertTrue(all(event["line"] < first_error for event in row["preceding_owner_logs"]))
            self.assertIn("strtoll_l", row["candidate_next_missing_symbols"])
            self.assertEqual(row["next_exact_fatal"], "unknown")

    def test_admitted_sources_match_frozen_receipts_and_app_dispatch(self):
        sources = json.loads((HERE / "sources.json").read_text())
        for row in sources["files"]:
            self.assertEqual(hashlib.sha256((HERE / row["snapshot"]).read_bytes()).hexdigest(), row["sha256"])
        source = (HERE / "inputs/app_native_loader.c").read_text()
        self.assertIn("&domain->app, path, mode | RTLD_LOCAL", source)
        self.assertIn("namespace_host_ops.open_namespace", source)
        host = json.loads((HERE / "evidence/open-host.json").read_text())
        self.assertEqual(sum(row["kind"] == "INHERIT-REPEAT" for row in host["findings"]), 0)
        self.assertEqual(sum(row["kind"] == "INHERIT-AFTER-OPEN" for row in host["findings"]), 4)


if __name__ == "__main__":
    unittest.main()
