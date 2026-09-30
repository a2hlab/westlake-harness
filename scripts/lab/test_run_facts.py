#!/usr/bin/env python3
"""run_facts.py prints the run identity first, so a regenerated facts.txt still says what it was counted on."""
import contextlib
import io
import json
import pathlib
import sys
import tempfile
import unittest

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
import run_facts


def run(d):
    buf = io.StringIO()
    with contextlib.redirect_stdout(buf):
        run_facts.main(["run_facts.py", str(d)])
    return buf.getvalue().splitlines()


class Identity(unittest.TestCase):
    def make(self, root, fingerprints=True):
        base = pathlib.Path(root) / "5cd1e3dd00000000000000000923012c"
        (base / "app").mkdir(parents=True)
        (base / "app" / "record.json").write_text(json.dumps({"status": "ok", "screenshots": []}))
        if fingerprints:
            (base / "runtime-fingerprint.txt").write_text("aa  /system/android/lib64/libx.so\n")
            (base / "boot-image-fingerprint.txt").write_text("bb  /system/android/framework/arm64/boot.art\n")
            (base / "plan.json").write_text(json.dumps({"tool": {"bms_batch_sha256": "456dfc6f00", "git_head": "380e9450d00",
                                                                  "manifest_sha256": "71cd7ecd00"}}))
        return root

    def test_header_order(self):
        with tempfile.TemporaryDirectory() as t:
            lines = run(self.make(t))
        self.assertEqual([l.split()[0] for l in lines[:4]], ["RUNTIME", "FROZEN", "BOOTIMAGE", "TOOL"])
        self.assertIn("head=380e9450d manifest=71cd7ecd", lines[3])
        self.assertTrue(lines[-1].startswith("TOTAL keys=1"))

    def test_missing_identity_is_said(self):
        with tempfile.TemporaryDirectory() as t:
            lines = run(self.make(t, fingerprints=False))
        self.assertTrue(lines[0].startswith("RUNTIME fingerprint=unknown"))
        self.assertTrue(lines[1].startswith("BOOTIMAGE fingerprint=unknown"))
        self.assertTrue(lines[2].startswith("TOOL unknown"))


if __name__ == "__main__":
    unittest.main()
