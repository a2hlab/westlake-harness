#!/usr/bin/env python3
"""Execute frozen boot shell cases without compilation or device endpoints."""
import hashlib
import importlib.util
import json
from pathlib import Path
import unittest

HERE = Path(__file__).resolve().parent
ATTEMPT = HERE / '.artifacts/t5-70b6-independent-attempt4'
PACKAGE = ATTEMPT / 'workspaces/westlake-harness-t0/benchmark/2026-10-12-recovery-executor'
specification = importlib.util.spec_from_file_location('frozen_boot_tests', PACKAGE / 'tests/test_autoboot.py')
module = importlib.util.module_from_spec(specification)
specification.loader.exec_module(module)


class IndependentBootBoundaries(module.AutoBootTests):
    def test_current_installed_uid_must_match(self):
        temporary, root, tools, kernel, old, calls, provenance = self.setup_case()
        (tools / 'stat').write_text('#!/bin/bash\nprintf "20011207\\n"\n')
        result = self.invoke(root, tools)
        self.assertEqual(result.returncode, 2, result.stderr)
        self.assertIn('INSTALLED_HOST_UID_CHANGED', result.stderr)
        self.assertFalse(calls.exists())

    def test_root_stop_kept_no_entry(self):
        temporary, root, tools, kernel, old, calls, provenance = self.setup_case()
        (root / 'stop').write_text('operator stop\n')
        result = self.invoke(root, tools)
        self.assertEqual(result.returncode, 2, result.stderr)
        self.assertIn('CANDIDATE_STOP', result.stderr)
        self.assertEqual((root / 'stop').read_text(), 'operator stop\n')
        self.assertFalse(calls.exists())

    def test_member_bytes_changed_no_entry(self):
        temporary, root, tools, kernel, old, calls, provenance = self.setup_case()
        (root / 'entry.sh').write_text('exit 0\n')
        result = self.invoke(root, tools)
        self.assertNotEqual(result.returncode, 0, result.stderr)
        self.assertFalse(calls.exists())


if __name__ == '__main__':
    selected = ['test_same_immutable_config_two_boots_no_mac_authorization',
                'test_candidate_stop_survives_later_boot', 'test_config_drift_and_unsigned_no_entry',
                'test_cfg_privileges_and_no_expiring_runtime_ticket',
                'test_current_installed_uid_must_match', 'test_root_stop_kept_no_entry',
                'test_member_bytes_changed_no_entry']
    suite = unittest.TestSuite(IndependentBootBoundaries(name) for name in selected)
    result = unittest.TextTestRunner(verbosity=2).run(suite)
    receipt = {'synthetic': True, 'commit': '70b6eeda5811819a6fcb03061906838ffce5f963',
               'tests_run': result.testsRun, 'failures': len(result.failures), 'errors': len(result.errors),
               'builds': 0, 'device_calls': 0,
               'limitations': ['lexical path relocation', 'recorded UID tools', 'entry endpoint substituted',
                               'not full fresh WID/parent/namespace or init acceptance'],
               'source_sha256': {name: hashlib.sha256((PACKAGE / 'payload' / name).read_bytes()).hexdigest()
                                 for name in ['config-common.sh', 'boot-entry.sh', 'entry.sh']}}
    (ATTEMPT / 'autoboot-review.json').write_text(json.dumps(receipt, indent=2) + '\n')
    raise SystemExit(0 if result.wasSuccessful() else 1)
