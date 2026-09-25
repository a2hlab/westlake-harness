"""Offline failure-path tests. No device or real sysctl operations."""
import json
from pathlib import Path
import subprocess
import tempfile
import unittest
import apply_all_fixes as apply
from verify_logs import verify

RUN = b'#!/system/bin/sh\nset -eu\nexport WESTLAKE_RUNTIME_ROOT=/data/local/tmp/asx\nexport WESTLAKE_ANDROID_NATIVE_TARGETS=libsscronet.so:liblynxsecurity.so\nexec appspawn-x\n'
TARGETS = ['libttcrypto.so','libttboringssl.so','libdelta.so','liblynxsecurity.so']

class RecipeTests(unittest.TestCase):
    def test_idempotent_targets_and_single_hook(self):
        one = apply.rewrite_run(RUN, TARGETS)
        self.assertEqual(one, apply.rewrite_run(one, TARGETS))
        self.assertEqual(one.count(apply.CHECK.encode()), 1)
        self.assertIn(b'libsscronet.so:liblynxsecurity.so:libttcrypto.so:libttboringssl.so:libdelta.so', one)

    def test_refuse_dynamic_or_duplicate_export(self):
        for bad in [RUN.replace(b'libsscronet.so:', b'$(touch forbidden):'),
                    RUN+b'export WESTLAKE_ANDROID_NATIVE_TARGETS=liba.so\n']:
            with self.assertRaises(ValueError): apply.rewrite_run(bad, TARGETS)

    def test_source_or_baseline_mismatch_before_writes(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d); stage = root/'stage'; stage.mkdir(); workspace = root/'ws'; workspace.mkdir()
            (stage/'run.sh').write_bytes(RUN); (stage/'library.so').write_bytes(b'original')
            (workspace/'patch.so').write_bytes(b'corrupt')
            m = dict(targets=TARGETS, binaries=[dict(source='patch.so', destination='library.so',
                    original_sha256=apply.digest(b'original'), sha256=apply.digest(b'patched'))])
            with self.assertRaises(ValueError): apply.plan(stage, workspace, m)
            self.assertEqual((stage/'library.so').read_bytes(), b'original')
            self.assertFalse((stage/'.stability46').exists())
            (workspace/'patch.so').write_bytes(b'patched'); (stage/'library.so').write_bytes(b'new integration')
            with self.assertRaises(ValueError): apply.plan(stage, workspace, m)
            self.assertEqual((stage/'library.so').read_bytes(), b'new integration')

    def test_symlink_escape_refused(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d); (root/'sub').symlink_to('/tmp', target_is_directory=True)
            with self.assertRaises(ValueError): apply.confined(root, 'sub/anything')

    def test_hook_sets_reads_back_and_gates_launch(self):
        with tempfile.TemporaryDirectory() as d:
            p = Path(d)/'sysctl'; p.write_text('65530\n')
            base = ['sh', str(apply.HERE/'prelaunch_map_count.sh'), '--file', str(p)]
            self.assertNotEqual(subprocess.run(base+['--check'], capture_output=True).returncode, 0)
            subprocess.run(base+['--', 'sh', '-c', 'exit 0'], check=True, capture_output=True)
            self.assertEqual(p.read_text(), '1048576\n')
            subprocess.run(base+['--check'], check=True, capture_output=True)
            p.write_text('2097152\n'); subprocess.run(base, check=True, capture_output=True)
            self.assertEqual(p.read_text(), '2097152\n')
            p.write_text('invalid\n')
            self.assertNotEqual(subprocess.run(base, capture_output=True).returncode, 0)

    def test_validation_requires_execution_and_rejects_errors(self):
        log = 'GLES library translated libGLESv2.so -> /system/lib64/platformsdk/libGLESv3.so\n'
        rows = [dict(uptime='1', maps='100', limit='1048576'), dict(uptime='11', maps='200', limit='1048576')]
        self.assertTrue(verify(log, rows)['passed'])
        for bad in ['', log+'UnsatisfiedLinkError', log+'Fatal signal 5 (SIGTRAP)']:
            self.assertFalse(verify(bad, rows)['passed'])
        self.assertFalse(verify(log, [])['passed'])
        rows[-1]['maps'] = '1048576'; self.assertFalse(verify(log, rows)['passed'])

if __name__ == '__main__': unittest.main()
