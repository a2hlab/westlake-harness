import json
import subprocess
import sys
import tempfile
import unittest
import zipfile
from pathlib import Path

P = Path(__file__).resolve().parent
ROOT = P.parents[1]
sys.path.insert(0, str(ROOT / 'scripts/lab'))
import lab_paths
import check_webview_jni as gate

SOURCE = ROOT / 'benchmark/2026-09-30-n3b-webview/src/webview_publication.cpp'
NATIVE = lab_paths.workspaces() / 'westlake-generation-n3b-53bb18d1/payload/android/lib64/liboh_android_runtime.so'


class ExactDefinitions(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.contract = gate.native_contract(SOURCE, NATIVE)

    def fixture(self, name):
        path = P / 'fixtures' / (name + '.jar')
        pin = json.loads((P / 'fixture-receipt.json').read_text())['fixtures'][name]['sha256']
        self.assertEqual(gate.digest(path.read_bytes()), pin)
        index, inputs = gate.dex_definitions([path])
        return [gate.resolve(index, r) for r in self.contract['requirements']], inputs

    def test_native_provenance_and_exported_pair(self):
        self.assertEqual(self.contract['native_sha256'], gate.NATIVE_SHA)
        self.assertEqual(len(self.contract['requirements']), 4)
        self.assertEqual([r['name'] for r in self.contract['requirements']],
                         ['isAvailable', 'getInstance', 'nativePrime', 'nativePublishAfterBind'])

    def test_good_fixture(self):
        checks, _ = self.fixture('good')
        self.assertTrue(all(r['passed'] for r in checks))

    def test_reference_is_not_definition(self):
        checks, _ = self.fixture('reference-only')
        self.assertEqual([r['reason'] for r in checks[:2]], ['missing_class_definition'] * 2)
        self.assertTrue(all(r['passed'] for r in checks[2:]))

    def test_full_return_descriptor_matters(self):
        checks, _ = self.fixture('wrong-return')
        self.assertEqual(checks[1]['reason'], 'missing_exact_method')
        self.assertEqual(checks[1]['observed_overloads'][0]['descriptor'], '()Landroid/os/IBinder;')

    def test_static_flag(self):
        checks, _ = self.fixture('nonstatic')
        self.assertEqual(checks[0]['reason'], 'static_flag_mismatch')

    def test_native_flag(self):
        checks, _ = self.fixture('not-native')
        self.assertEqual(checks[2]['reason'], 'native_flag_mismatch')

    def test_multidex_and_inheritance(self):
        checks, inputs = self.fixture('multidex')
        self.assertTrue(all(r['passed'] for r in checks))
        self.assertEqual(len(inputs[0]['dex']), 2)
        self.assertEqual(checks[0]['dex'], 'classes2.dex')
        checks, _ = self.fixture('inherited')
        self.assertTrue(all(r['passed'] for r in checks))
        self.assertEqual(checks[0]['owner'], 'Lfixture/Parent;')

    def test_ambiguous_duplicate_rejected(self):
        checks, _ = self.fixture('duplicate')
        self.assertEqual(checks[0]['reason'], 'duplicate_class_definition')

    def test_native_hash_change_and_empty_zip(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / 'bad.so'; path.write_bytes(b'not the pinned runtime')
            with self.assertRaisesRegex(ValueError, 'SHA mismatch'):
                gate.native_contract(SOURCE, path)
            jar = Path(tmp) / 'no-dex.jar'
            with zipfile.ZipFile(jar, 'w') as z: z.writestr('classes1xdex', b'not dex')
            with self.assertRaisesRegex(ValueError, 'missing or duplicate'):
                gate.dex_definitions([jar])

    def test_cli_exit_and_machine_receipt(self):
        with tempfile.TemporaryDirectory() as tmp:
            output = Path(tmp) / 'receipt.json'
            for name, expected in [('good', 0), ('wrong-return', 1)]:
                p = subprocess.run([sys.executable, str(ROOT / 'scripts/lab/check_webview_jni.py'),
                                    '--jar', str(P / 'fixtures' / (name + '.jar')), '--out', str(output)],
                                   capture_output=True, text=True)
                self.assertEqual(p.returncode, expected, p.stderr)
                self.assertEqual(json.loads(p.stdout), json.loads(output.read_text()))
                self.assertFalse(json.loads(p.stdout)['device_io'])

    def test_malformed_dex_is_input_error_not_pass(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / 'corrupt.jar'
            with zipfile.ZipFile(path, 'w') as z: z.writestr('classes.dex', b'not a dex file')
            p = subprocess.run([sys.executable, str(ROOT / 'scripts/lab/check_webview_jni.py'), '--jar', str(path)],
                               capture_output=True, text=True)
            self.assertEqual(p.returncode, 2)
            self.assertFalse(json.loads(p.stdout)['passed'])
            self.assertIn('input_error', json.loads(p.stdout))


class RealPair(unittest.TestCase):
    def test_real_j5_fails_j5b_passes(self):
        pins = json.loads((P / 'pair-inputs.json').read_text())
        for name, expected in [('j5', False), ('j5b', True)]:
            row = pins[name]
            self.assertIsNotNone(row, 'actual J5b not delivered; never substitute a fixture')
            path = lab_paths.workspaces() / row['path']
            self.assertEqual(gate.digest(path.read_bytes()), row['sha256'])
            result = gate.check([path], SOURCE, NATIVE)
            self.assertEqual(result['passed'], expected, result['checks'])
            if name == 'j5':
                self.assertEqual([r['reason'] for r in result['checks'][:2]], ['missing_class_definition'] * 2)
            recorded = json.loads((P / (name + '.json')).read_text())
            self.assertEqual(result['jars'][0]['sha256'], recorded['jars'][0]['sha256'])
            self.assertEqual(result['checks'], recorded['checks'])


if __name__ == '__main__': unittest.main()
