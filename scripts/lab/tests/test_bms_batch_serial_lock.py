#!/usr/bin/env python3
"""bms_batch: a second --execute on the same serial is refused while the first holds the per-serial process lock."""
import importlib.util
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

REPO = Path(__file__).resolve().parents[3]
BATCH = REPO / 'benchmark/2026-09-28-bms-route-deploy/batch/bms_batch.py'
spec = importlib.util.spec_from_file_location('bms_batch_under_test', BATCH)
b = importlib.util.module_from_spec(spec); spec.loader.exec_module(b)
SERIAL = sorted(b.SERIALS)[0]


class SerialLock(unittest.TestCase):
    def test_lock_is_exclusive_per_serial(self):
        with tempfile.TemporaryDirectory() as d:
            first = b.serial_process_lock(SERIAL, d)
            self.assertIsNotNone(first)
            self.assertIsNone(b.serial_process_lock(SERIAL, d))          # same serial: refused
            other = b.serial_process_lock(SERIAL + 'x', d)               # another board: allowed
            self.assertIsNotNone(other)
            first.close()
            again = b.serial_process_lock(SERIAL, d)                     # released with the holder
            self.assertIsNotNone(again)
            again.close(); other.close()

    def test_second_execute_refused_before_any_board_command(self):
        with tempfile.TemporaryDirectory() as d:
            held = b.serial_process_lock(SERIAL, d)
            env = dict(os.environ, BMS_BATCH_LOCK_DIR=d)
            out = Path(d) / 'out'
            p = subprocess.run([sys.executable, str(BATCH), '--execute', '--serial', SERIAL, '--lane', 'test',
                                '--out', str(out), '--keys', 'helloworld',
                                '--manifest', str(REPO / 'knowledge/smoke/controls-apps.json')],
                               capture_output=True, text=True, env=env, timeout=60)
            held.close()
            self.assertNotEqual(p.returncode, 0)
            self.assertIn('another bms_batch is already running', p.stderr)
            self.assertFalse(out.exists())                               # nothing created, no board touched


if __name__ == '__main__':
    unittest.main()
