#!/usr/bin/env python3
"""Tests for window_preflight.py (RUNBOOK pre-window gate). Uses a fake hdc; no board.

Run:  python3 -m unittest -v scripts/lab/test_window_preflight.py
"""
import io
import json
import os
import stat
import tempfile
import unittest
from contextlib import redirect_stdout
from pathlib import Path

import window_preflight as wp

SERIAL = "61b0657200000000000000000324012c"


def fake_hdc(dirpath, getenforce="Enforcing", uptime="120", ps="", bmdump=""):
    """Write a fake hdc shell that answers the read-only probes from files."""
    for name, val in [("getenforce", getenforce), ("uptime", uptime), ("ps", ps), ("bmdump", bmdump)]:
        (dirpath / name).write_text(val)
    script = dirpath / "hdc"
    script.write_text(
        "#!/bin/sh\n"
        'cmd="$4"\n'                       # args: -t <serial> shell <cmd>
        'case "$cmd" in\n'
        '  *getenforce*) cat "%s/getenforce" ;;\n'
        '  *uptime*)     cat "%s/uptime" ;;\n'
        '  *"ps -A"*)    cat "%s/ps" ;;\n'
        '  *"bm dump"*)  cat "%s/bmdump" ;;\n'
        '  *) echo "" ;;\n'
        'esac\n' % (dirpath, dirpath, dirpath, dirpath))
    script.chmod(script.stat().st_mode | stat.S_IEXEC)
    return str(script)


class WindowPreflight(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp())
        self.baseline = self.tmp / "baseline"
        self.baseline.mkdir()
        # baseline records Enforcing + a launch method
        (self.baseline / "snapshot.json").write_text(json.dumps({"selinux_enforce": "1"}))
        (self.baseline / "run-facts.json").write_text(json.dumps({"launch_method": "icon-tap"}))
        self.manifest = self.tmp / "manifest.json"
        self.manifest.write_text(json.dumps({"apps": [
            {"key": "studytracker", "package": "com.edward.studytracker"},
            {"key": "helloworld", "package": "com.example.helloworld"}]}))

    def _run(self, **hdc_kw):
        hdc = fake_hdc(self.tmp, **hdc_kw)
        argv = [SERIAL, "--keys", "studytracker", "--control", "helloworld",
                "--baseline", str(self.baseline), "--manifest", str(self.manifest), "--hdc", hdc]
        with redirect_stdout(io.StringIO()) as out:
            rc = wp.main(argv)
        return rc, out.getvalue()

    def test_all_pass(self):
        rc, out = self._run(getenforce="Enforcing", uptime="100",
                            bmdump="com.edward.studytracker\ncom.example.helloworld\n", ps="init\nhdcd\n")
        self.assertEqual(rc, 0, out)
        self.assertIn("PREFLIGHT PASS", out)

    def test_selinux_mismatch_fails(self):
        rc, out = self._run(getenforce="Permissive",
                            bmdump="com.edward.studytracker\ncom.example.helloworld\n")
        self.assertEqual(rc, 1)
        self.assertRegex(out, r"selinux-mode\s+FAIL")

    def test_baseline_mode_unknown_fails(self):
        (self.baseline / "snapshot.json").write_text(json.dumps({}))   # no mode recorded
        rc, out = self._run(getenforce="Enforcing",
                            bmdump="com.edward.studytracker\ncom.example.helloworld\n")
        self.assertEqual(rc, 1)
        self.assertIn("baseline mode unknown", out)

    def test_dirty_boot_or_already_started_fails(self):
        rc, out = self._run(getenforce="Enforcing", uptime="100",
                            ps="init\ncom.edward.stud\n",   # studytracker already running (truncated name) -> WMS risk
                            bmdump="com.edward.studytracker\ncom.example.helloworld\n")
        self.assertEqual(rc, 1)
        self.assertRegex(out, r"clean-boot\s+FAIL")
        self.assertIn("already-started", out)

    def test_high_uptime_fails_clean_boot(self):
        rc, out = self._run(getenforce="Enforcing", uptime="99999",
                            bmdump="com.edward.studytracker\ncom.example.helloworld\n")
        self.assertEqual(rc, 1)
        self.assertRegex(out, r"clean-boot\s+FAIL")

    def test_missing_key_or_not_bms_fails(self):
        rc, out = self._run(getenforce="Enforcing", bmdump="com.example.helloworld\n")  # studytracker not in bm dump
        self.assertEqual(rc, 1)
        self.assertRegex(out, r"manifest\+bms\s+FAIL")

    def test_launch_method_mismatch_fails(self):
        (self.baseline / "run-facts.json").write_text(json.dumps({"launch_method": "aa-start"}))
        rc, out = self._run(getenforce="Enforcing",
                            bmdump="com.edward.studytracker\ncom.example.helloworld\n")  # default --launch icon-tap
        self.assertEqual(rc, 1)
        self.assertRegex(out, r"launch-method\s+FAIL")


if __name__ == "__main__":
    unittest.main(verbosity=2)
