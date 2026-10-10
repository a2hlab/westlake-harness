from contextlib import redirect_stderr, redirect_stdout
import hashlib
import io
import json
from pathlib import Path
import sys
import tempfile
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parent))
import reboot_sim as sim
from selinux_label_audit import load_recipe, RECIPE


HOST = '/system/bin/appspawn-x'
RUNTIME = '/system/android/lib64/liboh_android_runtime.so'
CHILD = '/system/lib64/appspawn/libwestlake_android_child.z.so'
GUARD = '/system/lib64/libwestlake_thread_guard_registry.so'
FILTER = '/system/lib64/seccomp/libapp_filter.z.so'
SYSTEM = 'u:object_r:system_file:s0'
LIB = 'u:object_r:system_lib_file:s0'
DATA = 'u:object_r:data_local_tmp:s0'
BYTE_SHA = '1' * 64


def fixture():
    plan = {'mounts': [
        {'kind': 'directory', 'target': '/system/android', 'source': '/data/archive/android'},
        {'kind': 'file', 'target': HOST, 'source': '/data/archive/appspawn-x'},
        {'kind': 'file', 'target': CHILD, 'source': '/data/archive/child.so'},
        {'kind': 'file', 'target': GUARD, 'source': '/data/archive/guard.so'}
    ]}
    physical = {}
    paths = ['/system', '/system/bin', '/system/android', '/system/android/lib64',
             '/system/lib64', '/system/lib64/appspawn', '/system/lib64/seccomp']
    for path in paths:
        physical[path] = dict(kind='directory', label=SYSTEM, evidence='known-answer: independent inode fixture')
    physical['/system/lib64/seccomp']['label'] = LIB
    for path, label in [(HOST, 'u:object_r:appspawn_exec:s0'), (RUNTIME, LIB),
                        (CHILD, LIB), (GUARD, LIB), (FILTER, LIB)]:
        physical[path] = dict(kind='file', label=label, sha256=BYTE_SHA, evidence='known-answer: file inventory')
    sources = {'/data/archive/android': dict(kind='directory', label=DATA, evidence='known-answer: archived Android tree'),
               '/data/archive/android/lib64': dict(kind='directory', label=DATA, evidence='known-answer: archived lib64')}
    for path in [HOST, RUNTIME, CHILD, GUARD]:
        mount = next(row for row in plan['mounts'] if path == row['target'] or path.startswith(row['target'] + '/'))
        sources[mount['source'] + path[len(mount['target']):]] = dict(physical[path], label=DATA)
    inventory = dict(physical_files=physical, source_files=sources, physical_complete=True, source_complete=True)
    snapshot = dict(serial='61b0657200000000000000000324012c', boot_id='11111111-1111-1111-1111-111111111111',
                    complete=True, boot_stable=True,
                    params={'const.cust.config_dir_layer': None}, bind_targets=[row['target'] for row in plan['mounts']],
                    init_invalid=True, labels={HOST: DATA}, items={})
    autostart = dict(serial=snapshot['serial'], enabled=True, recover_phase='before-services', apply_label_recipe=True,
                     services=[dict(name='appspawn-x', path=HOST, secon='u:r:appspawn:s0', evidence='known-answer: init cfg')],
                     seccomp=dict(name='app', domain='appspawn', evidence='known-answer: config_policy defaults'))
    closure = dict(roots=[dict(path=path, domain='appspawn') for path in [HOST, CHILD, GUARD]], objects={})
    for path in [HOST, RUNTIME, CHILD, GUARD]:
        closure['objects'][path] = dict(sha256=BYTE_SHA, needed=[], evidence='known-answer: ELF readelf fixture')
    closure['objects'][HOST]['needed'] = [dict(soname='liboh_android_runtime.so', resolved_path=RUNTIME,
                                             namespace='appspawn', evidence='known-answer: pinned resolution')]
    queries = []
    for label, permissions, object_class in [
        ('system_file', ['search', 'getattr'], 'dir'),
        ('system_lib_file', ['search', 'getattr'], 'dir'),
        ('appspawn_exec', ['entrypoint', 'execute', 'read', 'open', 'map'], 'file'),
        ('system_lib_file', ['read', 'open', 'map', 'getattr'], 'file'),
        ('system_file', ['getattr', 'read', 'open'], 'file'),
        ('system_file', ['entrypoint', 'execute'], 'file'),
        ('data_local_tmp', ['read', 'open', 'map'], 'file')
    ]:
        for permission in permissions:
            allowed = not (label == 'data_local_tmp' or (label == 'system_file' and permission in ['entrypoint', 'execute']))
            queries.append(dict(domain='appspawn', label=label, permission=permission, **{'class': object_class},
                                allowed=allowed, evidence='MOCK_QUERY: not a real policy proof'))
    evidence = dict(query_provider='sepolicy_gate.run_query/mock-only', query_tool_sha256='2' * 64, queries=queries)
    return dict(plan=plan, snapshot=snapshot, inventory=inventory, autostart=autostart,
                closure=closure, recipe=load_recipe(), queries=evidence)


