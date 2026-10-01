import hashlib
import json
from pathlib import Path
import subprocess
import tempfile
import unittest
import base64
import os

import collect
import make_handoff

HERE = Path(__file__).resolve().parent


class EvidenceTests(unittest.TestCase):
    def test_four_keys_and_artifact_identity(self):
        evidence = json.loads((HERE / 'evidence.json').read_text())
        self.assertEqual({row['key'] for row in evidence['rows']}, collect.KEYS)
        self.assertEqual(evidence['artifact_identity']['exit'], 0)
        self.assertEqual(evidence['u8_alias_paths'], [])
        for label, provider in evidence['providers'].items():
            self.assertEqual(provider['sha256'], collect.PINS[label])
        self.assertEqual(evidence['providers']['alias']['soname'], ['libz.so'])
        self.assertEqual(evidence['providers']['alias']['needed'], ['libshared_libz.z.so'])

    def test_exact_consumer_coverage(self):
        evidence = json.loads((HERE / 'evidence.json').read_text())
        consumers = {row['key']: row['native_consumer'] for row in evidence['rows']}
        self.assertIn('libz.so', consumers['burgerking']['needed'])
        self.assertIn('crc32', consumers['burgerking']['undefined'])
        collect.require_coverage(['crc32'], evidence['providers']['zlib']['defined'])
        self.assertIn('libz.so', consumers['fd-im-vector-app']['needed'])
        imports = {'slCreateEngine', 'SL_IID_ENGINE', 'SL_IID_VOLUME', 'SL_IID_PLAY', 'SL_IID_ANDROIDSIMPLEBUFFERQUEUE'}
        self.assertTrue(imports <= set(consumers['mindustry']['undefined']))
        collect.require_coverage(imports - {'SL_IID_ANDROIDSIMPLEBUFFERQUEUE'} | {'SL_IID_BUFFERQUEUE'},
                                 evidence['providers']['oh_audio']['defined'])
        self.assertNotIn('slCreateEngine', evidence['providers']['android_audio']['defined'])

    def test_media_jni_not_mediandk(self):
        evidence = json.loads((HERE / 'evidence.json').read_text())
        media = evidence['media']
        self.assertEqual(media['requested_library'], 'libmedia_jni.so')
        self.assertFalse(media['mediandk_unlock_proven'])
        self.assertFalse(media['JNI_OnLoad_exported'])
        row = next(row for row in evidence['rows'] if row['key'] == 'cv2-com-chessclock-android')
        self.assertIsNone(row['native_consumer'])
        self.assertTrue(any('native_init=1 native_setup=1' in item['text'] for item in row['evidence']))
        self.assertTrue(any(item['line'] == 39509 and 'MediaPlayer.<clinit>' in item['text'] for item in row['evidence']))

    def test_hash_and_symbol_mismatch_rejected(self):
        with self.assertRaises(ValueError):
            collect.verify(b'changed', hashlib.sha256(b'original').hexdigest())
        with self.assertRaises(ValueError):
            collect.require_coverage(['slCreateEngine'], {'SL_IID_ENGINE': {}})


