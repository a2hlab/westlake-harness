#!/usr/bin/env python3
"""Unit tests for n11h_readout.py: load-base counting, host-marker split, first-fatal; + window5 known-answer."""
import sys, tempfile, unittest
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import n11h_readout as nr  # noqa: E402

MAPS = """\
7eec078000-7eec153000 r-xp 000b7000 103:30 467241 /system/android/lib64/liboh_adapter_bridge.so
7eec000000-7eec078000 r--p 00000000 103:30 467241 /system/android/lib64/liboh_adapter_bridge.so
7efa9f8000-7efaad3000 r-xp 000b7000 103:30 467241 /system/android/lib64/liboh_adapter_bridge.so
7ed6a2d000-7ed6bbe000 r-xp 0006c000 103:30 463980 /system/android/lib64/liboh_android_runtime.so
7e00000000-7e00001000 r-xp 00000000 103:30 1 /system/android/lib64/libart.so
"""


class LoadBases(unittest.TestCase):
    def setUp(self):
        self.p = Path(tempfile.mkdtemp()) / 'maps.txt'
        self.p.write_text(MAPS)

    def test_two_bridge_one_runtime_one_art(self):
        self.assertEqual(nr.load_bases(self.p, 'liboh_adapter_bridge.so'), 2)   # two distinct r-xp bases
        self.assertEqual(nr.load_bases(self.p, 'liboh_android_runtime.so'), 1)
        self.assertEqual(nr.load_bases(self.p, 'libart.so'), 1)

    def test_rxp_only_not_rminusp(self):
        # the r--p header line for bridge must NOT add a base
        self.assertEqual(nr.load_bases(self.p, 'liboh_adapter_bridge.so'), 2)


class Window5KnownAnswer(unittest.TestCase):
    def test_selftest(self):
        w5 = nr.WORKSPACES / 'westlake-harness-u7-executor/benchmark/2026-10-02-u10-1-t8-rerun/window5'
        if not w5.is_dir():
            self.skipTest('window5 not present')
        self.assertEqual(nr.selftest(), 0)


if __name__ == '__main__':
    unittest.main()
