#!/usr/bin/env python3
"""The signed U13 stage-A decision passes promotion_hook_u13 and each single defect is caught.

Needs the executor run tree (explanation evidence paths); skipped where it is absent.
"""
import copy
import hashlib
import json
import shutil
import sys
import tempfile
import unittest
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import build_decision as b  # noqa: E402

REPORT = HERE / 'selftest-u13-stage-a.json'


def load(name):
    return json.loads((HERE / name).read_text())


@unittest.skipUnless(b.ROOT.is_dir(), 'executor run tree not on this machine')
class Decision(unittest.TestCase):
    def setUp(self):
        self.reference = json.loads(b.REFERENCE.read_text())
        self.tmp = Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, self.tmp)
        self.smoke = json.loads(b.board_smoke('5ea').read_text())

    def run_hook(self, tag='common', decision=None, report=None, explanations=None, comp=None):
        decision = decision or load('outer-stage-a-%s.json' % tag)
        comp = comp or dict(bundle_sha256=decision['bundle_sha256'], native_manifest_sha256=decision['native_manifest_sha256'])
        rp, ep = REPORT, HERE / ('selftest-explanations-%s.json' % tag)
        if report is not None:
            rp = self.tmp / 'r.json'
            rp.write_text(report)
        if explanations is not None:
            ep = self.tmp / 'e.json'
            ep.write_text(json.dumps(explanations))
        return b.hook.retention_reason(decision, comp, self.reference, self.smoke, rp, ep)

    def test_both_bundles_pass(self):
        self.assertIsNone(self.run_hook('common'))
        self.assertIsNone(self.run_hook('61b'))

    def test_decision_of_one_bundle_does_not_admit_the_other(self):
        other = load('outer-stage-a-61b.json')
        comp = dict(bundle_sha256=other['bundle_sha256'], native_manifest_sha256=other['native_manifest_sha256'])
        self.assertEqual(self.run_hook('common', comp=comp), 'signoff belongs to another bundle')

    def test_dropping_one_explanation_rejects(self):
        e = load('selftest-explanations-common.json')
        e['explanations'] = e['explanations'][1:]
        self.assertEqual(self.run_hook(explanations=e),
                         'not every selftest error/unknown has an exact outer explanation')

    def test_changed_report_bytes_reject(self):
        self.assertEqual(self.run_hook(report=REPORT.read_text() + ' '), 'process selftest report not bound by outer')

    def test_one_badtag_vetoes_even_when_bound(self):
        data = json.loads(REPORT.read_text())
        run = next(r for r in data['runs'] if r['status'] == 'PASS')
        run['badtag_count'] = 1
        body = json.dumps(data, indent=2) + '\n'
        d = copy.deepcopy(load('outer-stage-a-common.json'))
        d['process_selftest_gate']['report_sha256'] = hashlib.sha256(body.encode()).hexdigest()
        self.assertIn('unconditionally rejects', self.run_hook(decision=d, report=body))

    def test_regression_count_must_cover_all_122(self):
        d = copy.deepcopy(load('outer-stage-a-common.json'))
        d['stage_A_regression_verdict']['measured'] = 121
        self.assertEqual(self.run_hook(decision=d), 'all signed U13-reference-lit keys must be measured')


if __name__ == '__main__':
    unittest.main()
