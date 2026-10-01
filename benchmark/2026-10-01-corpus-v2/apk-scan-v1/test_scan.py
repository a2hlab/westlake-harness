import copy
import hashlib
import json
from pathlib import Path
import unittest
from unittest.mock import patch

import report
import scan
import compact

HERE = Path(__file__).resolve().parent


def fixture():
    selection = dict(rows=[])
    apps, entries = [], []
    runtime = dict(name='fixture-not-real-U7', inputs={'lib.so':{}}, methods={'a.b()V':{}}, exports=[])
    for index in range(100):
        package = 'example.app'+str(index)
        row = dict(package=package, sha256=hashlib.sha256(package.encode()).hexdigest(), signer_sha256=['b'*64], group='priority', version_name='1', version_code=1)
        selection['rows'].append(row)
        entries.append(dict(package=package, key='cv2-'+package, apk_sha256=row['sha256'], signer_sha256=['b'*64], version_code=1))
        apps.append(dict(key=package, package=package, status='scanned', sha256=row['sha256'],
                         signer=dict(fingerprints=['b'*64]), dex=[dict(member='classes.dex')],
                         manifest=dict(launchers=[dict(target=package+'.Main')], activities=[{}]),
                         scanner_dependencies={'scanner':'c'*64}, startup=dict(reached=[], calls=[]),
                         risks=[], services=[], jni_calls=[], libraries=[], framework_calls=[],
                         features={}, app_native_candidates=[]))
    facts = dict(apps=apps, scanner_dependencies={'scanner':'c'*64}, tools={},
                 selection_sha256=report.digest(json.dumps(selection, ensure_ascii=False, sort_keys=True, indent=2).encode()+b'\n'),
                 runtime_profile_sha256=report.digest(json.dumps(runtime, sort_keys=True).encode()+b'\n'))
    return selection, facts, runtime, dict(apps=entries)


class IdentityTests(unittest.TestCase):
    def test_apk_sha_size_and_signer(self):
        payload = b'exact APK fixture'
        row = dict(package='fixture', sha256=hashlib.sha256(payload).hexdigest(), bytes=len(payload), signer_sha256=['a'*64])
        scan.check_identity(row, payload, ['a'*64])
        with self.assertRaisesRegex(ValueError, 'SHA/size'):
            scan.check_identity(row, payload+b'changed', ['a'*64])
        with self.assertRaisesRegex(ValueError, 'signer'):
            scan.check_identity(row, payload, ['b'*64])

    def test_modern_and_legacy_signer_output(self):
        for prefix in ['Signer #1', 'V3.0 Signer:', 'V2 Signer:']:
            with patch.object(scan, 'command', return_value=prefix+' certificate SHA-256 digest: '+'a'*64+'\n'):
                self.assertEqual(scan.signature(Path('fixture.apk'), Path('apksigner'))['fingerprints'], ['a'*64])
        with patch.object(scan, 'command', return_value='Verifies\n'):
            with self.assertRaisesRegex(ValueError, 'No verified'):
                scan.signature(Path('fixture.apk'), Path('apksigner'))


