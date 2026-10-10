import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

HERE = Path(__file__).resolve().parent
GATE = HERE / "sepolicy_gate.py"
HERE.parents[1].mkdir(parents=True, exist_ok=True)
EVIDENCE = HERE.parents[1] / "knowledge/gates/sepolicy-evidence.json"

sys.path.insert(0, str(HERE))
import lab_paths  # noqa: E402

POLICY = lab_paths.workspaces() / "westlake-inputs/sepolicy/oh-6.1.0.31/policy"


def run_gate(policy=None, recipe=None):
    with tempfile.TemporaryDirectory() as td:
        ev = Path(td) / "ev.json"
        cmd = [sys.executable, str(GATE), "--evidence", str(ev)]
        if policy:
            cmd += ["--policy", str(policy)]
        if recipe:
            cmd += ["--recipe", str(recipe)]
        r = subprocess.run(cmd, capture_output=True, text=True, timeout=600)
        data = json.loads(ev.read_text()) if ev.exists() else None
        return r, data


@unittest.skipUnless(POLICY.is_file(), "pinned policy not pulled on this host")
class TestSepolicyGate(unittest.TestCase):
    def test_all_recipe_entries_pass_evidence_portable(self):
        r, ev = run_gate()
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertIn("all 35 proofs pass", r.stdout)
        self.assertIn("app-private", r.stdout)  # reported skipped, out of scope
        self.assertEqual(ev.get("skipped"), ["app-private"])
        self.assertEqual(ev["policy_path"], "$WORKSPACES/westlake-inputs/sepolicy/oh-6.1.0.31/policy")
        self.assertNotIn("/Users/", ev["policy_path"])
        self.assertEqual(ev["failures"], [])
        ep = [p for p in ev["proofs"] if p["id"] == "init-entry"]
        self.assertTrue(ep and "appspawn_exec" in ep[0]["rule"])

    def test_shared_evidence_untouched_by_tests(self):
        before = EVIDENCE.read_bytes() if EVIDENCE.exists() else None
        run_gate()
        after = EVIDENCE.read_bytes() if EVIDENCE.exists() else None
        self.assertEqual(before, after, "tests must not rewrite the shared evidence file")

    def test_wrong_entrypoint_label_rejected(self):
        bad = {"schema_version": 1, "scope": "x", "sources": [], "required_targets": [],
               "rules": [{"id": "init-entry", "match": {"exact": "/system/bin/appspawn-x"},
                          "context": "u:object_r:system_file:s0", "sources": []}], "default": {}}
        with tempfile.NamedTemporaryFile("w", suffix=".json", delete=False) as f:
            json.dump(bad, f); tf = f.name
        try:
            r, _ = run_gate(recipe=Path(tf))
            self.assertNotEqual(r.returncode, 0)
            self.assertIn("init-entry", r.stderr)
            self.assertIn("entrypoint", r.stderr)
        finally:
            os.unlink(tf)

    def test_policy_sha_drift_fails_closed(self):
        with tempfile.NamedTemporaryFile("wb", suffix=".policy", delete=False) as f:
            f.write(b"not-the-policy"); tf = f.name
        try:
            r, _ = run_gate(policy=Path(tf))
            self.assertNotEqual(r.returncode, 0)
            self.assertIn("sha drift", r.stderr)
        finally:
            os.unlink(tf)

    def test_missing_policy_fails_closed(self):
        r, _ = run_gate(policy=Path("/nonexistent/policy"))
        self.assertNotEqual(r.returncode, 0)
        self.assertIn("policy missing", r.stderr)


if __name__ == "__main__":
    unittest.main()
