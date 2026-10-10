import contextlib
import io
import json
from pathlib import Path
import re
import subprocess
import tempfile
import unittest
from unittest import mock

import probe


BOOT = '31259bd5-a7ff-416f-bf5a-248dbef17688'
OTHER_BOOT = '15c1ab46-1111-2222-3333-444444444444'
SERIALS = sorted(probe.lab_paths.boards('oh'))
MOUNTS = '\n'.join([
    '1 0 8:1 / / rw,relatime - ext4 /dev/root rw',
    '2 1 8:2 /seq1 /system/android rw,nosuid - ext4 /dev/data rw',
    '3 2 8:2 /seq4 /system/android/lib64/liboh_adapter_bridge.so rw,noexec - ext4 /dev/data rw',
]) + '\n'


def stat(pid, ppid, ticks=100):
    return str(pid) + ' (app name with spaces) ' + ' '.join(['S', str(ppid)] + ['0'] * 17 + [str(ticks)])


class FixtureTransport:
    def __init__(self, missing_child=False, boot_drift=False, pid_reuse=False,
                 remote_failure=False, missing_marker=False, mount_drift=False, foreign=False):
        self.commands = []
        self.counts = {}
        self.missing_child, self.boot_drift, self.pid_reuse = missing_child, boot_drift, pid_reuse
        self.remote_failure, self.missing_marker = remote_failure, missing_marker
        self.mount_drift, self.foreign = mount_drift, foreign

    def run(self, wrapped):
        command = wrapped.split('( ', 1)[1].split(' ); probe_rc=', 1)[0]
        self.commands.append(command)
        self.counts[command] = self.counts.get(command, 0) + 1
        count = self.counts[command]
        marker = re.search(r'__SEALED_PROBE_RC_[a-f0-9]+__', wrapped)[0]
        code, error = 0, b''
        if command == 'cat ' + probe.BOOT:
            text = OTHER_BOOT if self.boot_drift and count == 2 else BOOT
        elif command == 'getenforce':
            text = 'Enforcing'
        elif command == 'ps -A -o PID,PPID,NAME':
            text = 'PID PPID NAME\n1 0 init\n100 1 appspawn-x\n'
            if not self.missing_child:
                text += '101 100 com.example.helloworld\n'
            if self.foreign:
                text += '900 1 unrelated\n'
        elif command == 'cat ' + probe.RECEIPT:
            text = 'state=READY\nboot_id=' + BOOT + '\nlayers=56\n'
        elif command.endswith('/stat'):
            pid = int(command.split('/')[2])
            text = stat(pid, {1: 0, 100: 1, 101: 100}[pid],
                        101 if self.pid_reuse and pid == 101 and count == 2 else 100)
        elif command.endswith('/mountinfo'):
            text = MOUNTS + ('4 1 8:1 / /new rw - ext4 /dev/root rw\n'
                             if self.mount_drift and count == 2 else '')
        elif command.endswith('/status'):
            pid = int(command.split('/')[2])
            text = 'PPid:\t' + str({1: 0, 100: 1, 101: 100}[pid]) + '\nUid:\t0 0 0 0\nGid:\t0 0 0 0\n'
        elif command.endswith('/cmdline'):
            text = '/system/bin/appspawn-x\x00'
        elif command.endswith('/attr/current'):
            text = 'u:r:appspawn:s0'
        elif command.endswith('/ns/mnt'):
            text = 'mnt:[1234]'
        elif command.endswith('/exe'):
            text = '/system/bin/init' if '/proc/1/' in command else '/system/bin/appspawn-x'
        elif command.startswith('sha256sum '):
            text = 'a' * 64 + '  ' + command.split(' ', 1)[1]
            if self.remote_failure:
                code, text, error = 1, '', b'sha256sum: permission denied'
        elif command.startswith('ls -ldnZ '):
            text = '-rwxr-xr-x 1 0 0 u:object_r:system_lib_file:s0 123 ' + command.split(' ', 2)[2]
        else:
            raise AssertionError('unexpected command: ' + command)
        stdout = text.encode() + b'\n'
        if not self.missing_marker:
            stdout += ('\n' + marker + str(code) + '\n').encode()
        return 0, stdout, error


