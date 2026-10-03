import contextlib
import copy
import io
import json
import os
from pathlib import Path
import subprocess
import tempfile
import unittest
from unittest.mock import patch

import return_61b as recovery

HERE = Path(__file__).resolve().parent
NEW_BOOT = 'aaaaaaaa-bbbb-cccc-dddd-eeeeeeeeeeee'


def fixture(root):
    workspaces = root / 'ws'
    source = workspaces / 'westlake-harness-u7-executor/window2/61b'
    source.mkdir(parents=True)
    journal = source / 'transaction/transaction/journal.json'
    journal.parent.mkdir(parents=True)
    recovery.save(journal, dict(status='active_verified', serial=recovery.SERIAL, boot_id=recovery.OLD_BOOT))
    hook = source / 'window_hook.py'
    hook.write_text('fixture hook; never executed')
    binding = copy.deepcopy(json.loads((HERE / 'binding.json').read_text()))
    portable = lambda path: '$WORKSPACES/' + str(path.relative_to(workspaces))
    binding.update(journal=portable(journal), hook=portable(hook), smoke_spec=portable(source / 'smoke-restored-61b.json'),
        pinned_files=[dict(path=portable(path), sha256=recovery.sha(path)) for path in [journal, hook]])
    output = root / 'out'
    output.mkdir()
    return workspaces, binding, output


class MockHdcAndExecutor:
    def __init__(self, binding, new_boot=False, problem=None):
        self.binding = binding
        self.boot = NEW_BOOT if new_boot else recovery.OLD_BOOT
        self.problem = problem
        self.calls = []
        self.unlocked = False
        self.boot_reads = 0

    def run(self, command, **kwargs):
        self.calls.append(command)
        code, stdout, stderr = 0, b'', b''
        if command[0] == 'mock-hdc':
            if command[1:] == ['list', 'targets']:
                stdout = (recovery.SERIAL + '\n').encode() if self.problem != 'offline' else b''
            elif 'recv' in command:
                if self.problem != 'empty-receive':
                    Path(command[-1]).write_text('mock cppcrash evidence')
            else:
                self.assert_serial(command)
                if 'boot_id' in command[-1]:
                    self.boot_reads += 1
                    stdout = (self.boot if not (self.problem == 'boot-drift' and self.boot_reads > 1) else NEW_BOOT).encode()
                    if self.problem == 'empty-boot':
                        return subprocess.CompletedProcess(command, 0, b'', b'')
                elif '/proc/uptime' in command[-1]:
                    stdout = b'123.45 678.90'
                elif 'find /data/log/faultlog' in command[-1]:
                    stdout = (str(self.binding['incident_start_epoch'] + 300)
                        + ' /data/log/faultlog/temp/cppcrash-foundation-20261003135000\n').encode()
                elif 'hilog -x' in command[-1]:
                    stdout = b'mock pre-recovery hilog'
                else:
                    raise AssertionError(command)
                stdout += ('\n' + recovery.MARKER + '=0\n').encode()
        elif '--rollback' in command or '--restore-baseline' in command:
            if self.problem == 'executor-fail':
                code, stderr = 2, b'mock replay/rollback refused'
            else:
                recovery.save(Path(command[command.index('--out') + 1]),
                    dict(status='baseline_restored' if '--restore-baseline' in command else 'rolled_back'))
        elif '--verify-base' in command:
            destination = Path(command[command.index('--root') + 1])
            destination.mkdir()
            report = dict(state='U13', identity_assertions=321, unique_paths=319, diff={}, absent=[],
                fingerprints=self.binding['fingerprints'], boot_id=self.boot)
            if self.problem == 'identity-diff':
                report['diff'] = {'/system/bin/appspawn-x': 'wrong'}
            if self.problem == 'identity-count':
                report['identity_assertions'] = 320
            if self.problem == 'common-fingerprint':
                report['fingerprints'] = copy.deepcopy(self.binding['fingerprints'])
                report['fingerprints']['runtime']['sha256_12'] = '821de739cf81'
            recovery.save(destination / 'identity.json', report)
            recovery.save(destination / 'process-view.json', dict(parent=100, child=101,
                maps=dict(passed=self.problem != 'view-fail')))
        elif 'activation_smoke.py' in command[1]:
            destination = Path(command[command.index('--out') + 1])
            destination.mkdir()
            keys = ['helloworld'] if self.problem == 'missing-zigzag' else ['helloworld', 'zigzag']
            recovery.save(destination / 'smoke-result.json', dict(serial=recovery.SERIAL,
                passed=self.problem != 'smoke-fail', checks=[dict(check='controls', key=key, ok=True) for key in keys]))
        elif 'held' in command:
            if self.unlocked:
                code = 0 if self.problem == 'ambiguous-release' else 1
            else:
                lane = 'other' if self.problem == 'wrong-owner' else 'cx-t0'
                timestamp = '2026-10-04T08:00:00+0800' if self.problem == 'wrong-window' else self.binding['held_since']
                stdout = (lane + ' 999 ' + timestamp + '\n').encode()
        elif 'unlock' in command:
            self.unlocked = True
        else:
            raise AssertionError('Unexpected external command: ' + str(command))
        return subprocess.CompletedProcess(command, code, stdout, stderr)

    def assert_serial(self, command):
        assert command[command.index('-t') + 1] == recovery.SERIAL


