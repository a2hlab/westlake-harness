import copy
from contextlib import redirect_stdout
from datetime import datetime, timedelta, timezone
import json
import io
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

import acceptance
import collect
import install
from prepare import HERE, NEW, OLD, REPO, SERIAL, TARGETS, build, fingerprint, sha


BOOT = '11111111-1111-1111-1111-111111111111'
AFTER = '22222222-2222-2222-2222-222222222222'


def approved(action='apply'):
    return dict(approved_by='outer(claude)', serial=SERIAL, lane='cx-bms', boot_id=BOOT,
                expires_at=(datetime.now(timezone.utc) + timedelta(hours=1)).isoformat(),
                actions=[action], window_evidence='mock-only; not an actual authorization',
                files={name: sha(HERE / name) for name in ['install.py', 'remote-transaction.sh', 'plan.json', 'reference.json']})


def probe():
    rows = ['BOOT ' + BOOT, 'ROOT_RO']
    for target in TARGETS:
        rows.extend(['FILE ' + target, OLD, '0:0:755:1', 'u:object_r:system_lib_file:s0 ' + target])
    return '\n'.join(rows)


class Guards(unittest.TestCase):
    def test_archive_identity_drift_refuses(self):
        with patch('prepare.sha', return_value='0' * 64), self.assertRaises(ValueError):
            build(Path(os.environ.get('WORKSPACES', REPO.parent)))

    def test_provenance_pins_source_log_and_archive(self):
        document = json.loads((HERE / 'provenance.json').read_text())
        rows = document['verified_local_files']
        self.assertEqual(rows[1]['sha256'], NEW)
        self.assertTrue(any(row['role'] == 'complete_source_archive' for row in rows))
        self.assertTrue(any(row['path'].endswith('/build-r5.log') for row in rows))
        self.assertTrue(any(row['path'].endswith('/candidate-source/foundation/bundlemanager/bundle_framework/services/bundlemgr/src/installd/installd_operator.cpp') for row in rows))
        for row in document['unpacked_source_drift']:
            self.assertNotEqual(row['actual_sha256'], row['frozen_sha256'])

    def test_approval_valid_known_answer(self):
        install.check_approval(approved(), 'apply', BOOT, 'cx-bms')

    def test_wrong_serial_boot_expiry_and_input_rejected(self):
        for field, value in [('serial', '61b0657200000000000000000324012c'), ('boot_id', AFTER),
                             ('approved_by', None), ('expires_at', '2000-01-01T00:00:00+00:00'), ('files', {})]:
            with self.subTest(field=field), self.assertRaises(ValueError):
                document = approved()
                document[field] = value
                install.check_approval(document, 'apply', BOOT, 'cx-bms')

    def test_wrong_action_and_lane_rejected(self):
        for action, lane in [('reboot', 'cx-bms'), ('apply', 'other')]:
            with self.assertRaises(ValueError):
                install.check_approval(approved(), action, BOOT, lane)

    def test_probe_valid_and_drift_refused(self):
        self.assertEqual(install.parse_probe(probe(), {OLD})[0], BOOT)
        for bad in [probe().replace('ROOT_RO', ''), probe().replace(OLD, NEW),
                    probe().replace(':755:1', ':755:2'), probe().replace('system_lib_file', 'wrong_label'),
                    probe() + '\nMOUNT_REFUSE /system']:
            with self.assertRaises(ValueError):
                install.parse_probe(bad, {OLD})

    def test_dry_run_never_constructs_transport(self):
        with patch.object(sys, 'argv', ['install.py']), patch.object(install, 'sha', return_value=NEW), \
                patch.object(install, 'Transport', side_effect=AssertionError('device access')):
            install.main()

    def test_missing_approval_refuses_before_transport(self):
        with patch.object(sys, 'argv', ['install.py', '--execute']), patch.object(install, 'sha', return_value=NEW), \
                patch.object(install, 'Transport', side_effect=AssertionError('device access')), self.assertRaises(SystemExit):
            install.main()

    def test_one_command_other_lane_uses_approval_defaults(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            wrapper = root / 'mock-hdc'
            wrapper.write_text('#!/bin/sh\nexit 99\n')
            wrapper.chmod(0o755)
            approval = approved()
            approval.update(lane='cx-t0', hdc='mock-hdc', out='evidence')
            approval_file = root / 'approval.json'
            approval_file.write_text(json.dumps(approval))
            with patch.object(install, 'Transport') as factory, patch.object(install, 'transaction') as transaction, redirect_stdout(io.StringIO()):
                factory.return_value.shell.return_value = probe()
                transaction.side_effect = lambda transport, action, candidate, metadata, state, out: state.update(status='mock_only')
                install.main(['--serial', SERIAL, '--approval', str(approval_file), '--execute'])
                self.assertEqual(factory.call_args.args[0], wrapper)
                self.assertEqual(factory.call_args.args[2], 'cx-t0')
                self.assertEqual(factory.call_args.args[3], root / 'evidence')
                self.assertEqual(transaction.call_args.args[1], 'apply')

    def test_serial_refuses_before_any_transport(self):
        for serial in ['5cd1e3dd', '61b0657200000000000000000324012c', '5ea34a4500000000000000001123012c']:
            with patch.object(install, 'Transport', side_effect=AssertionError('device access')), self.assertRaises(ValueError):
                install.main(['--serial', serial, '--execute'])

    def test_one_command_dry_run_does_not_open_transport(self):
        with tempfile.TemporaryDirectory() as directory:
            approval_file = Path(directory) / 'approval.json'
            approval_file.write_text(json.dumps(approved()))
            with patch.object(install, 'Transport', side_effect=AssertionError('device access')), redirect_stdout(io.StringIO()) as output:
                install.main(['--serial', SERIAL, '--approval', str(approval_file)])
            self.assertFalse(json.loads(output.getvalue())['device_access'])

    def test_ambiguous_actions_or_foreign_lane_refuse(self):
        with tempfile.TemporaryDirectory() as directory:
            approval_file = Path(directory) / 'approval.json'
            approval = approved()
            for change, arguments in [({'actions': ['apply', 'reboot']}, []), ({'lane': 'cx-t0'}, ['--lane', 'cx-bms'])]:
                approval_file.write_text(json.dumps(dict(approval, **change)))
                with patch.object(install, 'Transport', side_effect=AssertionError('device access')), self.assertRaises(ValueError):
                    install.main(['--serial', SERIAL, '--approval', str(approval_file), '--execute', *arguments])

    def test_approval_path_expansion_and_unknown_variable(self):
        with patch.dict(os.environ, WORKSPACES='/mock/workspaces'):
            self.assertEqual(install.approval_path('$WORKSPACES/evidence', Path('/mock/approval.json')), Path('/mock/workspaces/evidence'))
        for value in [None, '', '$UNSET_SPARE_INSTALLER_PATH/file']:
            with self.assertRaises(ValueError):
                install.approval_path(value, Path('/mock/approval.json'))

    def test_wrong_lock_prevents_write(self):
        with tempfile.TemporaryDirectory() as directory:
            transport = install.Transport('mock-hdc', 'mock-note', 'cx-bms', Path(directory))
            transport.approval, transport.boot, transport.action = approved(), BOOT, 'apply'
            with patch.object(transport, 'run', return_value='another-lane 123'), \
                    patch.object(transport, 'shell', side_effect=AssertionError('write')), self.assertRaises(ValueError):
                transport.mutate('mount -o rw,remount /')

    def test_reference_digest_uses_61b_baseline_not_common(self):
        document = json.loads((HERE / 'reference.json').read_text())
        self.assertEqual(len(document['expected_paths']), 319)
        self.assertEqual(fingerprint(document['expected_paths'], document['reference_paths']['runtime']), '452447a4a0ba')
        self.assertEqual(fingerprint(document['expected_paths'], document['reference_paths']['boot']), 'ee927db88a67')


class ShellTransaction(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.remote = self.root / 'data/local/tmp/spare-installer-mock'
        self.remote.mkdir(parents=True)
        self.targets = [self.root / target.lstrip('/') for target in TARGETS]
        for index, target in enumerate(self.targets):
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes(b'original mock ELF')
            target.chmod(0o755)
            (self.remote / f'meta-{index}.txt').write_text('0:0:755:1\nu:object_r:system_lib_file:s0 ' + str(target) + '\n')
        self.original = sha(self.targets[0])
        (self.remote / 'candidate.so').write_bytes(b'candidate mock ELF')
        self.candidate = sha(self.remote / 'candidate.so')
        (self.root / 'boot').write_text(BOOT + '\n')
        self.mounts = self.root / 'mounts'
        self.mounts.write_text('mock / ext4 ro 0 0\n')
        self.bin = self.root / 'bin'
        self.bin.mkdir()
        shim = self.bin / 'shim'
        shim.write_text('''#!/usr/bin/env python3
import os, pathlib, stat, sys
name=pathlib.Path(sys.argv[0]).name
args=sys.argv[1:]
root=pathlib.Path(os.environ['MOCK_ROOT'])
with (root/'commands.txt').open('a') as stream: stream.write(name+' '+' '.join(args)+'\\n')
if name=='mount':
 mode='ro' if 'ro,remount' in args else 'rw'
 if os.environ.get('FAIL_MOUNT')==mode: sys.exit(9)
 (root/'mounts').write_text('mock / ext4 '+mode+' 0 0\\n')
elif name=='ls': print('u:object_r:system_lib_file:s0 '+args[-1])
elif name=='stat':
 info=pathlib.Path(args[-1]).stat()
 print('0:0:'+oct(stat.S_IMODE(info.st_mode))[2:]+':'+str(info.st_nlink))
elif name=='cp':
 if os.environ.get('FAIL_SECOND')=='1' and args[-1].endswith('platformsdk/libinstalls.z.so.spare-unify-new'): sys.exit(9)
 os.execv('/bin/cp',['/bin/cp']+args)
elif name in ['chown','chcon','sync']: pass
else: sys.exit(99)
''')
        shim.chmod(0o755)
        for name in ['mount', 'ls', 'stat', 'cp', 'chown', 'chcon', 'sync']:
            (self.bin / name).symlink_to(shim)
        script = (HERE / 'remote-transaction.sh').read_text()
        script = script.replace('/proc/sys/kernel/random/boot_id', str(self.root / 'boot'))
        script = script.replace('/proc/mounts', str(self.mounts))
        script = script.replace('/system/lib64', str(self.root / 'system/lib64'))
        script = script.replace('/data/local/tmp', str(self.root / 'data/local/tmp'))
        script = script.replace(OLD, self.original).replace(NEW, self.candidate)
        self.script = self.root / 'transaction.sh'
        self.script.write_text(script)

    def run_shell(self, action, **extra):
        environment = dict(os.environ, MOCK_ROOT=str(self.root), PATH=str(self.bin) + os.pathsep + os.environ['PATH'], **extra)
        return subprocess.run(['/bin/sh', str(self.script), action, str(self.remote), BOOT], env=environment,
                              capture_output=True, text=True)

    def test_backup_apply_and_rollback(self):
        self.assertEqual(self.run_shell('backup').returncode, 0)
        result = self.run_shell('apply')
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertTrue(all(sha(target) == self.candidate for target in self.targets))
        self.assertIn(' ro ', self.mounts.read_text())
        result = self.run_shell('rollback')
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertTrue(all(sha(target) == self.original for target in self.targets))
        self.assertIn(' ro ', self.mounts.read_text())

    def test_partial_failure_readonly_and_explicit_rollback(self):
        self.assertEqual(self.run_shell('backup').returncode, 0)
        result = self.run_shell('apply', FAIL_SECOND='1')
        self.assertNotEqual(result.returncode, 0)
        self.assertIn(' ro ', self.mounts.read_text())
        self.assertEqual(sha(self.targets[0]), self.candidate)
        self.assertEqual(sha(self.targets[1]), self.original)
        self.assertFalse(Path(str(self.targets[1]) + '.spare-unify-new').exists())
        self.assertEqual(self.run_shell('rollback').returncode, 0)

    def test_remount_failure_still_attempts_ro(self):
        self.assertEqual(self.run_shell('backup').returncode, 0)
        result = self.run_shell('apply', FAIL_MOUNT='rw')
        self.assertNotEqual(result.returncode, 0)
        self.assertIn('mount -o ro,remount /', (self.root / 'commands.txt').read_text())

    def test_ro_restore_failure_is_not_success(self):
        self.assertEqual(self.run_shell('backup').returncode, 0)
        result = self.run_shell('apply', FAIL_MOUNT='ro')
        self.assertEqual(result.returncode, 24)
        self.assertIn('ROOT_RO_RESTORE_FAILED', result.stderr)

    def test_wrong_candidate_and_backups_no_rw(self):
        self.assertEqual(self.run_shell('backup').returncode, 0)
        (self.remote / 'candidate.so').write_bytes(b'wrong')
        self.assertNotEqual(self.run_shell('apply').returncode, 0)
        self.assertNotIn('rw,remount', (self.root / 'commands.txt').read_text())
        (self.remote / 'backup/0.so').write_bytes(b'wrong')
        self.assertNotEqual(self.run_shell('rollback').returncode, 0)


class HostPipeline(unittest.TestCase):
    def test_host_backups_verified_before_system_write(self):
        with tempfile.TemporaryDirectory() as directory:
            out = Path(directory)
            events = []

            class MockIO:
                boot = BOOT

                def mutate(self, command):
                    events.append(('mutate', command))

                def send(self, source, target):
                    events.append(('send', target))

                def recv(self, source, target):
                    events.append(('recv', source))
                    target.write_bytes(b'mock backup')

                def reference(self, expected):
                    events.append(('reference', sorted(expected)))

            state = dict(remote='/data/local/tmp/spare-installer-mock')
            with patch.object(install, 'sha', return_value=OLD):
                install.transaction(MockIO(), 'apply', out / 'candidate.so', ['mock0', 'mock1'], state, out)
            apply_index = next(index for index, event in enumerate(events) if event[0] == 'mutate' and ' apply ' in event[1])
            received = [index for index, event in enumerate(events) if event[0] == 'recv']
            self.assertEqual(len(received), 2)
            self.assertTrue(all(index < apply_index for index in received))
            events.clear()
            with patch.object(install, 'sha', return_value='0' * 64), self.assertRaises(ValueError):
                install.transaction(MockIO(), 'apply', out / 'candidate.so', ['mock0', 'mock1'], state, out)
            self.assertFalse(any(event[0] == 'mutate' and ' apply ' in event[1] for event in events))

    def test_collector_readonly_command_inventory(self):
        reference = json.loads((HERE / 'reference.json').read_text())
        seen = []

        def fake_run(argv, **kwargs):
            self.assertEqual(argv[1:4], ['-t', SERIAL, 'shell'])
            command = argv[4]
            seen.append(command)
            if command.startswith('sha256sum '):
                output = '\n'.join(reference['expected_paths'][path] + '  ' + path for path in command.split()[1:])
            elif command == 'cat /proc/sys/kernel/random/boot_id':
                output = BOOT
            else:
                self.assertIn(command, ['cat /proc/mounts', 'cat /proc/self/mountinfo', 'ps -A -o PID,PPID,UID,NAME',
                                        'bm dump -a', 'param get sys.westlake.demo.u13.ready', 'cat /proc/uptime',
                                        'cat /proc/1/attr/current', 'getenforce', 'dmesg'])
                output = 'mock readonly stdout'
            return subprocess.CompletedProcess(argv, 0, stdout=output, stderr='')

        with tempfile.TemporaryDirectory() as directory, patch.object(sys, 'argv', ['collect.py', '--hdc', 'mock-hdc', '--out', str(Path(directory) / 'reads')]), \
                patch.object(collect.subprocess, 'run', side_effect=fake_run):
            collect.main()
            result = json.loads((Path(directory) / 'reads/readonly-collection.json').read_text())
            self.assertEqual(result['board_mutations'], [])
            self.assertIsNone(result['visual_verdict'])
            self.assertEqual(result['fingerprints']['runtime'], '452447a4a0ba')


class Acceptance(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        expected = json.loads((HERE / 'reference.json').read_text())['expected_paths']
        self.observation = dict(serial=SERIAL, boot_before=BOOT, boot_after=AFTER, host_recovery_actions=[],
                                hashes=expected, root_readonly=True, autonomous_mount_count=56, installed_package_count=128,
                                installer_owner_aliases_equal=True, installer_stale_mappings=False,
                                appspawn_x=dict(pid=100, ppid=1, uid=0), appspawn_service_invalid=False,
                                parent_child_views_equal=True, single_art_owner=True)
        self.signoff = dict(serial=SERIAL, approved_by='outer(claude)', boot_id=AFTER, controls={})
        for key in ['helloworld', 'zigzag']:
            path = self.root / (key + '.jpeg')
            path.write_bytes(b'mocked image; never board evidence')
            self.signoff['controls'][key] = dict(path=path.name, sha256=sha(path), verdict='lit', seconds_after_launch=20)

    def test_correct_offline_fixture(self):
        self.assertEqual(acceptance.verify(self.observation, self.signoff, self.root)['paths'], 319)

    def acceptance_approval(self):
        observation = self.root / 'observation.json'
        signoff = self.root / 'signoff.json'
        observation.write_text(json.dumps(self.observation))
        signoff.write_text(json.dumps(self.signoff))
        document = dict(approved_by='outer(claude)', serial=SERIAL, boot_id=AFTER,
                        actions=['acceptance'], window_evidence='mock only; no real acceptance',
                        files={name: sha(HERE / name) for name in ['acceptance.py', 'install.py', 'reference.json']},
                        observation=dict(path=observation.name, sha256=sha(observation)),
                        signoff=dict(path=signoff.name, sha256=sha(signoff)))
        approval_file = self.root / 'acceptance-approval.json'
        approval_file.write_text(json.dumps(document))
        return approval_file, document

    def test_one_command_acceptance_bound_evidence(self):
        approval_file, document = self.acceptance_approval()
        with redirect_stdout(io.StringIO()) as output:
            acceptance.main(['--serial', SERIAL, '--approval', str(approval_file)])
        self.assertEqual(json.loads(output.getvalue())['status'], 'autonomous_reboot_verified_outer_lit')

    def test_one_command_acceptance_evidence_and_binding_drift(self):
        approval_file, document = self.acceptance_approval()
        for field, value in [('files', {}), ('boot_id', BOOT), ('serial', '61b0657200000000000000000324012c')]:
            approval_file.write_text(json.dumps(dict(document, **{field: value})))
            with self.subTest(field=field), self.assertRaises(ValueError):
                acceptance.main(['--serial', SERIAL, '--approval', str(approval_file)])
        approval_file.write_text(json.dumps(document))
        (self.root / 'observation.json').write_text('{}')
        with self.assertRaises(ValueError):
            acceptance.main(['--serial', SERIAL, '--approval', str(approval_file)])

    def test_one_command_acceptance_cannot_override_or_relax_autonomy(self):
        self.observation['host_recovery_actions'] = ['fresh native ticket']
        approval_file, document = self.acceptance_approval()
        with self.assertRaisesRegex(ValueError, 'not autonomous'):
            acceptance.main(['--serial', SERIAL, '--approval', str(approval_file)])
        with self.assertRaises(ValueError):
            acceptance.main(['--serial', SERIAL, '--approval', str(approval_file), '--signoff', 'different.json'])

    def test_no_daemon_even_with_exact_fingerprint_refuses(self):
        self.observation['appspawn_x'] = {}
        with self.assertRaises(ValueError):
            acceptance.verify(self.observation, self.signoff, self.root)

    def test_white_or_missing_signature_refuses(self):
        for changes in [('verdict', 'white'), ('seconds_after_launch', 10), ('sha256', '0' * 64)]:
            signoff = copy.deepcopy(self.signoff)
            signoff['controls']['zigzag'][changes[0]] = changes[1]
            with self.assertRaises(ValueError):
                acceptance.verify(self.observation, signoff, self.root)

    def test_same_boot_host_repair_or_path_drift_refuses(self):
        for field, value in [('boot_after', BOOT), ('host_recovery_actions', ['Mac replay']), ('hashes', {}),
                             ('appspawn_service_invalid', True)]:
            observation = copy.deepcopy(self.observation)
            observation[field] = value
            with self.assertRaises(ValueError):
                acceptance.verify(observation, self.signoff, self.root)


if __name__ == '__main__':
    unittest.main()
