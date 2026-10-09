#!/usr/bin/env python3
"""按真实持久产物复核交件，不以报告文字代替哈希/ABI证据。"""
import hashlib
import json
import sys
import unittest
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[1]
sys.path.insert(0, str(REPO / 'scripts/lab'))
import lab_paths


def read(name):
    return json.loads((HERE / name).read_text())


def sha(p):
    return hashlib.sha256(p.read_bytes()).hexdigest()


class Delivery(unittest.TestCase):
    def setUp(self):
        self.results = read('results.json')
        self.facts = read('evidence/facts.json')
        self.run = Path(self.facts['persisted']['run_dir'].replace('$WORKSPACES', str(lab_paths.workspaces())))

    def test_identity(self):
        expected = 'eebd62f2e9107e7915745280d4de85d44e4106a589508d25fa5f867007b2473c'
        for name in ('loader-a.so', 'loader-b.so'):
            self.assertEqual(sha(self.run / name), expected)
        fp = REPO / 'benchmark/2026-10-09-demo-baseline/evidence/readonly-20261009/61b/runtime-fingerprint.txt'
        self.assertIn(expected + '  /system/android/lib64/libapp_native_loader.so', fp.read_text())
        self.assertEqual(self.facts['loader']['identical_sections'], self.facts['loader']['section_count'])
        for key, file in (('log_sha256', 'build.log'), ('receipt_sha256', 'receipt.json')):
            self.assertEqual(sha(self.run / file), self.facts['persisted'][key])
        abi = read('evidence/loader-abi.json')
        self.assertEqual(abi['consumers'][0]['sha256'], '2a87118e7e8e62fb73ef71a436517cda406c308668753a478cf52331e996072e')
        self.assertEqual(abi['consumer_breaks'], [])

    def test_owner(self):
        abi = read('evidence/host-abi.json')
        for field in ('added', 'removed', 'drift', 'consumer_breaks'):
            self.assertEqual(abi[field], [])
        self.assertEqual(sha(self.run / 'host-public'), self.facts['host']['new_sha256'])
        self.assertEqual(read('evidence/host-strings-diff.json'), {
            'added': ['libicui18n.so:libGLESv2.so:libGLESv3.so:libjnigraphics.so'], 'removed': []})
        self.assertEqual(self.results['namespace_fix']['artifact'], 'appspawn-x')
        self.assertFalse(self.results['namespace_fix']['loader_only_fix_claimed'])

    def test_boat(self):
        boat = self.facts['boat']
        source = Path(boat['source'].replace('$HOME', str(Path.home())))
        self.assertEqual(sha(source), boat['sha256'])
        self.assertEqual(len(read('evidence/boat-byte-diff.json')), 49)
        self.assertEqual(boat['targets'], ['/system/android/lib64/libandroid.so'])
        self.assertFalse(boat['secondary_direct_replacement_verified'])
        self.assertEqual(boat['secondary_matching_patch_bytes'], 2)
        self.assertEqual(len(read('evidence/boat-runtime-abi.json')['removed']), 520)
        self.assertFalse(boat['compilation_required'])

    def test_report(self):
        self.assertEqual(self.results['status'], 'partially')
        self.assertEqual(self.results['board_writes'], 0)
        self.assertEqual(self.results['deployment_status'], 'unverified')
        gates = read('evidence/gates.json')
        for name in ('frozen', 'user_paths'):
            self.assertEqual(gates[name]['rc'], 0)
        self.assertTrue((HERE / 'README.md').exists())


if __name__ == '__main__':
    if len(sys.argv) > 1:
        name = sys.argv.pop(1)
        suite = unittest.defaultTestLoader.loadTestsFromName('Delivery.test_' + name, sys.modules[__name__])
    else:
        suite = unittest.defaultTestLoader.loadTestsFromTestCase(Delivery)
    sys.exit(not unittest.TextTestRunner(verbosity=2).run(suite).wasSuccessful())