class ReturnTests(unittest.TestCase):
    def run_case(self, root, problem=None, new_boot=False):
        workspaces, binding, output = fixture(root)
        backend = MockHdcAndExecutor(binding, new_boot, problem)
        recorder = recovery.Recorder(output)
        with patch.dict(os.environ, {'LAB_HOME': '/fixture/lab'}), patch.object(subprocess, 'run', side_effect=backend.run):
            result = recovery.recover(binding, workspaces, output, 'mock-hdc', recorder)
        return result, backend, output, binding

    def test_default_preview_never_calls_external_or_writes(self):
        with patch.object(subprocess, 'run', side_effect=AssertionError('no external calls')), contextlib.redirect_stdout(io.StringIO()) as text:
            self.assertEqual(recovery.main([]), 0)
        self.assertFalse(json.loads(text.getvalue())['board_access'])

    def test_same_boot_original_rollback_and_evidence_before_write(self):
        with tempfile.TemporaryDirectory() as temporary:
            result, backend, output, binding = self.run_case(Path(temporary))
            command = next(command for command in backend.calls if '--rollback' in command)
            self.assertIn('transaction/transaction/journal.json', command[command.index('--journal') + 1])
            self.assertNotIn('--package', command)
            before = backend.calls[:backend.calls.index(command)]
            self.assertTrue(any('recv' in row for row in before))
            self.assertTrue(any('hilog -x' in row[-1] for row in before))
            self.assertTrue(backend.unlocked)
            self.assertFalse(result['new_boot'])
            self.assertEqual(result['identity_assertions'], 321)
            self.assertTrue((output / 'commands.json').is_file())

    def test_new_boot_existing_restore_baseline_fresh_journal(self):
        with tempfile.TemporaryDirectory() as temporary:
            result, backend, output, binding = self.run_case(Path(temporary), new_boot=True)
            command = next(command for command in backend.calls if '--restore-baseline' in command)
            self.assertIn('--from-journal', command)
            self.assertEqual(command[command.index('--journal') + 1], str(output / 'replay-journal.json'))
            self.assertFalse(any('--rollback' in row for row in backend.calls))
            self.assertTrue(result['new_boot'])
            self.assertIn('候选的 bind 层可能', json.loads((output / 'readonly-evidence.json').read_text())['note'])

    def assert_refused(self, problem, new_boot=False):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            workspaces, binding, output = fixture(root)
            backend = MockHdcAndExecutor(binding, new_boot, problem)
            with patch.dict(os.environ, {'LAB_HOME': '/fixture/lab'}), patch.object(subprocess, 'run', side_effect=backend.run):
                with self.assertRaises(RuntimeError):
                    recovery.recover(binding, workspaces, output, 'mock-hdc', recovery.Recorder(output))
            self.assertFalse(backend.unlocked)
            self.assertTrue((output / 'commands.json').is_file())

    def test_offline_empty_targets_refuses(self):
        self.assert_refused('offline')

    def test_hdcrc0_missing_remote_marker_refuses(self):
        self.assert_refused('empty-boot')

    def test_fault_receive_empty_refuses(self):
        self.assert_refused('empty-receive')

    def test_original_rollback_failure_preserves_lock(self):
        self.assert_refused('executor-fail')

    def test_new_boot_replay_failure_preserves_lock(self):
        self.assert_refused('executor-fail', new_boot=True)

    def test_identity_diff_preserves_lock(self):
        self.assert_refused('identity-diff')

    def test_assertion_count_preserves_lock(self):
        self.assert_refused('identity-count')

    def test_common_fingerprint_cannot_replace61b(self):
        self.assert_refused('common-fingerprint')

    def test_parent_child_view_failure_preserves_lock(self):
        self.assert_refused('view-fail')

    def test_smoke_failure_preserves_lock(self):
        self.assert_refused('smoke-fail')

    def test_missing_zigzag_control_preserves_lock(self):
        self.assert_refused('missing-zigzag')

    def test_boot_change_during_collection_preserves_lock(self):
        self.assert_refused('boot-drift')

    def test_wrong_lock_owner_refuses(self):
        self.assert_refused('wrong-owner')

    def test_same_lane_different_window_lock_refuses(self):
        self.assert_refused('wrong-window')

    def test_ambiguous_unlock_is_not_reported_success(self):
        with tempfile.TemporaryDirectory() as temporary:
            workspaces, binding, output = fixture(Path(temporary))
            backend = MockHdcAndExecutor(binding, problem='ambiguous-release')
            with patch.dict(os.environ, {'LAB_HOME': '/fixture/lab'}), patch.object(subprocess, 'run', side_effect=backend.run):
                with self.assertRaisesRegex(RuntimeError, 'not confirmed empty'):
                    recovery.recover(binding, workspaces, output, 'mock-hdc', recovery.Recorder(output))
            self.assertTrue(backend.unlocked)

    def test_pinned_journal_drift_refuses_before_external(self):
        with tempfile.TemporaryDirectory() as temporary:
            workspaces, binding, output = fixture(Path(temporary))
            recovery.expand(binding['journal'], workspaces).write_text('{}')
            with self.assertRaisesRegex(RuntimeError, 'source drift'):
                recovery.verify_bindings(binding, workspaces)

    def test_cli_failure_archives_original_outputs_and_keeps_lock(self):
        with tempfile.TemporaryDirectory() as temporary:
            workspaces, binding, output = fixture(Path(temporary))
            output.rmdir()
            local = Path(temporary) / 'local'
            local.mkdir()
            recovery.save(local / 'binding.json', binding)
            (local / 'return_61b.py').write_text('mock script snapshot')
            backend = MockHdcAndExecutor(binding, problem='executor-fail')
            with patch.object(recovery, 'HERE', local), patch.dict(os.environ,
                    {'WORKSPACES': str(workspaces), 'LAB_HOME': '/fixture/lab'}), \
                    patch.object(subprocess, 'run', side_effect=backend.run), contextlib.redirect_stderr(io.StringIO()):
                self.assertEqual(recovery.main(['--outer-execute', '--out', str(output), '--hdc', 'mock-hdc']), 2)
            report = json.loads((output / 'result.json').read_text())
            self.assertFalse(report['unlock_attempted'])
            self.assertFalse(backend.unlocked)
            commands = json.loads((output / 'commands.json').read_text())
            failure = commands[-1]
            self.assertEqual((output / failure['stderr']).read_bytes(), b'mock replay/rollback refused')

    def test_cli_success_only_prints_followups(self):
        with tempfile.TemporaryDirectory() as temporary:
            workspaces, binding, output = fixture(Path(temporary))
            output.rmdir()
            local = Path(temporary) / 'local'
            local.mkdir()
            recovery.save(local / 'binding.json', binding)
            (local / 'return_61b.py').write_text('mock script snapshot')
            backend = MockHdcAndExecutor(binding)
            with patch.object(recovery, 'HERE', local), patch.dict(os.environ,
                    {'WORKSPACES': str(workspaces), 'LAB_HOME': '/fixture/lab'}), \
                    patch.object(subprocess, 'run', side_effect=backend.run), contextlib.redirect_stdout(io.StringIO()) as text:
                self.assertEqual(recovery.main(['--outer-execute', '--out', str(output), '--hdc', 'mock-hdc']), 0)
            self.assertIn('第6次补测', text.getvalue())
            self.assertIn('ALL THREE UNLOCK', text.getvalue())
            self.assertFalse(any('--apply' in command or 'apply-all.sh' in ' '.join(command) for command in backend.calls))

    def test_incident_crash_selection_mtime_or_filename(self):
        binding = json.loads((HERE / 'binding.json').read_text())
        start, end = binding['incident_start_epoch'], binding['incident_end_epoch']
        lines = [f'{start} /data/log/faultlog/cppcrash-first',
            f'{end} /data/log/faultlog/jscrash-last',
            f'{start - 10000} /data/log/faultlog/cppcrash-20261003135000',
            f'{end + 1} /data/log/faultlog/cppcrash-outside',
            f'{start} /data/log/faultlog/not-crash']
        self.assertEqual(len(recovery.fault_files('\n'.join(lines), start, end)), 3)

    def test_unsafe_fault_inventory_refuses(self):
        with self.assertRaisesRegex(RuntimeError, 'Unsafe'):
            recovery.fault_files('1 /data/log/faultlog/../../etc/cppcrash', 0, 2)


if __name__ == '__main__':
    unittest.main()
