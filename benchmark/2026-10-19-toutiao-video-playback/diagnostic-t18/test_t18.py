#!/usr/bin/env python3
"""Offline tests for the T18 bridge derivation. Proves: the T18 gate accepts ONLY the new bridge SHA,
refuses the old d4fa and any arbitrary bridge, keeps every other pin byte-identical to T16, and exposes NO
arbitrary-pin interface. Reuses test_t16.complete() so T18 never duplicates the admission builder."""
import inspect, sys, unittest
from pathlib import Path

HERE = Path(__file__).resolve().parent
T16 = HERE.parent / 'diagnostic-t16'
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(T16))
import t18_observer as T18
import t16_core as C          # public T16 (bridge d4fa)
import test_t16               # for complete() admission builder


def admission(bridge_sha):
    a = test_t16.complete()
    a['modules']['bridge']['sha256'] = bridge_sha
    return a


class T18Gate(unittest.TestCase):
    def setUp(self):
        self.t18 = T18.load_t18_core(str(T16))

    def test_accept_new_bridge(self):
        a = admission(T18.NEW_BRIDGE_SHA)
        self.assertEqual(self.t18.t16_validate(a, files=False)['serial'], C.SERIAL)

    def test_reject_old_d4fa_bridge(self):
        with self.assertRaises(RuntimeError):      # old bridge is no longer the T18 pin
            self.t18.t16_validate(admission(T18.OLD_BRIDGE_SHA), files=False)

    def test_reject_arbitrary_bridge(self):
        with self.assertRaises(RuntimeError):
            self.t18.t16_validate(admission('0' * 64), files=False)

    def test_only_bridge_changed(self):
        self.assertEqual(self.t18.MODULE_PINS['bridge'], T18.NEW_BRIDGE_SHA)
        self.assertNotEqual(self.t18.MODULE_PINS['bridge'], C.MODULE_PINS['bridge'])
        for role in ('player', 'android', 'shim', 'hwui'):
            self.assertEqual(self.t18.MODULE_PINS[role], C.MODULE_PINS[role])
        self.assertEqual(self.t18.SERIAL, C.SERIAL)
        self.assertEqual(self.t18.HOST_SHA, C.HOST_SHA)
        self.assertEqual(self.t18.SERVER_SHA, C.SERVER_SHA)
        self.assertEqual(self.t18.EXE_SHA, C.EXE_SHA)
        self.assertEqual(self.t18.PINNED_ADDRESSES, C.PINNED_ADDRESSES)
        self.assertEqual(set(self.t18.REQUIRED_MODULES), set(C.REQUIRED_MODULES))

    def test_public_t16_core_untouched(self):
        # loading T18 must NOT mutate the public t16_core bridge pin (isolation)
        self.assertEqual(C.MODULE_PINS['bridge'], T18.OLD_BRIDGE_SHA)


class T18Shape(unittest.TestCase):
    def test_no_arbitrary_pin_interface(self):
        params = list(inspect.signature(T18.load_t18_core).parameters)
        self.assertEqual(params, ['t16_dir'])          # no bridge=/pin= argument
        self.assertIsInstance(T18.NEW_BRIDGE_SHA, str)  # a hardcoded constant, not an input
        self.assertEqual(len(T18.NEW_BRIDGE_SHA), 64)

    def test_strict_source_pin_matches_real_t16(self):
        import hashlib
        self.assertIn('t16_identity.py', T18.T16_SOURCE_PINS)   # observer imports it (base5)
        for name, pin in T18.T16_SOURCE_PINS.items():
            got = hashlib.sha256((T16 / name).read_bytes()).hexdigest()
            self.assertEqual(got, pin, name + ' source pin must match the real T16 file')

    def test_preview_zero_device(self):
        p = T18.preview()
        self.assertEqual(p['device_calls'], 0)
        self.assertFalse(p['arbitrary_pin_interface'])
        self.assertEqual(p['bridge_new'], T18.NEW_BRIDGE_SHA)


if __name__ == '__main__':
    unittest.main(verbosity=2)
