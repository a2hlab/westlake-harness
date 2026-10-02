import hashlib
import json
import unittest
from pathlib import Path

HERE = Path(__file__).resolve().parent


class AuditTests(unittest.TestCase):
    def setUp(self):
        self.data = json.loads((HERE / 'results.json').read_text())

    def test_all_26_entries_and_23_unique_paths_have_evidence(self):
        rows = self.data['rows']
        self.assertEqual(len(rows), 26)
        self.assertEqual(len({row['path'] for row in rows}), 23)
        self.assertEqual(sum(row['lane'].endswith('bms-deploy') for row in rows), 22)
        self.assertEqual(sum(row['lane'].endswith('b4') for row in rows), 4)
        for row in rows:
            self.assertTrue(row['reason'])
            self.assertTrue(row['evidence'])
            self.assertTrue(all((HERE / path).is_file() for path in row['evidence']))

    def test_three_conflicts_do_not_land_unproved_versions(self):
        rows = self.data['rows']
        for name in ['hwui_oh_abi_patch.cpp', 'app_native_loader_host_test.c']:
            selected = [row for row in rows if Path(row['path']).name == name]
            self.assertEqual(len(selected), 2)
            self.assertEqual(len({row['branch_sha256'] for row in selected}), 2)
            self.assertTrue(all(row['decision'] != 'LAND' for row in selected))
        loaders = [row for row in rows if Path(row['path']).name == 'app_native_loader.c']
        self.assertEqual(len(loaders), 2)
        self.assertEqual(len({row['selected']['sha256'] for row in loaders}), 1)
        self.assertTrue(loaders[0]['selected']['sha256'].startswith('aa1cd7c0'))
        self.assertTrue(all(row['selected']['sha256'] != row['branch_sha256'] for row in loaders))
        policy = next(row for row in rows if Path(row['path']).name == 'native_loader.cpp')
        self.assertEqual(policy['decision'], 'KEEP-MASTER')
        self.assertEqual(policy['selected']['sha256'], policy['master_sha256'])
        self.assertNotEqual(policy['branch_sha256'], policy['master_sha256'])

    def test_snapshots_match_and_unknowns_cannot_enter_landing(self):
        selected = self.data['selected_sources']
        self.assertEqual(len(selected), 13)
        targets = {row['target'] for row in selected}
        listing = (HERE / 'source-landing-paths.txt').read_text()
        self.assertEqual(targets, {line for line in listing.splitlines() if line and not line.startswith('#')})
        self.assertEqual(listing.count('# deployed='), 13)
        self.assertFalse(targets.intersection(self.data['unknown_rows']))
        for row in selected:
            self.assertEqual(hashlib.sha256((HERE / row['snapshot']).read_bytes()).hexdigest(), row['sha256'])
            self.assertEqual(row['sha256'], row['source']['sha256'])
            self.assertEqual(row['deployed_sha256'], self.data['binary_checks'][row['deployed_role']]['deployed']['sha256'])
            self.assertTrue(row['deployed_device_paths'])
            self.assertTrue(all((HERE / evidence).is_file() for evidence in row['basis']))
        self.assertEqual(hashlib.sha256((HERE / 'selected-sources.patch').read_bytes()).hexdigest(), self.data['source_patch_sha256'])
        self.assertEqual(self.data['source_patch_check']['exit_code'], 0)

    def test_runtime_object_chain_and_zero_execution(self):
        objects = json.loads((HERE / self.data['runtime_object_evidence']).read_text())['objects']
        self.assertEqual(len(objects), 4)
        for row in objects:
            self.assertEqual(row['hashes']['candidate'], row['hashes']['repeat'])
            self.assertTrue(row['linked_functions'])
            if row['name'] != 'AndroidRuntime':
                self.assertEqual(row['hashes']['candidate'], row['n2_object_sha256'])
        self.assertEqual(self.data['compiler_runs'], 0)
        self.assertEqual(self.data['device_operations'], 0)
        self.assertFalse(self.data['execution_enabled'])
        for binary in self.data['binary_checks'].values():
            self.assertEqual(binary['archive']['sha256'], binary['deployed']['sha256'])
            self.assertEqual(binary['comparison']['exit_code'], 0)


if __name__ == '__main__':
    unittest.main(verbosity=2)
