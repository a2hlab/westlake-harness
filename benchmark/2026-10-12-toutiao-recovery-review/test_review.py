#!/usr/bin/env python3
import copy
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parent))
import review
import preview


class EvidenceTests(unittest.TestCase):
    def test_current_originals_and_bindings(self):
        result = review.evidence_review()
        self.assertEqual(result['instance']['seq'], '118')
        self.assertEqual(result['bootstrap']['elapsed'], 184)
        self.assertFalse(result['guardian']['receipt_is_liveness'])
        self.assertFalse(result['run_binding']['window_document_is_current_authorization'])
        self.assertEqual(result['stderr']['alternative_path_contents'], 'unknown; no board read performed')

    def test_wrong_sha_rejected(self):
        entries = json.loads((review.HERE / 'sources.json').read_text())
        entries[0]['sha256'] = '0' * 64
        with self.assertRaisesRegex(ValueError, 'source drift'):
            review.evidence_review(entries)

    def test_missing_source_rejected(self):
        entries = json.loads((review.HERE / 'sources.json').read_text())
        entries[0]['path'] = '$WORKSPACES/nonexistent/r2-missing'
        with self.assertRaisesRegex(ValueError, 'missing'):
            review.evidence_review(entries)


class PreviewTests(unittest.TestCase):
    def setUp(self):
        self.context = dict(serial=review.SERIAL, boot_id=review.BOOT,
                            base_plan_sha256='a' * 64, new_plan_sha256='b' * 64, candidate_sha256='c' * 64)
        self.now = datetime(2026, 10, 12, 12, tzinfo=timezone.utc)
        self.approval = dict(self.context, issued_at='2026-10-12T11:00:00+00:00',
                             expires_at='2026-10-12T13:00:00+00:00', approved_by='outer(codex)',
                             scope='reviewed-route-b-only', data_preserving=True, automatic_consent=False)

    def test_default_has_no_executor(self):
        result = preview.preview(self.context)
        self.assertEqual(result['board_commands_executed'], 0)
        self.assertFalse(result['execution_enabled'])

    def test_valid_preview_is_not_execution_authority(self):
        result = preview.preview(self.context, self.approval, self.now)
        self.assertFalse(result['execution_enabled'])
        self.assertFalse(result['seal_signed'])

    def test_wrong_boot_or_plan_rejected(self):
        for field in ('boot_id', 'base_plan_sha256', 'new_plan_sha256', 'candidate_sha256'):
            bad = dict(self.approval, **{field: 'wrong'})
            with self.subTest(field=field), self.assertRaisesRegex(ValueError, 'identity mismatch'):
                preview.preview(self.context, bad, self.now)

    def test_expiry_boundary_rejected(self):
        approval = dict(self.approval, expires_at=self.now.isoformat())
        with self.assertRaisesRegex(ValueError, 'expired'):
            preview.preview(self.context, approval, self.now)

    def test_execute_always_rejected(self):
        with self.assertRaisesRegex(ValueError, 'execution disabled'):
            preview.preview(self.context, self.approval, self.now, action='execute')

    def test_mock_tools_and_sentinels_untouched(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            sentinel = root / 'stop'
            sentinel.write_text('operator stop')
            for name in ('app-data', 'data', 'webview-t-data'):
                (root / name).mkdir()
                (root / name / 'user').write_text(name + ': keep')
            calls = root / 'calls'
            for name in ('hdc', 'kill', 'pkill', 'rm', 'mv', 'uinput', 'aa', 'chcon', 'deploy_generation'):
                tool = root / name
                tool.write_text('#!/bin/sh\nprintf "%s\\n" "$0 $*" >> "$R2_CALLS"\nexit 99\n')
                tool.chmod(0o755)
            context = root / 'context.json'
            context.write_text(json.dumps(self.context))
            approval = root / 'approval.json'
            approval.write_text(json.dumps(dict(self.approval, boot_id='wrong')))
            before = {str(path.relative_to(root)): review.digest(path) for path in root.rglob('*') if path.is_file()}
            env = dict(os.environ, PATH=str(root) + ':' + os.environ.get('PATH', ''), R2_CALLS=str(calls),
                       PYTHONDONTWRITEBYTECODE='1')
            command = [sys.executable, str(review.HERE / 'preview.py'), '--context', str(context)]
            result = subprocess.run(command, env=env, capture_output=True, text=True)
            self.assertEqual(result.returncode, 0, result.stderr)
            rejected = subprocess.run(command + ['--authorization', str(approval)], env=env, capture_output=True, text=True)
            self.assertEqual(rejected.returncode, 2)
            self.assertFalse(calls.exists())
            after = {str(path.relative_to(root)): review.digest(path) for path in root.rglob('*') if path.is_file()}
            self.assertEqual(before, after)


class CandidateTests(unittest.TestCase):
    def test_real_checkpoint_owner_write_failure_is_blocker(self):
        import adversarial_checkpoint
        result = adversarial_checkpoint.run_owner_failure()
        self.assertEqual(result['status'], 'blocker')
        self.assertEqual(result['candidate_exit'], 0)
        self.assertEqual(result['state'].strip(), 'READY')
        self.assertEqual([call['command'] for call in result['launch_commands_after_failure']],
                         ['parent_tool', 'spawn_tool'])
        self.assertIn('Is a directory', result['stderr'])
        self.assertEqual(review.checkpoint_review()['status'], 'blocker')

    def test_missing_and_unpinned_pending(self):
        self.assertEqual(review.candidate_review()['status'], 'pending')
        self.assertEqual(review.candidate_review(__file__)['status'], 'pending')

    def test_known_defects_blocked(self):
        cases = ['uinput -T -d 600 1273', 'mv "$RUNTIME/app-data" archive',
                 'rm -rf "$RUNTIME/operator-selfheal-previous"', 'pkill appspawn-x',
                 'kill -9 4792', 'rm -f "$F/stop"']
        with tempfile.TemporaryDirectory() as directory:
            source = Path(directory) / 'candidate.sh'
            for code in cases:
                source.write_text('#!/bin/sh\n' + code + '\n')
                with self.subTest(code=code):
                    self.assertEqual(review.candidate_review(source, review.digest(source))['status'], 'blocker')

    def test_source_drift_blocked(self):
        self.assertEqual(review.candidate_review(__file__, '0' * 64)['status'], 'blocker')

    def test_safe_looking_text_cannot_self_accept(self):
        with tempfile.TemporaryDirectory() as directory:
            source = Path(directory) / 'candidate.sh'
            source.write_text('#!/bin/sh\necho pending\n')
            result = review.candidate_review(source, review.digest(source))
            self.assertEqual(result['status'], 'pending')
            self.assertFalse(result['offline_accept'])
            self.assertFalse(result['ui_signed'])


if __name__ == '__main__':
    unittest.main(verbosity=2)
