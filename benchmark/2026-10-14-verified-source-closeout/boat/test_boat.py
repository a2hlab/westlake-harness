#!/usr/bin/env python3
import importlib.util
import json
import os
from pathlib import Path
import subprocess
import tempfile
import unittest

HERE = Path(__file__).resolve().parent
REPO = next(p for p in HERE.parents if (p / 'sources/api-implementations/boat-v2-production/build.py').is_file())
SOURCE = REPO / 'sources/api-implementations/boat-v2-production'
spec = importlib.util.spec_from_file_location('boat_build', SOURCE / 'build.py')
module = importlib.util.module_from_spec(spec); spec.loader.exec_module(module)


class BoatCloseout(unittest.TestCase):
    def test_delivered_source_pins(self):
        module.sources()
        source = SOURCE / 'signal/src/unity_signal_box.c'
        self.assertEqual(module.digest(source), 'bb7732fa81128e37ec28f94248022fe8ec5f148941b642f39c2a142add0e5dbe')

    def test_original_sha_expectations_not_relaxed(self):
        lock = json.loads((SOURCE / 'dependencies.lock.json').read_text())
        self.assertEqual(lock['expected_outputs'], {
            'libunity.so': '1bea0fae1e6e76db15f17fca2bfa91b9c303ce278d6a4dcfba6af233b68b64ac',
            'libil2cpp.so': 'f6b806b5c55e702b98caa2e85d2f9afb678bc47dcc4067017b33f5269afed746',
            'libwestlake_bionic_signal_box.so': '7a931c79c0be28468bdd02a626a637431f2447f5fd0aba87176e5acdb071f5da'})
        self.assertEqual(len(lock['sdk_files']), 2418)

    def test_exact_replay_receipt(self):
        r = json.loads((HERE / 'evidence/transform-receipt.json').read_text())
        self.assertEqual(r['rc'], 0)
        self.assertEqual(len(r['outputs']), 2)
        self.assertTrue(all(x['equal'] and x['sha256'] == x['expected_sha256'] for x in r['outputs']))
        self.assertEqual(len(r['commands']), 6)
        self.assertTrue(all(x['rc'] == 0 for x in r['commands']))
        self.assertEqual(r['recipe_sha256'], module.digest(SOURCE / 'build.py'))
        self.assertEqual(r['source_lock_sha256'], module.digest(SOURCE / 'source.lock.json'))
        self.assertEqual(r['dependencies_lock_sha256'], module.digest(SOURCE / 'dependencies.lock.json'))

    def test_signal_diff_is_not_promoted(self):
        r = json.loads((HERE / 'evidence/signal-receipt.json').read_text())
        self.assertEqual(r['rc'], 2)
        self.assertEqual(r['status'], 'BUILD_SUCCEEDED_OUTPUT_DIFFERS')
        self.assertFalse(r['outputs'][0]['equal'])
        self.assertTrue(all(x['rc'] == 0 for x in r['commands']))
        self.assertEqual(len(r['commands']), 6)
        self.assertEqual(r['historical_logs'], 'unknown')
        self.assertEqual(r['recipe_sha256'], module.digest(SOURCE / 'build.py'))
        comparison = json.loads((HERE / 'signal-section-comparison.json').read_text())
        self.assertEqual([x['section'] for x in comparison['differences']], ['.note.gnu.build-id'])
        self.assertTrue(comparison['not_runtime_validation'])

    def test_wrong_patch_preimage_zero_write(self):
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp) / 'binary'; path.write_bytes(b'original')
            with self.assertRaisesRegex(ValueError, 'preimage'):
                module.patch_exact(path, 0, 'eeee', 'ffff')
            self.assertEqual(path.read_bytes(), b'original')

    def test_missing_dependency_rejected(self):
        with tempfile.TemporaryDirectory() as temp:
            with self.assertRaises(FileNotFoundError):
                module.check_sdk(Path(temp), {'sdk_files': [{'path': 'missing', 'sha256': '0' * 64}]})

    def test_wrong_apk_cli_retains_failure_no_tool_execution(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp); apk = root / 'wrong.apk'; apk.write_bytes(b'not signed input')
            out = root / 'run'
            done = subprocess.run(['python3', str(SOURCE / 'build.py'), 'transform', '--apk', str(apk),
                                   '--patchelf', str(root / 'must-not-execute'), '--out', str(out)],
                                  capture_output=True, text=True)
            self.assertEqual(done.returncode, 1)
            r = json.loads((out / 'receipt.json').read_text())
            self.assertEqual(r['status'], 'FAILED_EVIDENCE_RETAINED')
            self.assertEqual(r['commands'], [])
            self.assertFalse((out / 'libunity.so').exists())

    def test_fresh_output_only(self):
        with tempfile.TemporaryDirectory() as temp:
            done = subprocess.run(['python3', str(SOURCE / 'build.py'), 'signal', '--sdk', temp,
                                   '--out', temp], capture_output=True)
            self.assertNotEqual(done.returncode, 0)
            self.assertEqual(list(Path(temp).iterdir()), [])

    def test_entry_check_no_devices(self):
        r = subprocess.run(['python3', str(SOURCE / 'build.py'), 'check'], capture_output=True, text=True)
        self.assertEqual(r.returncode, 0)
        self.assertEqual(r.stdout.strip(), 'SOURCE_PINS_OK')


if __name__ == '__main__':
    unittest.main()
