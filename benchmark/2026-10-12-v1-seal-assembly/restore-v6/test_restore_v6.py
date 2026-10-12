#!/usr/bin/env python3
"""Eight offline v6 delta checks, rebuilding the full package in a temporary dir.

Only v5 provider/binding/plan metadata are read. No v5 payload/runtime, device,
production lock, transaction executor, shell worker or network is exercised.
"""
import ast
import copy
import importlib.util
import json
from pathlib import Path
import re
import sys
import tempfile
import unittest

sys.dont_write_bytecode = True
HERE = Path(__file__).resolve().parent
V5 = HERE.parent / 'restore-v5'
CLASSIFIER_SHA = '0bf966d76e038379af1fa2542746572a2c76a9bf88e17a97869682debfc36eaf'
WATCHDOG_SHA = '2b635ef1ea9e00546e1306b0fe6872a415a8c7d5653e19f9fb42fca04386db4a'
HELPER_SHA = '6bce7c3c8f84ad1047313c5dd76bcb084637d9095b9163dc710c88aaee12fe4c'
WORKER_SHA = '2d3ce1546c9df1e3a222e23f19c39f8f4aec82fb551d59f37dbe7fd343573717'
spec = importlib.util.spec_from_file_location('restore_v6_delta_provider', HERE / 'toutiao_provider.py')
p = importlib.util.module_from_spec(spec)
spec.loader.exec_module(p)


