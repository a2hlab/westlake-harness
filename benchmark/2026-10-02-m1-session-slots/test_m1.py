#!/usr/bin/env python3
"""Runs the host test of the per-session slot helpers (extracted verbatim from the bridge source); skipped without
a C++ compiler."""
import shutil
import subprocess
import unittest
from pathlib import Path

HERE = Path(__file__).resolve().parent


class SessionSlots(unittest.TestCase):
    def test_host_slots(self):
        if not shutil.which('c++'):
            self.skipTest('no c++')
        r = subprocess.run(['bash', str(HERE / 'test/run_slots_test.sh')], capture_output=True, text=True)
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        self.assertIn('PASS (0 failure(s))', r.stdout)


if __name__ == '__main__':
    unittest.main()
