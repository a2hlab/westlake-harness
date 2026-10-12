"""Local fixtures only: no subprocess, device, or transport execution."""
import copy
import json
from pathlib import Path
import tempfile
import unittest

import realization as core
import seal_checks as checks

OLD = '/data/westlake-demo/toutiao/recovery-attempts/old'
NEW = '/data/westlake-demo/toutiao/recovery-attempts/new'
APK = '/data/apps/demo.apk'
HASH = 'a' * 64


class Collector:
    def __init__(self, responses):
        self.responses = responses
        self.commands = []

    def read(self, kind, command):
        self.commands.append((kind, command))
        value = self.responses[command]
        if isinstance(value, Exception):
            raise value
        return value.encode(), {'command': command, 'transport_rc': 0, 'remote_rc': 0}


class SealChecksTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.seal = {'schema': 'demo-seal/v1', 'serial': sorted(checks.observations.SERIALS)[0],
                     'files': {'runtime': {OLD + '/entry.sh': HASH}, 'boot': {'/boot/art': HASH},
                               'overlays': {}, 'installation': {APK: HASH}},
                     'system_params': {'persist.demo.enabled': 'true'},
                     'packages': [{'package': 'org.example.demo', 'version_code': 2,
                                   'apk_path': APK, 'apk_sha256': HASH, 'note': 'preserve'}],
                     'inventories': [{'patterns': [OLD + '/*.sh'], 'paths': [OLD + '/entry.sh']}]}
        self.proof = {'request': {'path': str(self.root / 'request.json')},
                      'parameters': {'control_root': NEW},
                      'files': [{'source_target': OLD + '/entry.sh', 'target': NEW + '/entry.sh'}]}
        self.repin()

    def repin(self):
        path = self.root / 'seal.json'
        path.write_text(json.dumps(self.seal))
        pin = {'path': 'seal.json', 'sha256': core.digest(path)}
        self.proof['source_identity'] = dict(pin, kind='seal')
        self.proof['source_seal'] = pin

    def req(self):
        return checks.requirements(self.proof)

    def observed(self):
        return {'errors': [], 'files': {APK: HASH},
                'system_params': dict(self.seal['system_params']),
                'packages': {'org.example.demo': {'version_code': '2'}},
                'inventories': [[NEW + '/entry.sh']]}

    def responses(self):
        return {'sha256sum ' + APK: HASH + '  ' + APK + '\n',
                'param get persist.demo.enabled': 'true\n',
                'bm dump -n org.example.demo': 'bundle:\n' + json.dumps(
                    {'name': 'org.example.demo', 'versionCode': 2, 'applicationInfo': {'versionCode': 0}}),
                'sha256sum ' + NEW + '/*.sh': HASH + '  ' + NEW + '/entry.sh\n'}

    def test_exact_inventory_root_mapping_preserves_packages_and_source(self):
        original = copy.deepcopy(self.seal)
        req = self.req()
        self.assertEqual(req['packages'], original['packages'])
        self.assertEqual(req['system_params'], original['system_params'])
        self.assertEqual(req['inventories'][0], {'patterns': [NEW + '/*.sh'], 'paths': [NEW + '/entry.sh']})
        self.assertEqual(core.read(self.root / 'seal.json'), original)
        checks.compare(req, self.observed())

    def test_source_pin_drift_and_separate_seal_pin_rejected(self):
        (self.root / 'seal.json').write_text('{}')
        with self.assertRaises(ValueError):
            self.req()
        self.repin()
        self.proof['source_seal']['sha256'] = '0' * 64
        with self.assertRaises(ValueError):
            self.req()

    def test_complete_original_structure_required(self):
        original = copy.deepcopy(self.seal)
        for mutation in ('group', 'empty-installation', 'system', 'packages', 'inventory'):
            with self.subTest(mutation=mutation):
                self.seal = copy.deepcopy(original)
                if mutation == 'group':
                    del self.seal['files']['overlays']
                elif mutation == 'empty-installation':
                    self.seal['files']['installation'] = {}
                elif mutation == 'system':
                    del self.seal['system_params']
                elif mutation == 'packages':
                    self.seal['packages'] = []
                else:
                    self.seal['inventories'][0]['paths'] = ['/not/sealed']
                self.repin()
                with self.assertRaises(ValueError):
                    self.req()

    def test_inventory_migration_requires_exact_file_projection(self):
        self.proof['files'][0]['target'] = NEW + '/different.sh'
        with self.assertRaisesRegex(ValueError, 'projection'):
            self.req()

    def test_similar_control_root_and_noncontrol_paths_are_not_rewritten(self):
        path = '/data/old/entry.sh'
        self.seal['files']['runtime'][path] = HASH
        self.seal['inventories'].append({'patterns': ['/data/old/*.sh'], 'paths': [path]})
        self.proof['files'].append({'source_target': path, 'target': path})
        self.repin()
        self.assertEqual(self.req()['inventories'][1], self.seal['inventories'][1])

    def test_unsafe_commands_rejected_before_collection(self):
        self.seal['inventories'][0]['patterns'] = [OLD + '/*;reboot']
        self.repin()
        with self.assertRaises(ValueError):
            self.req()

    def test_nonfile_and_apk_drift_are_all_rejected(self):
        req = self.req()
        for variant in ('param', 'version', 'apk', 'inventory-missing', 'inventory-extra', 'read-errors'):
            with self.subTest(variant=variant):
                obs = self.observed()
                if variant == 'param':
                    obs['system_params']['persist.demo.enabled'] = 'false'
                elif variant == 'version':
                    obs['packages']['org.example.demo']['version_code'] = 0
                elif variant == 'apk':
                    del obs['files'][APK]
                elif variant == 'inventory-missing':
                    obs['inventories'] = []
                elif variant == 'inventory-extra':
                    obs['inventories'][0].append(NEW + '/extra.sh')
                else:
                    obs['errors'] = ['transport']
                with self.assertRaises(ValueError):
                    checks.compare(req, obs)

    def test_collect_uses_top_level_bundle_version_and_only_read_commands(self):
        collector = Collector(self.responses())
        obs = checks.collect(self.req(), collector)
        checks.compare(self.req(), obs)
        self.assertEqual(obs['packages']['org.example.demo']['version_code'], '2')
        self.assertEqual({command for _, command in collector.commands}, set(self.responses()))

    def test_wrong_or_missing_top_level_bundle_identity_rejected(self):
        for data in ({'name': 'wrong', 'versionCode': 2},
                     {'name': 'org.example.demo', 'applicationInfo': {'versionCode': 2}},
                     {'name': 'org.example.demo', 'versionCode': True}):
            with self.subTest(data=data):
                responses = self.responses()
                responses['bm dump -n org.example.demo'] = json.dumps(data)
                with self.assertRaises(ValueError):
                    checks.collect(self.req(), Collector(responses))

    def test_transport_and_bad_sha_output_are_not_absence(self):
        for value in (ValueError('transport'), '', HASH + '  ' + APK + '\n' + HASH + '  ' + APK):
            with self.subTest(value=value):
                responses = self.responses()
                responses['sha256sum ' + APK] = value
                with self.assertRaises(ValueError):
                    checks.collect(self.req(), Collector(responses))

    def test_candidate_has_no_seal_requirements_or_reads(self):
        self.proof['source_identity']['kind'] = 'candidate-fingerprint'
        self.proof['source_seal'] = None
        req = checks.requirements(self.proof)
        self.assertEqual(req, {})
        collector = Collector({})
        self.assertEqual(checks.collect(req, collector), {})
        checks.compare(req, {})
        self.assertEqual(collector.commands, [])


if __name__ == '__main__':
    unittest.main()