class RestoreV6DeltaTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.binding_path = HERE / 'binding.5cd.composed.disabled.json'
        cls.binding = p.read(cls.binding_path)
        cls.oldbinding = p.read(V5 / 'binding.5cd.r3.disabled.json')
        cls.oldplan = p.read(V5 / 'package-r3-disabled/plan.json')
        cls.temp = tempfile.TemporaryDirectory(prefix='restore-v6-full-delta-')
        cls.addClassCleanup(cls.temp.cleanup)
        cls.package = Path(cls.temp.name) / 'rebuilt-package'
        # This is intentional: a sparse landing cannot pass by reusing its
        # producer's runtime directory or the previous v5 package payload.
        p.compile_package(cls.binding_path, cls.package)
        cls.payload = cls.package / 'payload'
        cls.plan = p.read(cls.package / 'plan.json')
        cls.manifest = p.read(cls.package / 'manifest.json')

    def test_01_rebuild_manifest_exactly_matches_frozen_package(self):
        expected = HERE / 'package-composed-disabled/manifest.json'
        self.assertEqual((self.package / 'manifest.json').read_bytes(), expected.read_bytes())
        self.assertEqual(self.manifest['plan_sha256'], p.digest(self.package / 'plan.json'))

    def test_02_complete_inventory_and_all_487_actual_member_bytes(self):
        self.assertEqual(len(self.plan['members']), 487)
        self.assertEqual(len({r['target'] for r in self.plan['members']}), 487)
        inventory = self.manifest['files']
        self.assertEqual(len({r['path'] for r in inventory}), len(inventory))
        for row in inventory:
            with self.subTest(file=row['path']):
                source = self.package / row['path']
                self.assertTrue(source.is_file())
                self.assertEqual(p.digest(source), row['sha256'])
                self.assertEqual(source.stat().st_size, row['bytes'])
        for row in self.plan['members']:
            with self.subTest(target=row['target']):
                self.assertTrue(row['source'].startswith('$PACKAGE/'))
                self.assertEqual(p.digest(self.package / row['source'].removeprefix('$PACKAGE/')),
                                 row['sha256'])

    def test_03_thirteen_boot_members_entry_and_startup_hash_chain(self):
        aliases = {'start-parent.sh': 'start-parent-prepared.sh',
                   'spawn.sh': 'spawn-prepared.sh', 'screen-gate': 'screen-gate-feed'}
        rows = [line.split() for line in (self.payload / 'members.tsv').read_text().splitlines()]
        self.assertEqual(len(rows), 13)
        self.assertEqual(len({r[1] for r in rows}), 13)
        for sha, name, mode in rows:
            self.assertEqual(p.digest(self.payload / aliases.get(name, name)), sha, name)
            self.assertIn(mode, ('550', '440'))
        fields = dict(re.findall(r"^([A-Z_]+)='([^']*)'$", (self.payload / 'startup.env').read_text(), re.M))
        self.assertEqual(fields['STARTUP_MEMBERS_SHA'], p.digest(self.payload / 'members.tsv'))
        self.assertEqual(fields['STARTUP_DECODER_SHA'], CLASSIFIER_SHA)
        self.assertEqual((self.payload / 'startup.expected.sha256').read_text().strip(),
                         p.digest(self.payload / 'startup.env'))
        entry = (self.payload / 'entry.sh').read_text()
        for name in ('watchdog.sh', 'route-b-owner.sh'):
            self.assertEqual(entry.count(p.digest(self.payload / name)), 1, name)

    def test_04_only_composed_programs_change_and_r3_guardians_stay_exact(self):
        expected = {'screen-gate-feed': CLASSIFIER_SHA, 'watchdog.sh': WATCHDOG_SHA,
                    'route-b-owner.sh': HELPER_SHA, 'readiness-probe.sh': WORKER_SHA}
        for name, sha in expected.items():
            self.assertEqual(p.digest(self.payload / name), sha, name)
        old = {r['target']: r for r in self.oldplan['members']}
        changed_names = {'watchdog.sh', 'screen-gate', 'entry.sh', 'members.tsv',
                         'startup.env', 'startup.expected.sha256'}
        self.assertEqual(set(old), {r['target'] for r in self.plan['members']})
        for row in self.plan['members']:
            if Path(row['target']).name not in changed_names:
                self.assertEqual(row['sha256'], old[row['target']]['sha256'], row['target'])
        composition = self.binding['composition_update']
        source = p.read(p.pin(composition['composition'], HERE))
        self.assertEqual(source['classifier_sha256'], CLASSIFIER_SHA)
        self.assertEqual(source['t10_watchdog_sha256'], WATCHDOG_SHA)
        self.assertEqual(composition['classifier_sha256'], CLASSIFIER_SHA)
        self.assertEqual(composition['watchdog_sha256'], WATCHDOG_SHA)

    def test_05_target_preimages_metadata_and_directories_remain_v5(self):
        for name in ('before', 'after', 'preserved', 'prerequisites', 'storage',
                     'new_storage_directories', 'runtime_file_metadata',
                     'extra_runtime_files', 'required_directories', 'directories', 'control_source'):
            self.assertEqual(self.binding[name], self.oldbinding[name], name)
        oldstage = {r['target']: r for r in self.oldbinding['stage_files']}
        self.assertEqual(set(oldstage), {r['target'] for r in self.binding['stage_files']})
        for row in self.binding['stage_files']:
            old = copy.deepcopy(oldstage[row['target']]); new = copy.deepcopy(row)
            old_evidence = old.pop('metadata_evidence'); new_evidence = new.pop('metadata_evidence')
            self.assertEqual(new, old, row['target'])
            # Only the producer-worktree path moved to its byte-identical landed
            # record. Never require the stale producer path to still exist.
            self.assertEqual({k: v for k, v in new_evidence.items() if k != 'path'},
                             {k: v for k, v in old_evidence.items() if k != 'path'})
            self.assertEqual(p.digest(p.pin(new_evidence, HERE)), old_evidence['sha256'])
        for name in ('directories', 'storage_directories', 'retained_directories', 'directory_prerequisites'):
            self.assertEqual(self.plan[name], self.oldplan[name], name)
        for field in ('before', 'after'):
            self.assertEqual({r['target']: r[field] for r in self.plan['members']},
                             {r['target']: r[field] for r in self.oldplan['members']}, field)

    def test_06_actual_5cd_uid_is_strict_and_package_stays_disabled(self):
        self.assertEqual(self.binding['host_uid'], 20011300)
        self.assertEqual(self.plan['serial'], '5cd1e3dd00000000000000000923012c')
        self.assertIn('AUTH_UID=20011300\n', (self.payload / 'config-common.sh').read_text())
        for name in ('real-start-parent.sh', 'real-start-parent-bounded.sh'):
            self.assertIn('"$RT" 20011300 /system/bin/sh', (self.payload / name).read_text())
        helper = (self.payload / 'route-b-owner.sh').read_text()
        self.assertIn('[ "$uid" = "$RB_OWNER_UID:$RB_OWNER_UID:$RB_OWNER_UID:$RB_OWNER_UID" ]', helper)
        watchdog = (self.payload / 'watchdog.sh').read_text()
        self.assertIn('timeout 2 sh "$F/readiness-probe.sh"', watchdog)
        self.assertIn('child_owned "$child" "$child_birth" ||', watchdog)
        self.assertFalse(self.binding['startup_enabled'])
        self.assertFalse(self.plan['execution_enabled'])
        self.assertNotIn('authorization', self.binding)
        startup = (self.payload / 'startup.env').read_text()
        self.assertIn("STARTUP_APPROVED_BY='PENDING'", startup)
        self.assertIn("STARTUP_ENABLED='0'", startup)
        self.assertFalse(list(self.package.glob('*authorization*')))

    def test_07_invoke_and_transaction_executor_ast_are_unchanged(self):
        def functions(path):
            return {n.name: ast.dump(n, include_attributes=False) for n in ast.parse(path.read_text()).body
                    if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef))}
        old, new = functions(V5 / 'toutiao_provider.py'), functions(HERE / 'toutiao_provider.py')
        for name in ('invoke', 'new_executor'):
            self.assertEqual(old[name], new[name], name)

    def test_08_composition_plan_and_independent_program_pin_drift_rejects_before_output(self):
        for field in ('composition', 'plan', 'classifier_sha256', 'watchdog_sha256'):
            with self.subTest(field=field), tempfile.TemporaryDirectory(prefix='restore-v6-pin-negative-') as temp:
                root = Path(temp); binding = copy.deepcopy(self.binding)
                if field in ('composition', 'plan'):
                    binding['composition_update'][field]['sha256'] = '0' * 64
                else:
                    binding['composition_update'][field] = '0' * 64
                source = root / 'binding.json'; p.write(source, binding)
                output = root / 'must-not-exist'
                with self.assertRaises(ValueError):
                    p.compile_package(source, output)
                self.assertFalse(output.exists())


if __name__ == '__main__':
    unittest.main(verbosity=2)
