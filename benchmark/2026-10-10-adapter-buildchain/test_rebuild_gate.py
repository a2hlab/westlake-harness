#!/usr/bin/env python3
"""Known answers for the offline rebuildability fence; fixtures are not reproduction receipts."""
import contextlib
import copy
import importlib.util
import io
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

HERE = Path(__file__).resolve().parent
spec = importlib.util.spec_from_file_location("rebuild_gate", HERE / "rebuild_gate.py")
gate = importlib.util.module_from_spec(spec)
spec.loader.exec_module(gate)


class RebuildGateTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        p = self.root / "input"
        p.write_bytes(b"fixture input, not a real compiler")
        evidence = self.root / "evidence.txt"
        evidence.write_text("fixture paired log")
        self.row = {
            "id": "fixture", "sha256": gate.digest(p), "provenance": {"source": "fixture"},
            "inputs": {k: {"state": "complete", "path": str(p), "sha256": gate.digest(p)} for k in gate.REQUIRED},
            "evidence": ["evidence.txt"],
            "last_reproduction": {"status": "reproduced", "runs": [
                {"clean_dir": str(self.root / label), "clean": True, "rc": 0, "tee_rc": 0,
                 "artifact": {"path": str(p), "sha256": gate.digest(p)},
                 "raw_log": {"path": str(evidence), "sha256": gate.digest(evidence)}}
                for label in ("clean-a", "clean-b")]},
        }

    def test_two_pinned_clean_receipts_pass(self):
        self.assertEqual([], gate.audit(self.row, self.root, True))

    def test_missing_input_stops_without_build_or_binary(self):
        self.row["inputs"]["patch_series"] = {"state": "missing"}
        table = self.root / "registry.json"
        table.write_text(json.dumps({"schema": 1, "artifacts": [dict(self.row, evidence=[])]}))
        with patch.object(gate.subprocess, "check_output") as build, contextlib.redirect_stdout(io.StringIO()) as out:
            rc = gate.main(["--table", str(table), "--artifact", "fixture", "--preflight"])
        self.assertEqual(2, rc)
        self.assertIn("patch_series", out.getvalue())
        build.assert_not_called()
        self.assertFalse(list(self.root.glob("*.so")))

    def test_changed_input_rejects(self):
        self.row["inputs"]["build_script"]["sha256"] = "0" * 64
        self.assertIn("build_script", "\n".join(gate.audit(self.row, self.root)))

    def test_unpinned_partial_source_rejects(self):
        self.row["inputs"]["source_snapshot"]["state"] = "partial"
        self.assertIn("source_snapshot", "\n".join(gate.audit(self.row, self.root)))

    def test_reused_clean_directory_rejects(self):
        self.row["last_reproduction"]["runs"][1]["clean_dir"] = self.row["last_reproduction"]["runs"][0]["clean_dir"]
        self.assertIn("same clean directory", "\n".join(gate.audit(self.row, self.root, True)))

    def test_changed_raw_log_rejects(self):
        (self.root / "evidence.txt").write_text("changed log")
        self.assertIn("raw_log", "\n".join(gate.audit(self.row, self.root, True)))

    def test_mismatch_returns_nonzero_and_report_no_patched_output(self):
        target, r1, r2 = [self.root / x for x in ("target", "r1", "r2")]
        target.write_bytes(b"target"); r1.write_bytes(b"different"); r2.write_bytes(b"different")
        report = self.root / "diff.json"
        with contextlib.redirect_stdout(io.StringIO()):
            rc = gate.main(["--compare", str(target), str(r1), str(r2), "--report", str(report)])
        self.assertEqual(2, rc)
        self.assertFalse(json.loads(report.read_text())["new_patched_artifact_created"])
        self.assertFalse(list(self.root.glob("*.so")))

    def test_equal_bytes_comparator_positive_is_fixture_only(self):
        files = [self.root / x for x in ("target", "r1", "r2")]
        for f in files:
            f.write_bytes(b"fixture bytes")
        self.assertTrue(gate.compare(files[0], files[1:])["byte_identical"])

    def test_missing_or_malformed_table_fails_closed(self):
        table = self.root / "bad.json"
        for data in (None, "{", '{"schema": 99, "artifacts": []}'):
            if data is not None:
                table.write_text(data)
            with contextlib.redirect_stdout(io.StringIO()):
                self.assertEqual(2, gate.main(["--table", str(table)]))

    def test_recorded_search_first_visits_are_mac_vm_remote(self):
        log = json.loads((HERE / "search-log.json").read_text())
        order = [next(i for i, row in enumerate(log["entries"]) if row["stage"] == tag)
                 for tag in ("Mac", "OrbStack", "hw248")]
        self.assertEqual(sorted(order), order)
        self.assertEqual([], log["upstream_downloads"])

    def test_real_target_known_answers(self):
        targets = json.loads((HERE / "target-identities.json").read_text())
        self.assertEqual("84695d62f515cfec6bb317c959ec55b1d5085bf82303f792a764cf549a22267a", targets["u13"]["sha256"])
        self.assertEqual("8ab85446f8b386c4a649576326d5f393669b3a22529874fb673eea7c3b1cd71e", targets["boat"]["sha256"])
        self.assertEqual((2357, 2359), tuple(targets[x]["defined_dynamic_count"] for x in ("u13", "boat")))
        self.assertEqual(targets["u13"]["needed"], targets["boat"]["needed"])
        self.assertEqual((53, 53), tuple(targets[x]["file_symbol_count"] for x in ("u13", "boat")))

    def test_actual_registry_preserves_adapter_block_and_runtime_receipt(self):
        table = json.loads((gate.REPO / "knowledge/gates/rebuildable-artifacts.json").read_text())
        self.assertEqual(["locked", "locked", "reproduced"],
                         [row["last_reproduction"]["status"] for row in table["artifacts"]])
        runtime = table["artifacts"][2]
        self.assertEqual("18763dd4b3a48aefaaf80c9f9630b849e282175eea8da04f7918d6d2cfa3fbae", runtime["sha256"])
        runs = runtime["last_reproduction"]["runs"]
        self.assertEqual(2, len(runs))
        self.assertNotEqual(runs[0]["clean_dir"], runs[1]["clean_dir"])
        for run in runs:
            self.assertEqual(runtime["sha256"], run["artifact"]["sha256"])
            self.assertEqual(0, run["preexisting_objects_consumed"])
            self.assertGreater(run["raw_log"]["bytes"], 0)



if __name__ == "__main__":
    unittest.main()
