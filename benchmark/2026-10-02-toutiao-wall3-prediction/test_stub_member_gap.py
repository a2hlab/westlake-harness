#!/usr/bin/env python3
"""stub_member_gap.py: member lookup rules, and the U10 known answer on the real toutiao APK.

Known answer (U10 61b hilog, toutiao CronetInit thread): `NoSuchMethodError: No virtual method getSubtype()I in class
Landroid/net/NetworkInfo; (declaration ... adapter-mainline-stubs.jar)` at
NetworkChangeNotifierAutoDetect$ConnectivityManagerDelegate.getNetworkState, uncaught (the thread ended). The scan must
report that member on that call site with no local Error handler, on the deployed U9 stubs and on T8's.
"""
import sys
import unittest
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(HERE.parents[1] / 'scripts/lab'))
import lab_paths  # noqa: E402
import stub_member_gap as smg  # noqa: E402

APK = Path.home() / 'a2hlab/app-inputs/toutiao/toutiao.apk'
GEN = lab_paths.inputs() / 'generations/u10.1-t8-rerun-j5ae3dd29-s2f365a75-v3/bundle'
T8_STUBS = GEN / 'framework/adapter-mainline-stubs.jar'        # 2f365a75, the round's stubs
U9_STUBS = GEN / 'gate-reference/adapter-mainline-stubs.jar'   # f3bcc9d7, deployed on U9 / U10 / U10.1

STUBS = {
    'La/Base;': {'super': 'Ljava/lang/Object;', 'ifaces': [], 'jar': 's.jar',
                 'methods': {('<init>', '()V'), ('base', '()I')}, 'fields': {'f'}},
    'La/Kid;': {'super': 'La/Base;', 'ifaces': ['La/Iface;'], 'jar': 's.jar', 'methods': set(), 'fields': set()},
    'La/Iface;': {'super': 'Ljava/lang/Object;', 'ifaces': [], 'jar': 's.jar',
                  'methods': {('dflt', '()V')}, 'fields': set()},
    'La/Edge;': {'super': 'Landroid/view/View;', 'ifaces': [], 'jar': 's.jar', 'methods': set(), 'fields': set()},
}


class Lookup(unittest.TestCase):
    def test_inherited_method_field_and_interface_are_found(self):
        self.assertEqual(smg.lookup(STUBS, 'La/Kid;', 'methods', ('base', '()I')), 'found')
        self.assertEqual(smg.lookup(STUBS, 'La/Kid;', 'fields', 'f'), 'found')
        self.assertEqual(smg.lookup(STUBS, 'La/Kid;', 'methods', ('dflt', '()V')), 'found')

    def test_constructors_are_not_inherited(self):
        self.assertEqual(smg.lookup(STUBS, 'La/Kid;', 'methods', ('<init>', '()V')), 'missing')

    def test_absent_member_is_missing_unless_the_hierarchy_leaves_the_stubs(self):
        self.assertEqual(smg.lookup(STUBS, 'La/Kid;', 'methods', ('nope', '()V')), 'missing')
        self.assertEqual(smg.lookup(STUBS, 'La/Edge;', 'methods', ('nope', '()V')), 'super_outside_stubs')


@unittest.skipUnless(APK.exists() and T8_STUBS.exists() and U9_STUBS.exists(), 'toutiao APK / round stubs not here')
class ToutiaoKnownAnswer(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.t8 = smg.scan(str(APK), smg.load_stubs([str(T8_STUBS)]))
        cls.u9 = smg.scan(str(APK), smg.load_stubs([str(U9_STUBS)]))

    def test_cronet_getsubtype_site_is_reported_uncaught(self):
        row = next(r for r in self.t8 if r['class'] == 'Landroid/net/NetworkInfo;' and r['member'] == 'getSubtype()I')
        self.assertEqual(row['verdict'], 'missing')
        site = ('Lcom/ttnet/org/chromium/net/NetworkChangeNotifierAutoDetect$ConnectivityManagerDelegate;',
                'getNetworkState', 'none')
        self.assertIn(site, row['sites'])

    def test_t8_closes_none_of_the_u9_member_gaps(self):
        key = lambda rows: {(r['class'], r['member']) for r in rows}
        self.assertEqual(key(self.t8), key(self.u9))
        self.assertEqual(len(self.t8), 122)


if __name__ == '__main__':
    unittest.main()
