#!/usr/bin/env python3
"""Known answers over immutable review receipts; not board acceptance."""
import hashlib
import json
import os
from pathlib import Path
import subprocess
import tempfile
import unittest

HERE = Path(__file__).resolve().parent
RAW_HERE = HERE
if not (RAW_HERE / '.artifacts/t5-70b6-independent-attempt4').is_dir():
    workspaces = Path(os.environ.get('WORKSPACES', str(HERE.parents[2])))
    RAW_HERE = workspaces / 'westlake-harness-bms/benchmark/2026-10-12-toutiao-recovery-review'
ATTEMPT = RAW_HERE / '.artifacts/t5-70b6-independent-attempt4'
DATA = json.loads((HERE / 't5-70b6-results.json').read_text())
ROWS = {row['case']: row for row in DATA['cases']}


@unittest.skipUnless(ATTEMPT.is_dir(), 'Persistent independent raw attempt unavailable; no candidate PASS is inferred')
class FrozenReviewAnswers(unittest.TestCase):
    def test_complete_bound_matrix(self):
        self.assertEqual(len(ROWS), 26)
        self.assertEqual(DATA['receipt']['members'], 58)
        self.assertEqual(DATA['receipt']['commit'], '70b6eeda5811819a6fcb03061906838ffce5f963')
        for name, row in ROWS.items():
            root = ATTEMPT / 'cases' / name
            for filename, field in [('plan.json', 'real_plan_sha256'), ('synthetic-auth.json', 'real_auth_sha256')]:
                content = (root / filename).read_bytes()
                if name == 'new_boot_rollback' and filename == 'synthetic-auth.json':
                    ticket = json.loads(content)
                    ticket['boot_id'] = json.loads((root / 'plan.json').read_text())['boot_id']
                    content = json.dumps(ticket, indent=2).encode()
                self.assertEqual(hashlib.sha256(content).hexdigest(), row[field])

    def test_actual_cli_success_and_preview_no_calls(self):
        self.assertEqual(ROWS['positive_cli']['apply_exit'], 0)
        self.assertEqual(ROWS['positive_cli']['send_count'], 4)
        self.assertEqual(ROWS['preview']['transport_calls'], 0)
        self.assertFalse((ATTEMPT / 'cases/preview/transaction').exists())

    def test_identity_and_backup_fail_before_write(self):
        for name in ['wrong_auth_pin', 'changed_plan', 'wrong_serial', 'expired_auth',
                     'wrong_auth_boot', 'wrong_device_boot', 'missing_before_label',
                     'partial_backup', 'preimage_drift']:
            self.assertEqual(ROWS[name]['apply_exit'], 2)
            self.assertEqual(ROWS[name]['send_count'], 0)

    def test_zero_write_missing_root_not_success(self):
        row = ROWS['mkdir_first_failure']
        self.assertEqual(row['send_count'], 0)
        self.assertFalse(row['root_exists_after_apply'])
        self.assertEqual(row['rollback_exit'], 2)
        self.assertFalse(row['root_stop_exists'])
        self.assertFalse(row['rollback_receipt_exists'])
        self.assertTrue(all(row['restored_aliases'].values()))
        self.assertIn('rollback-stop-create', row['rollback_stderr'])

    def test_real_local_shell_missing_parent_redirection(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory) / 'absent' / 'attempt'
            result = subprocess.run(['/bin/sh', '-c', 'set -eu; set -C; umask 077; : > "$1/stop"',
                                     'readonly-protocol-proof', str(root)], capture_output=True, text=True)
            self.assertNotEqual(result.returncode, 0)
            self.assertFalse(root.exists())

    def test_partial_send_retains_unrestored_alias(self):
        row = ROWS['partial_send']
        self.assertEqual(row['send_count'], 3)
        self.assertEqual(row['rollback_exit'], 2)
        self.assertEqual(row['rollback_sends'], 0)
        self.assertFalse(any(row['restored_aliases'].values()))
        self.assertIn('foreign/partial replacement', row['rollback_stderr'])

    def test_unknown_after_metadata_reaches_write(self):
        self.assertEqual(ROWS['null_after_label']['apply_exit'], 2)
        self.assertEqual(ROWS['null_after_label']['send_count'], 2)

    def test_inert_retry_is_retryable(self):
        row = ROWS['inert_retry']
        self.assertEqual(row['rollback_exit'], 2)
        self.assertFalse(row['rollback_receipt_exists'])
        self.assertEqual(row['retry_exit'], 0)
        root = ATTEMPT / 'cases/inert_retry'
        model = json.loads((root / 'device.json').read_text())
        plan = json.loads((root / 'plan.json').read_text())
        for member in plan['members']:
            if member['before']['exists'] and member['target'].endswith('/watchdog.sh'):
                self.assertEqual(model['objects'][member['target']]['sha256'], member['before']['sha256'])
        self.assertTrue((root / 'transaction/rollback.json').is_file())

    def test_exact_guardian_and_backup_rejects_no_stop(self):
        for name in ['guardian_reuse', 'guardian_uid', 'guardian_argv', 'wrong_guardian_boot',
                     'wrong_transaction', 'corrupt_backup']:
            self.assertEqual(ROWS[name]['rollback_exit'], 2)
            self.assertEqual(ROWS[name]['rollback_sends'], 0)
            self.assertFalse(ROWS[name]['root_stop_exists'])
        self.assertTrue(ROWS['guardian_stuck']['root_stop_exists'])
        self.assertFalse(ROWS['guardian_stuck']['rollback_receipt_exists'])
        for directory in (ATTEMPT / 'cases').iterdir():
            model = json.loads((directory / 'device.json').read_text())
            self.assertFalse(any('kill ' in command[-1] or 'target boot' in command[-1]
                                 for command in model['events']))

    def test_original_r2_files_unchanged(self):
        mapping = json.loads((RAW_HERE / 'evidence/t4-handoff-inputs.json').read_text())['original_r2_file_hashes']
        repository = RAW_HERE.parents[1]
        self.assertEqual(len(mapping), 52)
        for path, expected in mapping.items():
            self.assertEqual(hashlib.sha256((repository / path).read_bytes()).hexdigest(), expected)


if __name__ == '__main__':
    unittest.main(verbosity=2)
