import sys
import unittest
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import installation_chain as c


class InstallationIdentity(unittest.TestCase):
    def test_exact_process_roles_exclude_caller(self):
        text = 'PID PPID UID NAME\n123 1 0 foundation\n124 1 0 installs\n125 1 0 sh\n'
        self.assertEqual(c.processes(text), [{'pid': 123, 'role': 'foundation'}, {'pid': 124, 'role': 'installs'}])

    def test_maps_segments_deduplicate_but_distinct_inodes_remain(self):
        text = ('100-200 r-xp 0 00:01 3 /system/lib64/libinstalls.z.so\n'
                '200-300 r--p 1 00:01 3 /system/lib64/libinstalls.z.so\n'
                '300-400 r-xp 0 00:01 4 /system/lib64/libinstalls.z.so (deleted)\n')
        rows = c.mappings(text)
        self.assertEqual(len(rows), 2)
        self.assertTrue(rows[1]['deleted'])

    def test_current_disk_hash_cannot_validate_old_mapped_inode(self):
        row = {'path': c.PATHS[2], 'inode': 3, 'deleted': False}
        self.assertFalse(c.check_loaded(row, {row['path']: 'a'}, 'a', 4)['matches'])
        self.assertFalse(c.check_loaded(row, {row['path']: 'a'}, 'b', 3)['matches'])
        self.assertTrue(c.check_loaded(row, {row['path']: 'a'}, 'a', 3)['matches'])

    def test_deleted_mapping_rejected_even_if_content_matches(self):
        row = {'path': c.PATHS[2], 'inode': 3, 'deleted': True}
        self.assertFalse(c.check_loaded(row, {row['path']: 'a'}, 'a', 3)['matches'])

    def test_missing_process_is_unknown(self):
        import tempfile
        class Board:
            def shell(self, command, **kwargs):
                if command.startswith('sha256sum'):
                    return 0, '\n'.join('a'*64+'  '+p for p in c.PATHS)
                return 0, 'PID PPID UID NAME\n'
        with tempfile.TemporaryDirectory() as d:
            x = c.collect(Board(), d)
        self.assertEqual(x['verdict'], 'unknown')
        self.assertEqual(len(x['disk_identities']), 6)
        self.assertEqual(len(x['unobserved_libraries']), 3)

    def test_expected_identity_requires_every_alias(self):
        expected = {path: 'a'*64 for path in c.PATHS}
        with self.assertRaises(ValueError):
            c.compare_expected(dict(list(expected.items())[:-1]), {})
        with self.assertRaises(ValueError):
            c.compare_expected({path: 'a'*8 for path in c.PATHS}, {})

    def test_exact_alias_drift_is_reported_not_hidden_by_same_native(self):
        expected = {path: 'a'*64 for path in c.PATHS}
        actual = dict(expected);actual['/system/lib64/platformsdk/libinstalls.z.so'] = 'b'*64
        result = c.compare_expected(expected, {'disk_identities': actual, 'mismatches': [], 'unobserved_libraries': []})
        self.assertFalse(result['passed']);self.assertEqual(len(result['diff']), 1)
        self.assertEqual(result['diff'][0]['path'], '/system/lib64/platformsdk/libinstalls.z.so')

    def test_loader_unknown_does_not_become_verified_disk_assertion(self):
        expected = {path: 'a'*64 for path in c.PATHS}
        result = c.compare_expected(expected, {'disk_identities': expected, 'mismatches': [], 'unobserved_libraries': ['libinstalls.z.so']})
        self.assertTrue(result['disk_assertion_passed']);self.assertEqual(result['loaded_verdict'], 'unknown')
        self.assertTrue(result['passed'])  # the disk assertion, explicitly not loader verification
        stale = dict(disk_identities=expected, mismatches=[{'reason': 'stale inode'}], unobserved_libraries=[])
        self.assertFalse(c.compare_expected(expected, stale)['passed'])

    def test_runtime_fingerprints_include_all_aliases_once_and_detect_service_drift(self):
        import importlib.util
        import sweep_bind_deploy as sweep
        repo = Path(__file__).resolve().parents[3]
        spec = importlib.util.spec_from_file_location('batch_chain_test', repo/'benchmark/2026-09-28-bms-route-deploy/batch/bms_batch.py')
        batch = importlib.util.module_from_spec(spec); spec.loader.exec_module(batch)
        self.assertEqual(batch.FINGERPRINT_PATHS, sweep.FINGERPRINT_PATHS)
        self.assertEqual(batch.FINGERPRINT_PATHS.count('/system/bin/appspawn-x'), 1)
        for path in c.PATHS:
            self.assertEqual(batch.FINGERPRINT_PATHS.split().count(path), 1)
        one = ['a'*64+'  '+p for p in c.PATHS]
        two = list(one); two[2] = 'b'*64+'  '+c.PATHS[2]
        self.assertNotEqual(sweep.short_fingerprint('\n'.join(one)), sweep.short_fingerprint('\n'.join(two)))

if __name__ == '__main__': unittest.main()
