#!/usr/bin/env python3
"""auto_approve_exceptions: identical findings (ignoring issue_id, disposition, line, sequence) match approved ones."""
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import auto_approve_exceptions as a

OLD = 'a' * 64
NEW = 'b' * 64


def finding(text, line, seq, iid, disp):
    return {'kind': 'unknown', 'detail': {'evidence': {'source': 'x.c', 'line': line, 'text': text}, 'sequence': seq},
            'issue_id': iid, 'disposition': disp}


class Auto(unittest.TestCase):
    def setUp(self):
        self.base = {'package_manifest_sha256': OLD, 'inputs_sha256': 'c' * 64,
                     'gates': {'N1': {'findings': [finding('dlopen(a)', 10, 3, '1' * 64, 'EXCEPTED'),
                                                   finding('dlopen(b)', 20, 4, '2' * 64, 'REJECT')]}}}
        self.reg = [{'gate': 'N1', 'package_manifest_sha256': OLD, 'issue_id': '1' * 64, 'approved_by': 'outer(claude)',
                     'removal_condition': 'rc'}]

    def test_moved_line_and_sequence_still_identical(self):
        cand = {'package_manifest_sha256': NEW, 'inputs_sha256': 'd' * 64,
                'gates': {'N1': {'findings': [finding('dlopen(a)', 99, 7, '9' * 64, 'REJECT')]}}}
        matched, new = a.classify(cand, [self.base], self.reg)
        self.assertEqual((len(matched), len(new)), (1, 0))
        self.assertEqual(matched[0][2]['issue_id'], '1' * 64)

    def test_changed_text_is_new(self):
        cand = {'package_manifest_sha256': NEW, 'inputs_sha256': 'd' * 64,
                'gates': {'N1': {'findings': [finding('dlopen(a2)', 10, 3, '9' * 64, 'REJECT')]}}}
        self.assertEqual(len(a.classify(cand, [self.base], self.reg)[1]), 1)

    def test_rejected_or_unregistered_baseline_does_not_approve(self):
        cand = {'package_manifest_sha256': NEW, 'inputs_sha256': 'd' * 64,
                'gates': {'N1': {'findings': [finding('dlopen(b)', 20, 4, '8' * 64, 'REJECT')]}}}
        self.assertEqual(len(a.classify(cand, [self.base], self.reg)[1]), 1)   # baseline REJECT -> not approved

    def test_gate_matters(self):
        cand = {'package_manifest_sha256': NEW, 'inputs_sha256': 'd' * 64,
                'gates': {'N2': {'findings': [finding('dlopen(a)', 10, 3, '9' * 64, 'REJECT')]}}}
        self.assertEqual(len(a.classify(cand, [self.base], self.reg)[1]), 1)


if __name__ == '__main__':
    unittest.main()
