#!/usr/bin/env python3
"""Known-answer tests for reboot_sim_inputs.py against the real 5ea v2 snapshot. No board.

Run:  python3 -m unittest -v scripts/lab/test_reboot_sim_inputs.py
"""
import hashlib
import json
import os
import tempfile
import unittest
from pathlib import Path

import reboot_sim_inputs as rsi

WS = os.environ.get("WORKSPACES") or str(Path.home() / "orca/workspaces")
SNAP = Path(WS) / "westlake-harness-tools-inventory/benchmark/2026-10-10-5ea-u13-restore/v2/post-reboot-pre-app/snapshot.json"
RECIPE = Path(WS) / "westlake-harness/knowledge/gates/selinux-label-recipe.json"
EIGHT = {"plan", "snapshot", "inventory", "autostart", "closure", "recipe", "queries", "policy"}


def sha(p):
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()


@unittest.skipUnless(SNAP.is_file(), "real 5ea snapshot not present in this tree")
class RebootSimInputsKnownAnswer(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp())
        self.plan = self.tmp / "plan.json"
        self.plan.write_text(json.dumps({"schema": "deployment/v1", "targets": []}))
        os.environ.setdefault("WORKSPACES", WS)

    def _run(self, extra=None):
        out = self.tmp / "inputs.json"
        argv = ["--snapshot", str(SNAP), "--plan", str(self.plan), "--out", str(out)] + (extra or [])
        rc = rsi.main(argv)
        return rc, (json.loads(out.read_text()) if out.is_file() else None)

    def test_schema_and_eight_names(self):
        rc, m = self._run()
        self.assertEqual(rc, 0)
        self.assertEqual(m["schema_version"], 1)
        self.assertEqual(set(m["inputs"]), EIGHT)

    def test_snapshot_sha_is_the_real_one(self):
        _, m = self._run()
        self.assertEqual(m["inputs"]["snapshot"]["sha256"], sha(SNAP))

    def test_raw_inputs_cover_every_item_with_matching_shas(self):
        _, m = self._run()
        snap = json.loads(SNAP.read_text())
        for name, item in snap["items"].items():
            self.assertIn(name, m["raw_inputs"], "missing raw_input for item " + name)
            self.assertEqual(m["raw_inputs"][name]["sha256"], item.get("raw_sha256"), name)
            if item.get("stderr_raw"):
                self.assertEqual(m["raw_inputs"][name + ".stderr"]["sha256"], item.get("stderr_sha256"), name)

    def test_unsupplied_aux_are_marked_missing(self):
        _, m = self._run()
        for name in ("inventory", "autostart", "closure", "recipe", "queries", "policy"):
            self.assertIsNone(m["inputs"][name]["sha256"])
            self.assertEqual(m["inputs"][name].get("status"), "MISSING")

    @unittest.skipUnless(RECIPE.is_file(), "recipe gate not present")
    def test_supplied_aux_is_referenced_with_correct_sha(self):
        _, m = self._run(extra=["--recipe", str(RECIPE)])
        self.assertEqual(m["inputs"]["recipe"]["sha256"], sha(RECIPE))
        self.assertNotIn("status", m["inputs"]["recipe"])

    def test_refuse_existing_out(self):
        out = self.tmp / "inputs.json"
        out.write_text("{}")
        rc = rsi.main(["--snapshot", str(SNAP), "--plan", str(self.plan), "--out", str(out)])
        self.assertEqual(rc, 2)

    def test_refuse_missing_snapshot(self):
        rc = rsi.main(["--snapshot", str(self.tmp / "nope.json"), "--plan", str(self.plan),
                       "--out", str(self.tmp / "o.json")])
        self.assertEqual(rc, 2)


if __name__ == "__main__":
    unittest.main(verbosity=2)
