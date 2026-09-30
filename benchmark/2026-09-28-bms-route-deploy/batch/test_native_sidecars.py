"""Exercise sidecar orchestration with a byte-addressed FakeBoard; no devices."""
import contextlib
import hashlib
import io
import json
from pathlib import Path
import shlex
import subprocess
import tempfile
import unittest
from unittest.mock import patch
import zipfile

import bms_batch as b
from test_bms_batch import FakeBoard, PKG, ABILITY

CODE = '/data/app/el1/bundle/public/' + PKG + '/android'
LIB = CODE + '/lib/arm64-v8a/'


def elf(machine=183):
    h = bytearray(64)
    h[:6] = b'\x7fELF\x02\x01'
    h[16:18] = (3).to_bytes(2, 'little')
    h[18:20] = machine.to_bytes(2, 'little')
    return bytes(h)


class NativeBoard(FakeBoard):
    def __init__(self, apk):
        super().__init__()
        self.files = {CODE+'/base.apk': apk, LIB+'unrelated.so': b'preserve me'}
        self.corrupt_stage = False
        self.corrupt_installed = False
        self.original_send = None

    def send(self, local, remote):
        super().send(local, remote)
        data = Path(local).read_bytes()
        if remote.endswith('original.apk'):
            self.original_send = data
        if self.corrupt_stage and '/native-sidecars/' in remote:
            data += b'corruption'
        self.files[remote] = data

    def shell(self, command, required=True, timeout=60):
        if command.startswith('sha256sum ') and shlex.split(command)[1] in self.files:
            self.calls.append(command)
            path = shlex.split(command)[1]
            return 0, hashlib.sha256(self.files[path]).hexdigest()+'  '+path
        if command.startswith('if test -e '):
            self.calls.append(command)
            path = shlex.split(command)[3].rstrip(';')
            return ((0, hashlib.sha256(self.files[path]).hexdigest()+'  '+path)
                    if path in self.files else (44, ''))
        if command.startswith('cp '):
            self.calls.append(command)
            _, source, target = shlex.split(command)
            self.files[target] = self.files[source] + (b'bad' if self.corrupt_installed else b'')
            return 0, ''
        return super().shell(command, required, timeout)


class NativeSidecarTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        self.inputs = self.root/'inputs'
        self.appdir = self.inputs/'app1'
        self.libdir = self.appdir/'lib/arm64-v8a'
        self.libdir.mkdir(parents=True)
        self.apk = self.appdir/'base.apk'
        with zipfile.ZipFile(self.apk, 'w') as archive:
            archive.writestr('AndroidManifest.xml', b'fixture manifest')
        self.original = self.apk.read_bytes()
        self.metadata = {'application': {'package': PKG, 'launch_activity': ABILITY,
                        'kind': 'original-apk-with-splits'}, 'apk_sha256': b.sha(self.apk)}
        for name in ('liba.so', 'libb.so'):
            (self.libdir/name).write_bytes(elf()+name.encode())
        self.entry = {'key': 'app1', 'phase': 'tail', 'native_sidecar_count': 2}
        self.write_metadata()

    def write_metadata(self):
        self.metadata['native_libraries'] = {
            'lib/arm64-v8a/'+p.name: {'sha256': b.sha(p), 'bytes': p.stat().st_size}
            for p in self.libdir.glob('*.so')}
        (self.appdir/'app-input.json').write_text(json.dumps(self.metadata))

    def tearDown(self):
        self.temp.cleanup()

    def collect(self, board=None, **kwargs):
        board = board or NativeBoard(self.original)
        with patch.object(b.time, 'sleep'):
            record = b.collect_app(board, self.entry, self.inputs, self.root/'out', '/stage',
                                   wait_seconds=3, **kwargs)
        return board, record

    def test_installs_after_cold_stop_before_click_preserves_apk(self):
        board, record = self.collect(reinstall=True, shots=[1], hilog_seconds=2, focus_check=True)
        self.assertEqual(record['native_assembly']['status'], 'verified')
        self.assertEqual(len(record['native_assembly']['files']), 2)
        self.assertTrue(record['clicked'])
        self.assertEqual(board.original_send, self.original)
        self.assertEqual(self.apk.read_bytes(), self.original)
        self.assertEqual(board.files[LIB+'unrelated.so'], b'preserve me')
        for name in ('liba.so', 'libb.so'):
            self.assertEqual(board.files[LIB+name], (self.libdir/name).read_bytes())
        cp = next(i for i,c in enumerate(board.calls) if c.startswith('cp '))
        stop = next(i for i,c in enumerate(board.calls) if c.startswith('aa force-stop '))
        click = board.calls.index('uitest uiInput click 200 300')
        self.assertLess(stop, cp)
        self.assertLess(cp, click)

    def test_missing_sidecars_stops_before_device(self):
        (self.libdir/'liba.so').unlink()
        board, record = self.collect()
        self.assertEqual(record['status'], 'app_failed')
        self.assertFalse(board.calls)

    def test_wrong_architecture_stops_before_device(self):
        (self.libdir/'liba.so').write_bytes(elf(40))
        self.write_metadata()
        board, record = self.collect()
        self.assertIn('not an AArch64', record['error'])
        self.assertFalse(board.calls)

    def test_input_metadata_digest_mismatch(self):
        (self.libdir/'liba.so').write_bytes(elf()+b'changed')
        board, record = self.collect()
        self.assertIn('differs from app-input', record['error'])
        self.assertFalse(board.calls)

    def test_staged_corruption_prevents_all_package_copies(self):
        board = NativeBoard(self.original); board.corrupt_stage = True
        board, record = self.collect(board)
        self.assertIn('staged native sidecar hash', record['error'])
        self.assertFalse(record['clicked'])
        self.assertFalse(any(c.startswith('cp ') for c in board.calls))

    def test_installed_corruption_prevents_launch_and_records_failure(self):
        board = NativeBoard(self.original); board.corrupt_installed = True
        board, record = self.collect(board)
        self.assertIn('installed native sidecar hash', record['error'])
        self.assertFalse(record['clicked'])
        self.assertEqual(json.loads((self.root/'out/native-assembly.json').read_text())['status'], 'failed')

    def test_launch_only_rejects_wrong_installed_apk(self):
        board = NativeBoard(b'other APK')
        board, record = self.collect(board, launch_only=True)
        self.assertIn('installed APK hash differs', record['error'])
        self.assertFalse(record['clicked'])
        self.assertFalse(any(c.startswith('bm install') or c.startswith('cp ') for c in board.calls))

    def test_launch_only_matching_existing_libraries_reused(self):
        board = NativeBoard(self.original)
        for p in self.libdir.glob('*.so'): board.files[LIB+p.name] = p.read_bytes()
        board, record = self.collect(board, launch_only=True)
        self.assertTrue(record['clicked'])
        self.assertFalse(any(c.startswith('cp ') or c.startswith('bm install') for c in board.calls))

    def test_existing_conflict_preserved_and_refused(self):
        board = NativeBoard(self.original); board.files[LIB+'liba.so'] = b'old different lib'
        board, record = self.collect(board)
        self.assertIn('installed native sidecar conflicts', record['error'])
        self.assertFalse(record['clicked'])
        self.assertEqual(board.files[LIB+'liba.so'], b'old different lib')

    def test_missing_remote_file_preserves_transport_status_marker(self):
        board, _ = self.collect()
        command = next(c for c in board.calls if c.startswith('if test -e '))
        command = command.replace(LIB, str(self.root/'missing')+'/')
        result = subprocess.run(['sh', '-c', command+'; sidecar_rc=$?; printf "__RC__%s" "$sidecar_rc"'],
                                capture_output=True, text=True, check=True)
        self.assertEqual(result.stdout, '__RC__44')

    def test_input_symlink_escape_rejected(self):
        external = self.root/'external.so'; external.write_bytes(elf())
        (self.libdir/'liba.so').unlink(); (self.libdir/'liba.so').symlink_to(external)
        board, record = self.collect()
        self.assertIn('invalid native sidecar', record['error'])
        self.assertFalse(board.calls)

    def test_embedded_conflict_rejected(self):
        with zipfile.ZipFile(self.apk, 'a') as archive:
            archive.writestr('lib/arm64-v8a/liba.so', elf()+b'other version')
        self.metadata['apk_sha256'] = b.sha(self.apk); self.write_metadata()
        board, record = self.collect()
        self.assertIn('conflicts with embedded APK', record['error'])
        self.assertFalse(board.calls)

    def test_resolved_plan_is_offline_and_lists_sidecars(self):
        manifest = self.root/'apps.json'; manifest.write_text(json.dumps({'apps': [self.entry]}))
        with patch.object(b.subprocess, 'run', side_effect=AssertionError('offline')), contextlib.redirect_stdout(io.StringIO()) as stdout:
            b.main(['--manifest',str(manifest),'--input-root',str(self.inputs),'--resolve-inputs'])
        plan = json.loads(stdout.getvalue())
        self.assertEqual(plan['execution'], 'not-requested')
        self.assertEqual(len(plan['apps'][0]['native_sidecars']), 2)


if __name__ == '__main__': unittest.main()
