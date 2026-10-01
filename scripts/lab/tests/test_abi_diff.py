#!/usr/bin/env python3
"""abi_diff: a changed signature is reported as drift; a consumer import the new build lacks is a break."""
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import abi_diff as a  # noqa: E402

OLD_CS = '_ZN10oh_adapter21OHWindowManagerClient13createSessionEiiiim'
NEW_CS = '_ZN10oh_adapter21OHWindowManagerClient13createSessionEiiiiim'
NAMES = {OLD_CS: 'oh_adapter::OHWindowManagerClient::createSession(int, int, int, int, unsigned long)',
         NEW_CS: 'oh_adapter::OHWindowManagerClient::createSession(int, int, int, int, int, unsigned long)',
         'gone_c_fn': 'gone_c_fn', 'kept': 'kept'}


class AbiDiff(unittest.TestCase):
    def test_signature_change_is_drift(self):
        rep = a.compare({OLD_CS, 'kept'}, {NEW_CS, 'kept'}, NAMES, {})
        self.assertEqual(len(rep['drift']), 1)
        self.assertEqual(rep['drift'][0]['function'], 'oh_adapter::OHWindowManagerClient::createSession')

    def test_consumer_break(self):
        rep = a.compare({'gone_c_fn', 'kept'}, {'kept'}, NAMES, {'libx.so': {'gone_c_fn', 'malloc'}})
        self.assertEqual([b['symbol'] for b in rep['consumer_breaks']], ['gone_c_fn'])
        self.assertEqual(rep['drift'], [])

    def test_base_name_ignores_template_parens(self):
        self.assertEqual(a.base_name('ns::f<void (int)>::g(int) const'), 'ns::f<void (int)>::g')


if __name__ == '__main__':
    unittest.main()
