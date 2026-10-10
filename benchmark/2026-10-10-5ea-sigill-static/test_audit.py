import importlib.util
import json
from pathlib import Path
import unittest


SPEC = importlib.util.spec_from_file_location('audit', Path(__file__).with_name('audit.py'))
audit = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(audit)


def line(pid, message):
    return '10-10 16:16:05.000 ' + str(pid) + ' ' + str(pid) + ' W TEST: ' + message


class KnownAnswers(unittest.TestCase):
    def test_transient_child_without_last_observation(self):
        result = audit.analyze('\n'.join([line(4000, 'WLCGATE:STOCK:SPAWN_RESULT ret=0 pid=4375'),
            line(4375, 'load ' + audit.BRIDGE + ' failed, namespace=westlake.sealed.child, errno=13'),
            line(4375, 'WLCGATE:LSP:LOAD_ERROR:10'),
            line(4000, 'com.example.helloworld with pid 4375 exit with code:123')]), [])
        self.assertEqual(result['target_pids'], [4375])
        self.assertEqual(result['stage'], 'bridge-load-EACCES')
        self.assertEqual(len(result['exits']), 1)

    def test_foreign_signal_not_app_signal(self):
        result = audit.analyze(line(9000, 'MUSL-SIGCHAIN signal: 4'), [4375])
        self.assertEqual(result['all_signal4'], 1)
        self.assertEqual(result['own_signal4'], 0)

    def test_handled_signal_can_precede_java_success(self):
        result = audit.analyze('\n'.join([line(6150, 'MUSL-SIGCHAIN signal: 4'),
            line(6150, '[CHILD_CK] Java main entered')]), [6150])
        self.assertEqual(result['own_signal4'], 1)
        self.assertEqual(result['stage'], 'java-entry')

    def test_provider_entry_not_loader_failure(self):
        result = audit.analyze('\n'.join([line(29164, 'WLCGATE:LSP:PASS_LOAD_RESULT'),
            line(29164, 'WLCGATE:PROVIDER:INSTALL_RESULT:0'),
            line(29164, 'WLCGATE:PROVIDER:ENTRY_RESULT:4294965293'),
            line(29164, 'WLCGATE:RAC:FAIL_SEALED_PROVIDER')]), [29164])
        self.assertEqual(result['provider_entry_results'], [-2003])
        self.assertEqual(result['loader_errors'], [])
        self.assertEqual(result['stage'], 'provider-entry')

    def test_no_new_spawn_is_unknown_not_independent_crash(self):
        result = audit.analyze(line(9000, 'LIFECYCLE_TIMEOUT MUSL-SIGCHAIN signal: 4'), [])
        self.assertFalse(result['has_new_spawn'])
        self.assertEqual(result['stage'], 'unknown')

    def test_sigchld_is_not_sigill(self):
        result = audit.analyze(line(4000, 'ProcessSignal signum:17 pid:4375'), [4375])
        self.assertEqual(result['own_signal4'], 0)

    def test_covering_mount_not_substring(self):
        text = '\n'.join(['1 0 1:1 / / rw - ext4 /dev/sda rw',
            '2 1 1:2 /seq /system/android rw,nosuid - ext4 /dev/sdb rw',
            '3 2 1:2 /seq2 /system/android/lib64/liboh_adapter_bridge.so rw,noexec - ext4 /dev/sdb rw'])
        self.assertEqual(audit.mount_rows(text, audit.BRIDGE)[0]['options'], 'rw,noexec')
        self.assertEqual(audit.mount_rows(text, '/system/android-extra/file')[0]['mount_id'], '1')

    def test_real_known_answers(self):
        excerpts = json.loads((Path(__file__).parent / 'evidence/hilog-excerpts.json').read_text())
        sample = next(row for row in excerpts if row['name'] == '5cd-host-only-suid')
        result = audit.analyze('\n'.join(row['text'] for row in sample['lines']), [])
        self.assertEqual(result['stage'], 'provider-entry')
        self.assertEqual(result['provider_entry_results'], [-2003])
        self.assertEqual(result['bridge_errno13'], [])
        sample = next(row for row in excerpts if row['name'] == 'healthy-noon-5ea-helloworld')
        good = audit.analyze('\n'.join(row['text'] for row in sample['lines']), [6150])
        self.assertEqual(good['own_signal4'], 4)
        self.assertEqual(good['own_java_entry'], 5)

    def test_different_plans_never_imply_missing_library(self):
        reports = json.loads((Path(__file__).parent / 'snapshot-comparison.json').read_text())
        for report in reports[:3]:
            self.assertFalse(report['plan_comparable'])
            self.assertEqual(report['exit'], 3)
            self.assertEqual(report['path_sets']['status'], 'NOT-COMPARABLE')

    def test_pure_base_all_three_boards_sha_equal(self):
        report = json.loads((Path(__file__).parent / 'fingerprint-comparison.json').read_text())
        self.assertEqual(len(report['states']['5ea-definitive']['paths']), 124)
        for changes in report['diffs'].values():
            self.assertEqual(changes, {})


if __name__ == '__main__':
    unittest.main()