class KnownAnswers(unittest.TestCase):
    def setUp(self):
        self.directory = tempfile.TemporaryDirectory()
        self.addCleanup(self.directory.cleanup)
        self.root = Path(self.directory.name)

    def capture(self, transport=None, name='capture', **kwargs):
        return probe.capture(transport or FixtureTransport(), SERIALS[0], self.root / name, **kwargs)

    def test_complete_fixture_and_boot_binding(self):
        result = self.capture()
        self.assertEqual(result['exit_code'], 0)
        self.assertTrue(result['boot_stable'])
        self.assertTrue(result['recover_receipt']['current_boot_match'])
        self.assertEqual(result['selected'], dict(host_pids=[100], child_pids=[101]))
        self.assertEqual([row['role'] for row in result['processes']], ['init', 'host', 'child'])
        bridge = result['processes'][2]['artifacts'][0]
        self.assertEqual(bridge['observed_via'], '/proc/101/root' + probe.TARGETS[0])
        self.assertEqual(bridge['label'], 'u:object_r:system_lib_file:s0')
        self.assertTrue(bridge['covering_mounts'][0]['noexec'])
        self.assertEqual(probe.load_report(self.root / 'capture/probe.json')['serial'], SERIALS[0])

    def test_dry_run_never_constructs_transport(self):
        factory = mock.Mock(side_effect=AssertionError('no board contact allowed'))
        with contextlib.redirect_stdout(io.StringIO()) as output:
            code = probe.main(['--serial', SERIALS[0]], factory)
        self.assertEqual(code, 0)
        self.assertFalse(json.loads(output.getvalue())['board_access'])
        factory.assert_not_called()

    def test_read_only_command_allowlist(self):
        transport = FixtureTransport()
        self.capture(transport)
        for command in transport.commands:
            self.assertIn(command.split()[0], ('cat', 'ls', 'sha256sum', 'readlink', 'ps', 'getenforce'))
            self.assertNotRegex(command, r'\b(mount|umount|boot|chcon|chmod|kill|aa|bm|param|hilog)\b')
        with self.assertRaises(ValueError):
            probe.read_command('chcon', probe.TARGETS[0])
        with self.assertRaises(ValueError):
            probe.read_command('cat', '/proc/1/../2/status')

    def test_three_boards_same_scope_and_offline_matrix(self):
        paths = []
        for serial in SERIALS:
            result = probe.capture(FixtureTransport(), serial, self.root / serial)
            self.assertEqual(result['protocol_sha256'], probe.PROTOCOL_SHA)
            paths.append(self.root / serial / 'probe.json')
        result = probe.compare(paths)
        self.assertTrue(result['complete'])
        self.assertEqual(len(result['matrix']), 27)
        self.assertTrue(all(row['comparable'] for row in result['matrix']))
        self.assertEqual(result['init_differences'], [])

    def test_comparison_shows_known_noexec_delta(self):
        class NoRestrictions(FixtureTransport):
            def run(self, command):
                code, stdout, stderr = super().run(command)
                return code, stdout.replace(b'rw,noexec', b'rw').replace(b'rw,nosuid', b'rw'), stderr
        probe.capture(FixtureTransport(), SERIALS[0], self.root / 'first')
        probe.capture(NoRestrictions(), SERIALS[1], self.root / 'second')
        result = probe.compare([self.root / 'first/probe.json', self.root / 'second/probe.json'])
        self.assertEqual(len(result['init_differences']), 2)
        self.assertTrue(all(row['field'] == 'mount_restrictions' for row in result['init_differences']))

    def test_remote_exit_wrapper_with_real_local_shell_only(self):
        class LocalShell:
            def run(self, command):
                result = subprocess.run(['/bin/sh', '-c', command], capture_output=True)
                return result.returncode, result.stdout, result.stderr
        reads = probe.Reads(LocalShell(), self.root / 'local-shell')
        self.assertIsNotNone(reads.read('good', probe.read_command('cat', '/dev/null')))
        self.assertIsNone(reads.read('bad', probe.read_command('cat', '/dev/null/no-such-file')))
        self.assertEqual(reads.items['bad']['host_exit'], 0)
        self.assertNotEqual(reads.items['bad']['remote_exit'], 0)

    def test_missing_child_is_unknown_not_pass(self):
        result = self.capture(FixtureTransport(missing_child=True))
        self.assertEqual(result['exit_code'], 1)
        self.assertFalse(result['observations_complete'])
        comparison = probe.compare([self.root / 'capture/probe.json'])
        self.assertFalse(comparison['complete'])
        self.assertIn('NOT-COMPARABLE', comparison['unavailable'][0]['warnings'][0])

    def test_boot_drift_rejected(self):
        result = self.capture(FixtureTransport(boot_drift=True))
        self.assertEqual(result['exit_code'], 2)
        self.assertFalse(result['boot_stable'])
        self.assertFalse(any(row['comparable'] for row in probe.compare([self.root / 'capture/probe.json'])['matrix']))

    def test_child_pid_reuse_rejected(self):
        result = self.capture(FixtureTransport(pid_reuse=True))
        self.assertEqual(result['exit_code'], 1)
        self.assertFalse(result['processes'][2]['pid_stable'])

    def test_mountinfo_change_rejected(self):
        result = self.capture(FixtureTransport(mount_drift=True))
        self.assertEqual(result['exit_code'], 1)
        self.assertFalse(result['processes'][2]['mountinfo_stable'])

    def test_covering_mount_boundary_and_stacked_rows(self):
        self.assertEqual(probe.covering_mounts(MOUNTS, '/system/android-extra/file')[0]['id'], '1')
        runtime = probe.covering_mounts(MOUNTS, probe.TARGETS[1])[0]
        self.assertTrue(runtime['nosuid'])
        self.assertFalse(runtime['noexec'])
        stacked = MOUNTS + '4 2 8:2 /seq5 ' + probe.TARGETS[0] + ' rw,nosuid - ext4 /dev/data rw\n'
        self.assertEqual(len(probe.covering_mounts(stacked, probe.TARGETS[0])), 2)
        escaped = '7 1 8:2 /source\\040name /target\\040name rw - ext4 /dev/data rw\n'
        self.assertEqual(probe.covering_mounts(escaped, '/target name/file')[0]['root'], '/source name')

    def test_host_zero_remote_failure_not_pass(self):
        result = self.capture(FixtureTransport(remote_failure=True))
        self.assertEqual(result['exit_code'], 1)
        item = result['items']['child-101-file-0-sha']
        self.assertEqual(item['host_exit'], 0)
        self.assertEqual(item['remote_exit'], 1)
        self.assertIsNone(result['processes'][2]['artifacts'][0]['sha256'])
        self.assertIn(b'permission denied', (self.root / 'capture' / item['stderr_raw']).read_bytes())

    def test_missing_remote_sentinel_not_pass(self):
        result = self.capture(FixtureTransport(missing_marker=True))
        self.assertEqual(result['exit_code'], 2)
        self.assertIsNone(result['items']['boot-before']['remote_exit'])

    def test_explicit_processes_and_foreign_child_rejected(self):
        result = self.capture(host_pids=[100], child_pids=[101])
        self.assertEqual(result['exit_code'], 0)
        result = self.capture(FixtureTransport(foreign=True), name='foreign', host_pids=[100], child_pids=[900])
        self.assertEqual(result['exit_code'], 1)
        self.assertIn('not a direct child', result['warnings'][0])

    def test_host_named_child_not_misidentified_as_second_host(self):
        rows = probe.process_rows('100 1 appspawn-x\n101 100 appspawn-x\n102 100 helloworld\n')
        self.assertEqual(probe.select_processes(rows), ([100], [101, 102]))
        with self.assertRaisesRegex(ValueError, 'duplicate explicit PID'):
            probe.select_processes(rows, [100, 100])

    def test_unknown_serial_and_pid_refused_without_contact(self):
        factory = mock.Mock()
        with contextlib.redirect_stderr(io.StringIO()):
            self.assertEqual(probe.main(['--serial', '5ea;boot'], factory), 2)
            self.assertEqual(probe.main(['--serial', SERIALS[0], '--child-pid', '1'], factory), 2)
            self.assertEqual(probe.main(['--serial', SERIALS[0], '--serial', SERIALS[1], '--child-pid', '101'], factory), 2)
        factory.assert_not_called()

    def test_same_out_supports_repeated_and_multiple_boards(self):
        arguments = ['--capture', '--out', str(self.root)]
        for serial in SERIALS:
            arguments += ['--serial', serial]
        with contextlib.redirect_stdout(io.StringIO()):
            self.assertEqual(probe.main(arguments, lambda *_: FixtureTransport()), 0)
            self.assertEqual(probe.main(arguments, lambda *_: FixtureTransport()), 0)
        self.assertEqual(len(list(self.root.glob('*/*/probe.json'))), 6)

    def test_tampered_raw_or_scope_rejected(self):
        self.capture()
        raw = self.root / 'capture/raw/boot-before.stdout'
        original = raw.read_bytes()
        raw.write_bytes(original + b'tampered')
        with self.assertRaisesRegex(ValueError, 'hash mismatch'):
            probe.compare([self.root / 'capture/probe.json'])
        raw.write_bytes(original)
        report_path = self.root / 'capture/probe.json'
        report = json.loads(report_path.read_text())
        report['protocol']['targets'].pop()
        report_path.write_text(probe.dump(report))
        with self.assertRaisesRegex(ValueError, 'protocol differs'):
            probe.compare([report_path])

    def test_receipt_unavailable_diagnostic_not_fake_ready(self):
        class NoReceipt(FixtureTransport):
            def run(self, command):
                result = super().run(command)
                if '( cat ' + probe.RECEIPT + ' )' in command:
                    return result[0], re.sub(rb'(__SEALED_PROBE_RC_[a-f0-9]+__)0', rb'\g<1>1', result[1]), b'absent'
                return result
        result = self.capture(NoReceipt())
        self.assertEqual(result['exit_code'], 0)
        self.assertFalse(result['recover_receipt']['available'])
        self.assertIsNone(result['recover_receipt']['current_boot_match'])


if __name__ == '__main__':
    unittest.main()