class RuleTests(unittest.TestCase):
    def test_services_and_wrong_overload(self):
        instructions = [('0000', 10, 'const-string v1, "audio" // string@0000'),
                        ('0002', 11, 'invoke-virtual {v0, v1}, Landroid/content/Context;.getSystemService:(Ljava/lang/String;)Ljava/lang/Object; // method@0001')]
        calls, natives, features = scan.scan_apps.method_scan('example.Main.onCreate:()V', instructions, 'classes.dex', 0, set())
        self.assertEqual(calls[0]['service'], 'audio')
        self.assertEqual(calls[0]['line'], 11)
        self.assertFalse(natives)
        instructions[1] = ('0002', 11, 'invoke-virtual {v0, v1}, Lexample/Fake;.notSystemService:(Ljava/lang/String;)Ljava/lang/Object; // method@0001')
        self.assertEqual(scan.scan_apps.method_scan('example.Main.onCreate:()V', instructions, 'classes.dex', 0, set())[0], [])

    def test_native_access_not_name_guess(self):
        text = "Class descriptor  : 'Lexample/Bridge;'\n      name          : 'foo'\n      type          : '(I)Z'\n      access        : 0x0101 (PUBLIC NATIVE)\n"
        native = scan.native_declarations(text, 'classes.dex')
        self.assertEqual(native[0]['id'], 'example/Bridge.foo(I)Z')
        self.assertEqual(scan.native_declarations(text.replace('PUBLIC NATIVE', 'PUBLIC ABSTRACT'), 'classes.dex'), [])

    def test_application_class_not_child_activity(self):
        text = 'E: manifest\n  E: application (line=3)\n    A: android:name(0x01010003)="example.App"\n    E: activity\n      A: android:name(0x01010003)="example.Main"\n'
        self.assertEqual(scan.application_class(text), 'example.App')
        self.assertEqual(scan.application_class(text.replace('android:name', 'http://schemas.android.com/apk/res/android:name')), 'example.App')
        self.assertIsNone(scan.application_class(text.replace('    A: android:name(0x01010003)="example.App"\n', '')))

    def test_unknown_jni_is_not_claimed_missing(self):
        selection, facts, runtime, manifest = fixture()
        app = facts['apps'][0]
        app['jni_calls'] = [dict(id='a.b()V', method='example.Main.onCreate:()V', coverage='unknown', line=12)]
        row = report.predict(selection['rows'][0], app, runtime, manifest['apps'][0]['key'])
        self.assertEqual(row['first_wall'], 'unknown')
        self.assertEqual(row['first_wall_candidates'][0]['family'], 'framework-jni:unknown')
        self.assertEqual(row['checkpoint'], 'unknown')
        self.assertEqual(report.method_key('example.Main.onCreate:()V'), 'Lexample/Main;->onCreate()V')

    def test_projection_counts_and_coordinates(self):
        selection, facts, runtime, manifest = fixture()
        app = facts['apps'][0]
        app['startup'].update(roots=[], reached=['Lexample/Main;->onCreate()V'])
        app['services'] = [dict(service='audio', method='example.Main.onCreate:()V', line=number, dex='classes.dex') for number in range(10)]
        result = compact.project(app)
        self.assertEqual(result['raw_counts']['services'], 10)
        self.assertEqual(result['services'][0]['occurrence_count'], 10)
        self.assertEqual(len(result['services'][0]['examples']), 3)
        prediction = report.predict(selection['rows'][0], result, runtime, manifest['apps'][0]['key'])
        self.assertEqual(prediction['first_wall_candidates'][0]['startup_occurrences'], 10)
        self.assertEqual(prediction['system_service_counts']['audio'], 10)


class FreezeTests(unittest.TestCase):
    def test_complete_positive_and_rejections(self):
        original = fixture()
        self.assertEqual(report.build(*original)['selected_count'], 100)
        mutations = [lambda data: data[1]['apps'].pop(),
                     lambda data: data[1]['apps'].__setitem__(1, copy.deepcopy(data[1]['apps'][0])),
                     lambda data: data[1]['apps'][0].update(status='pending'),
                     lambda data: data[1]['apps'][0].update(sha256='c'*64),
                     lambda data: data[2].update(name='changed profile'),
                     lambda data: data[3]['apps'].append(copy.deepcopy(data[3]['apps'][0]))]
        for mutate in mutations:
            data = copy.deepcopy(original)
            mutate(data)
            with self.assertRaises(ValueError):
                report.build(*data)


class ReplayTests(unittest.TestCase):
    def test_published_artifacts(self):
        selection = json.loads((HERE.parent/'results.json').read_text())
        facts = report.load_evidence(HERE/'facts.json.gz.b64')
        runtime = report.load_evidence(HERE/'runtime-profile.json.gz.b64')
        manifest = report.load_evidence(HERE/'input-manifest.json.gz.b64')
        result = report.build(selection, facts, runtime, manifest)
        self.assertEqual(result, json.loads((HERE/'results.json').read_text()))
        csv_payload = report.csv_text(result).encode()
        self.assertEqual((HERE/'PREDICTIONS.csv').read_bytes(), csv_payload)
        self.assertEqual((HERE/'README.md').read_text(), report.markdown(result, facts, runtime))
        freeze = json.loads((HERE/'FREEZE.json').read_text())
        self.assertEqual(freeze['csv_sha256'], report.digest(csv_payload))
        self.assertEqual(freeze['rows'], 100)
        self.assertEqual(freeze['prediction_generator_sha256'], report.digest((HERE/'report.py').read_bytes()))
        expected_path = scan.ROOT/'benchmark/2026-10-01-u7-prospective/v1/expected-run.json'
        expected = json.loads(expected_path.read_text())
        deployed = {**expected['runtime_files'], **expected['boot_files']}
        self.assertEqual(runtime['expected_run_sha256'], report.digest(expected_path.read_bytes()))
        for item in runtime['inputs'].values():
            self.assertTrue(item['deployed_paths'])
            self.assertTrue(all(deployed[path] == item['sha256'] for path in item['deployed_paths']))
        for relative, expected_sha in runtime['scanner_dependencies'].items():
            self.assertEqual(report.digest((scan.ROOT/relative).read_bytes()), expected_sha)
        self.assertFalse(result['observed_device_results'])
        self.assertEqual(facts['selection_sha256'], report.digest((HERE.parent/'results.json').read_bytes()))
        for relative, expected in facts['scanner_dependencies'].items():
            self.assertEqual(report.digest((scan.ROOT/relative).read_bytes()), expected)


if __name__ == '__main__':
    unittest.main()