class RebootSimulationTests(unittest.TestCase):
    def setUp(self):
        self.data = fixture()

    def predict(self):
        return sim.simulate(*(self.data[name] for name in ['plan', 'snapshot', 'inventory', 'autostart', 'closure', 'recipe']),
                            sim.RecordedQueries(self.data['queries']))

    def rows(self, report, kind):
        return [row for row in report['checks'] if row['kind'] == kind]

    def test_clean_replay_predicts_three_checks_and_clears_old_invalid(self):
        report = self.predict()
        self.assertEqual(report['status'], 'PASS')
        self.assertTrue(report['safe_to_reboot'])
        self.assertFalse(report['execution_enabled'])
        self.assertFalse(report['board_access'])
        self.assertEqual(report['predicted_files'][HOST]['label'], 'u:object_r:appspawn_exec:s0')
        self.assertEqual(report['predicted_files'][FILTER]['label'], LIB)
        self.assertIn('does not survive', report['init_invalid'])
        self.assertTrue(all(row['status'] == 'PASS' for row in self.rows(report, 'init-entrypoint')))
        self.assertEqual(self.rows(report, 'seccomp-cfg')[0]['status'], 'PASS')

    def test_61b_three_observed_walls_have_independent_evidence(self):
        self.data['autostart']['enabled'] = False
        physical = self.data['inventory']['physical_files']
        physical[HOST]['label'] = SYSTEM
        physical[RUNTIME]['label'] = DATA
        del physical[FILTER]
        report = self.predict()
        self.assertEqual(report['status'], 'FAIL')
        self.assertEqual(self.rows(report, 'init-entrypoint')[0]['status'], 'FAIL')
        self.assertIn('entrypoint', self.rows(report, 'init-entrypoint')[0]['reason'])
        wall = next(row for row in self.rows(report, 'dependency-map') if row['path'] == RUNTIME)
        self.assertEqual(wall['status'], 'FAIL')
        self.assertIn('map', wall['reason'])
        self.assertIn('data_local_tmp', wall['reason'])
        self.assertIn('visible_count=0', self.rows(report, 'seccomp-cfg')[0]['reason'])
        self.assertTrue(all(row['evidence'] for row in report['checks']))

    def test_disabled_autostart_discards_current_bind_labels(self):
        self.data['autostart']['enabled'] = False
        self.data['inventory']['physical_files'][HOST]['label'] = SYSTEM
        self.data['snapshot']['labels'][HOST] = 'u:object_r:appspawn_exec:s0'
        report = self.predict()
        self.assertEqual(report['predicted_files'][HOST]['label'], SYSTEM)
        self.assertEqual(report['status'], 'FAIL')

    def test_unobserved_underlying_inodes_are_unknown_not_current_bind(self):
        self.data['autostart']['enabled'] = False
        self.data['inventory']['physical_complete'] = False
        del self.data['inventory']['physical_files'][HOST]
        report = self.predict()
        self.assertEqual(self.rows(report, 'init-entrypoint')[0]['status'], 'UNKNOWN')
        self.assertFalse(report['safe_to_reboot'])

    def test_late_recover_missing_source_and_missing_query_cannot_pass(self):
        for mode in ['late', 'source', 'query']:
            with self.subTest(mode=mode):
                self.data = fixture()
                if mode == 'late':
                    self.data['autostart']['recover_phase'] = 'after-services'
                elif mode == 'source':
                    del self.data['inventory']['source_files']['/data/archive/appspawn-x']
                else:
                    self.data['queries']['queries'] = []
                self.assertFalse(self.predict()['safe_to_reboot'])

    def test_source_labels_are_not_magically_correct_without_recipe(self):
        self.data['autostart']['apply_label_recipe'] = False
        report = self.predict()
        self.assertEqual(report['predicted_files'][RUNTIME]['label'], DATA)
        self.assertEqual(report['status'], 'FAIL')

    def test_multiple_visible_filters_and_denied_stat_both_fail(self):
        physical = self.data['inventory']['physical_files']
        physical['/chipset'] = dict(kind='directory', label=SYSTEM, evidence='known-answer')
        physical['/chipset/lib64'] = dict(physical['/chipset'])
        physical['/chipset/lib64/seccomp'] = dict(physical['/chipset'])
        physical['/chipset/lib64/seccomp/libapp_filter.z.so'] = dict(physical[FILTER])
        self.assertIn('visible_count=2', self.rows(self.predict(), 'seccomp-cfg')[0]['reason'])
        del physical['/chipset/lib64/seccomp/libapp_filter.z.so']
        for query in self.data['queries']['queries']:
            if query['label'] == 'system_lib_file' and query['class'] == 'file' and query['permission'] == 'getattr':
                query['allowed'] = False
        self.assertIn('visible_count=0', self.rows(self.predict(), 'seccomp-cfg')[0]['reason'])

    def test_closure_unknown_sha_missing_inventory_or_unresolved_edge(self):
        for mode in ['hash', 'missing', 'unresolved']:
            self.data = fixture()
            if mode == 'hash':
                self.data['closure']['objects'][HOST]['sha256'] = 'f' * 64
            elif mode == 'missing':
                del self.data['closure']['objects'][RUNTIME]
            else:
                self.data['closure']['objects'][HOST]['needed'][0]['resolved_path'] = None
            self.assertFalse(self.predict()['safe_to_reboot'])

    def test_missing_cfg_parameter_capture_is_unknown(self):
        self.data['snapshot']['params'] = {}
        self.assertEqual(self.rows(self.predict(), 'seccomp-cfg')[0]['status'], 'UNKNOWN')

    def test_query_interface_export_records_explicit_denies_and_binding(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            policy = root / 'policy'
            policy.write_bytes(b'mock policy')
            tool = root / 'query.py'
            tool.write_text('mock source only')
            calls = []

            def run_query(policy_path, domain, label, permission, object_class):
                calls.append((domain, label, permission, object_class))
                if label == 'data_local_tmp' or (label == 'system_file' and permission == 'entrypoint'):
                    return []
                return ['MOCK allow ' + domain + ' ' + label + ':' + object_class + ' ' + permission]

            exported = sim.collect_queries(run_query, policy, RECIPE, self.data['inventory'],
                                           self.data['autostart'], self.data['closure'], tool)
            self.assertEqual(exported['recipe_sha256'], sim.digest(RECIPE))
            self.assertEqual(exported['policy_sha256'], sim.digest(policy))
            self.assertEqual(exported['query_tool_sha256'], sim.digest(tool))
            query = sim.RecordedQueries(exported)
            self.assertFalse(query('appspawn', 'data_local_tmp', 'map', 'file')['allowed'])
            self.assertTrue(query('appspawn', 'appspawn_exec', 'entrypoint', 'file')['allowed'])
            self.assertEqual(len(calls), len(set(calls)))

    def test_prediction_is_deterministic(self):
        first = json.dumps(self.predict(), sort_keys=True)
        second = json.dumps(self.predict(), sort_keys=True)
        self.assertEqual(first, second)

    def write_inputs(self, root):
        inputs = {}
        snapshot = json.dumps(self.data['snapshot'], sort_keys=True).encode()
        self.data['inventory']['snapshot_sha256'] = hashlib.sha256(snapshot).hexdigest()
        policy = b'MOCK_POLICY_NOT_LIVE_SEPOLICY'
        self.data['queries']['policy_sha256'] = hashlib.sha256(policy).hexdigest()
        self.data['queries']['recipe_sha256'] = sim.digest(RECIPE)
        for name, obj in self.data.items():
            target = root / (name + '.json')
            blob = RECIPE.read_bytes() if name == 'recipe' else json.dumps(obj, sort_keys=True).encode()
            target.write_bytes(blob)
            inputs[name] = dict(path=target.name, sha256=sim.digest(target))
        (root / 'policy').write_bytes(policy)
        inputs['policy'] = dict(path='policy', sha256=sim.digest(root / 'policy'))
        manifest = root / 'inputs.json'
        manifest.write_text(json.dumps(dict(schema_version=1, inputs=inputs)))
        return manifest

    def invoke(self, manifest, out):
        with redirect_stdout(io.StringIO()) as stdout, redirect_stderr(io.StringIO()) as stderr:
            status = sim.main(['--inputs', str(manifest), '--out', str(out)])
        return status, stdout.getvalue(), stderr.getvalue()

    def test_cli_pinned_inputs_repeat_identically(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            manifest = self.write_inputs(root)
            for name in ['one', 'two']:
                status, stdout, stderr = self.invoke(manifest, root / name)
                self.assertEqual(status, 0, stderr)
                self.assertIn('advisory_only=true', stdout)
            for name in ['prediction.json', 'prediction.tsv']:
                self.assertEqual((root / 'one' / name).read_bytes(), (root / 'two' / name).read_bytes())

    def test_missing_or_drifted_input_writes_no_prediction(self):
        for mode in ['missing', 'hash', 'policy-binding', 'snapshot-binding']:
            with self.subTest(mode=mode), tempfile.TemporaryDirectory() as directory:
                root = Path(directory)
                manifest = self.write_inputs(root)
                if mode == 'missing':
                    (root / 'snapshot.json').unlink()
                elif mode == 'hash':
                    (root / 'plan.json').write_text('{}')
                else:
                    name = 'queries' if mode == 'policy-binding' else 'inventory'
                    data = json.loads((root / (name + '.json')).read_text())
                    data['policy_sha256' if name == 'queries' else 'snapshot_sha256'] = 'f' * 64
                    (root / (name + '.json')).write_text(json.dumps(data))
                    refs = json.loads(manifest.read_text())
                    refs['inputs'][name]['sha256'] = sim.digest(root / (name + '.json'))
                    manifest.write_text(json.dumps(refs))
                status, stdout, stderr = self.invoke(manifest, root / 'out')
                self.assertEqual(status, 2)
                self.assertIn('NO_PREDICTION', stderr)
                self.assertFalse((root / 'out').exists())

    def test_incomplete_snapshot_and_duplicate_query_cannot_be_safe(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            self.data['snapshot']['complete'] = False
            manifest = self.write_inputs(root)
            status, stdout, stderr = self.invoke(manifest, root / 'out')
            self.assertEqual(status, 2)
            self.assertIn('snapshot incomplete', stderr)
        evidence = self.data['queries']
        evidence['queries'].append(dict(evidence['queries'][0]))
        with self.assertRaisesRegex(ValueError, 'duplicate'):
            sim.RecordedQueries(evidence)

    def test_relative_package_sources_require_explicit_archive_root(self):
        self.data['autostart']['source_root'] = '/data/archive'
        for row in self.data['plan']['mounts']:
            row['source'] = row['source'][len('/data/archive/'):]
        self.assertEqual(self.predict()['status'], 'PASS')
        del self.data['autostart']['source_root']
        with self.assertRaisesRegex(ValueError, 'source_root'):
            self.predict()

    def test_raw_snapshot_receipts_and_plan_binding_refuse_drift(self):
        for mode in ['raw', 'plan']:
            with self.subTest(mode=mode), tempfile.TemporaryDirectory() as directory:
                root = Path(directory)
                if mode == 'plan':
                    self.data['snapshot']['plan_sha256'] = 'f' * 64
                else:
                    self.data['snapshot']['items'] = {'boot_id': dict(rc=0, raw_sha256='e' * 64,
                                                                    stderr_sha256='f' * 64)}
                manifest = self.write_inputs(root)
                status, stdout, stderr = self.invoke(manifest, root / 'out')
                self.assertEqual(status, 2)
                self.assertFalse((root / 'out').exists())
                self.assertIn('binding' if mode == 'plan' else 'raw input', stderr)
                self.data = fixture()


if __name__ == '__main__':
    unittest.main()
