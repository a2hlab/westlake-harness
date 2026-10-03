#!/usr/bin/env python3
"""Known-answer test: the parameterized stage_a_selftest.py must reproduce U13's master report.

Runs build() over the real U13 tree with U13's pattern and compares:
  - report SHA prefix 0488fa09
  - 41 explanations (the common shard's count on master)
  - exclusion class counts include the executor-state records
Skipped when the U13 tree is not present on this host.
"""
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import lab_paths  # noqa: E402
import stage_a_selftest as sas  # noqa: E402

U13_ROOT = lab_paths.workspaces() / 'westlake-harness-u7-executor/benchmark/2026-10-03-u13-stage-a-plan'
_MASTER = lab_paths.workspaces() / 'westlake-harness/benchmark/2026-10-03-u13-stage-a-decision' \
          '/selftest-explanations-common.json'

U13_PATTERN = 'window*/u13-A*/*/runner/**/record.json'


class U13KnownAnswer(unittest.TestCase):
    def test_reproduces_master_report_sha_and_41_explanations(self):
        if not U13_ROOT.is_dir():
            self.skipTest('U13 executor tree not present')
        body, report_sha, rows, excl, any_pid, report = sas.build(U13_ROOT, U13_PATTERN)
        self.assertTrue(report_sha.startswith('0488fa09'),
                        'report sha %s does not match the master prefix 0488fa09' % report_sha)
        self.assertEqual(len(rows), 41, 'expected 41 explanations (master common shard), got %d' % len(rows))
        self.assertEqual(any_pid, {})
        self.assertIn('executor state record (no app run)', excl)
        self.assertGreater(excl['executor state record (no app run)'], 0)

    def test_bad_pattern_errors(self):
        if not U13_ROOT.is_dir():
            self.skipTest('U13 executor tree not present')
        with self.assertRaises(SystemExit):
            sas.build(U13_ROOT, 'window*/no-such-A*/*/runner/**/record.json')


class ExplanationsOutput(unittest.TestCase):
    def test_written_explanations_match_master_row_by_row(self):
        """--out must write 41 rows identical (record/pid/reason/evidence_sha256) to master's
        selftest-explanations-common.json explanations array."""
        master = _MASTER
        if not (U13_ROOT.is_dir() and master.is_file()):
            self.skipTest('U13 tree or master explanations not present')
        import json, tempfile
        import subprocess
        with tempfile.TemporaryDirectory() as tmp:
            r = subprocess.run([sys.executable, str(Path(__file__).resolve().parents[1] / 'stage_a_selftest.py'),
                                '--root', str(U13_ROOT), '--pattern', U13_PATTERN,
                                '--known-answer', '0488fa09', '--out', tmp],
                               capture_output=True, text=True)
            self.assertEqual(r.returncode, 0, r.stderr)
            got = json.loads((Path(tmp) / '2026-10-03-u13-stage-a-plan-explanations.json').read_text())
            want = json.loads(master.read_text())['explanations']
            self.assertEqual(len(got['explanations']), len(want), '41 rows expected')
            for g, w in zip(got['explanations'], want):
                for field in ('record', 'pid', 'reason', 'evidence_sha256'):
                    self.assertEqual(g[field], w[field],
                                     'row mismatch on %s: %r != %r' % (field, g[field], w[field]))


if __name__ == '__main__':
    unittest.main()