class HandoffTests(unittest.TestCase):
    def test_engine_forwarding_and_failures(self):
        with tempfile.TemporaryDirectory() as directory:
            binary = Path(directory) / 'engine'
            subprocess.run(['/usr/bin/clang', '-std=c11', '-O2', '-Wall', '-Wextra', '-Werror',
                str(HERE / 'opensles-owner.c'), str(HERE / 'test_engine.c'), '-o', str(binary)], check=True)
            for mode in ['bound', 'unbound']:
                subprocess.run([str(binary), mode], check=True)

    def test_actual_owner_router_and_negative_controls(self):
        with tempfile.TemporaryDirectory() as directory:
            binary = Path(directory) / 'routes'
            subprocess.run(['/usr/bin/clang', '-std=c11', '-O2', '-Wall', '-Wextra', '-Werror',
                            str(HERE / 'test_routes.c'), '-o', str(binary)], check=True)
            for mode in ['bound', 'missing', 'iid-missing', 'bind-missing', 'bind-failed', 'owner-failed', 'facade-failed', 'wrong-owner']:
                subprocess.run([str(binary), mode], check=True)

    def test_source_bound_patches(self):
        bases = json.loads((HERE / 'source-bases.json').read_text())
        sources = make_handoff.proposal(bases['policy'], bases['header'], bases['loader'], bases['host'], bases['policy_checker'])
        actual = make_handoff.patches(sources)
        host = next(after for target, (before, after) in sources.items() if target.endswith('westlake_stock_host_main.c'))
        self.assertIn('strncmp(missing_original_search, "/system/android/lib64/westlake_native:"', host)
        self.assertEqual(actual, json.loads((HERE / 'patches.json').read_text())['patches'])
        with self.assertRaises(ValueError):
            make_handoff.proposal(bases['policy'], bases['header'].replace('SystemLibrary, 4', 'SystemLibrary, 6'), bases['loader'], bases['host'])

    def test_distinguishing_precheck(self):
        entries = json.loads((HERE / 'offline-precheck.json').read_text())
        self.assertFalse(entries['window_authorized'])
        for component in entries['components']:
            precheck = component['offline_precheck']
            self.assertNotEqual(precheck['expect']['confirm'], precheck['expect']['refute'])
            self.assertEqual(precheck['result'], 'not-falsified')
        self.assertIn('native-gates-exit-0-or-fresh-approved-exceptions', entries['required_before_window'])

    def test_built_facade_identity_and_imports(self):
        receipt = json.loads((HERE / 'facade-build.json').read_text())
        data = base64.b64decode((HERE / 'facade.so.b64').read_bytes())
        collect.verify(data, receipt['artifact_sha256'])
        for name, pin in receipt['sources'].items():
            collect.verify((HERE / name).read_bytes(), pin)
        with tempfile.TemporaryDirectory() as directory:
            artifact = Path(directory) / 'libOpenSLES.so'
            artifact.write_bytes(data)
            result = collect.elf(artifact, receipt['artifact_sha256'], '/opt/homebrew/opt/llvm/bin/llvm-readelf')
        self.assertEqual(result['soname'], ['libOpenSLES.so'])
        self.assertEqual(result['needed'], [])
        required = {'slCreateEngine', 'SL_IID_ENGINE', 'SL_IID_VOLUME', 'SL_IID_PLAY', 'SL_IID_ANDROIDSIMPLEBUFFERQUEUE'}
        collect.require_coverage(required, result['defined'])
        for name in required - {'slCreateEngine'}:
            self.assertEqual(result['defined'][name], dict(type='OBJECT', size=8))

    def test_overlay_retains_private_scope_and_refuses_existing_destination(self):
        import stage_overlay
        workspaces = Path(os.environ.get('WORKSPACES', HERE.parents[2]))
        alias_root = workspaces / '01.OH61AOSP16/real-work'
        if not alias_root.exists():
            self.skipTest('Persistent donor workspace not available; no staging claim')
        with tempfile.TemporaryDirectory() as directory:
            destination = Path(directory) / 'overlay'
            result = stage_overlay.overlay(workspaces, destination)
            self.assertEqual(len(result['files']), 3)
            self.assertEqual(result['status'], 'overlay-only-not-deployable')
            self.assertFalse((destination / result['forbidden_root_alias']).exists())
            with self.assertRaises(ValueError):
                stage_overlay.overlay(workspaces, destination)


class PolicyTests(unittest.TestCase):
    def test_real_system_loader_and_policy(self):
        bases = json.loads((HERE / 'source-bases.json').read_text())
        source = make_handoff.proposal(bases['policy'], bases['header'], bases['loader'], bases['host'], bases['policy_checker'])
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            for relative, (before, after) in source.items():
                if relative.startswith(make_handoff.POLICY):
                    target = root / relative.removeprefix(make_handoff.POLICY)
                    target.parent.mkdir(parents=True, exist_ok=True)
                    target.write_text(after)
            for name, text in bases['loader_headers'].items():
                (root / 'src' / name).write_text(text)
            subprocess.run(['python3', str(root / 'tests/verify_bridge_policy.py')], check=True)
            manifest = root / 'policy/native_bridge_policy.v1.json'
            valid = manifest.read_text()
            manifest.write_text(valid.replace('liboh_android_runtime.so', 'wrong-owner.so'))
            header = root / 'include/nativeloader/native_bridge_policy.h'
            header_valid = header.read_text()
            header.write_text(header_valid.replace('liboh_android_runtime.so', 'wrong-owner.so'))
            rejected = subprocess.run(['python3', str(root / 'tests/verify_bridge_policy.py')], capture_output=True)
            self.assertNotEqual(rejected.returncode, 0)
            manifest.write_text(valid)
            header.write_text(header_valid)
            binary = root / 'policy-probe'
            subprocess.run(['/usr/bin/clang++', '-std=c++17', '-O2', '-Wall', '-Wextra', '-Werror',
                '-include', str(HERE / 'namespace-type-host.h'),
                '-I' + str(root / 'include'), '-I' + str(root / 'src'), '-I' + str(root / 'src/jni'),
                str(root / 'src/system_loader.cpp'), str(HERE / 'test_policy.cpp'), '-o', str(binary)], check=True)
            subprocess.run([str(binary)], check=True)


if __name__ == '__main__':
    unittest.main()
