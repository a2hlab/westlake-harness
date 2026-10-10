import argparse
import contextlib
import hashlib
import importlib.util
import io
import json
import os
from pathlib import Path
import shutil
import struct
import subprocess
import sys
import tarfile
import tempfile
import unittest
from unittest.mock import patch


HERE = Path(__file__).resolve().parent
REPO = HERE.parents[1]
sys.path.insert(0, str(REPO / 'scripts/lab'))
import demo_seal_61b as seal
import demo_toutiao_slot as slot

SPEC = importlib.util.spec_from_file_location('prepare_uid_slot', REPO / 'benchmark/2026-10-10-toutiao-boot-slot/prepare_payload.py')
prepare = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(prepare)
SOURCE_REPO = REPO if (REPO / 'benchmark/2026-10-10-u13-autostart/boot-slot-uid-dynamic').is_dir() else Path(os.environ.get('WORKSPACES', str(REPO.parent))) / 'westlake-harness'
DYNAMIC = SOURCE_REPO / 'benchmark/2026-10-10-u13-autostart/boot-slot-uid-dynamic'
DONOR = SOURCE_REPO / 'benchmark/2026-10-10-toutiao-boot-slot/payload'
BOOT = '22222222-2222-2222-2222-222222222222'


class StageTransport:
    def __init__(self, directory, document, immutable):
        self.calls = []
        self.uid = '20011206'
        self.fail_reconcile = False
        self.corrupt_immutable = False
        self.after_reconcile = False
        self.hashes = {row['target']: row['sha256'] for row in document['placements']}
        self.hashes.update({target: digest for digest, target in immutable})
        for row in document['placements']:
            if row['target'].startswith('/system/'):
                self.hashes[slot.ROOT + '/staged-system/' + Path(row['target']).name] = row['sha256']

    def run(self, name, argv):
        self.calls.append((name, argv))
        if name in ('tt-boot-before', 'tt-boot-before-enable'):
            return 0, BOOT
        if name == 'tt-host-uid' or name == 'tt-reconcile-readback':
            return 0, self.uid
        if name == 'tt-reconcile':
            self.after_reconcile = True
            return (1 if self.fail_reconcile else 0), self.uid
        if name in ('tt-stage-sha', 'tt-immutable-readback'):
            target = argv[-1].split()[-1]
            digest = self.hashes[target]
            if self.corrupt_immutable and self.after_reconcile and 'route-b-owner.sh' in target:
                digest = '0' * 64
            return 0, digest + '  ' + target
        return 0, ''


class UidSlotTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        inputs = self.root / 'inputs'
        inputs.mkdir()
        (inputs / 'source-host.hap').write_bytes(b'fixture-hap')
        for name in ('tt-rt.tar', 'tt-stage.tar', 'tt-wd.tar'):
            with tarfile.open(inputs / name, 'w') as archive:
                if name == 'tt-wd.tar':
                    data = b'fixture-screen-gate'
                    entry = tarfile.TarInfo('selfheal48/screen-gate')
                    entry.size = len(data)
                    archive.addfile(entry, io.BytesIO(data))
        self.digests = {path.name: prepare.sha(path) for path in inputs.iterdir()}
        self.args = argparse.Namespace(inputs=inputs, out=self.root / 'prepared', payload_dir=DONOR, uid_dynamic_dir=DYNAMIC)
        with patch.object(prepare, 'INPUTS', self.digests), contextlib.redirect_stdout(io.StringIO()):
            self.document = prepare.prepare(self.args)
        self.source_pins = [dict(path=str(DYNAMIC / name), sha256=seal.sha(DYNAMIC / name)) for name in slot.DYNAMIC]
        self.reference = dict(path=str(self.args.out / 'placement.json'), sha256=seal.sha(self.args.out / 'placement.json'))
        self.directory, self.document, self.immutable = slot.payload(self.reference, self.source_pins)
        self.transport = StageTransport(self.directory, self.document, self.immutable)

    def test_dynamic_sources_are_staged_verbatim(self):
        for name in slot.DYNAMIC:
            self.assertEqual((self.args.out / 'data/scripts' / name).read_bytes(), (DYNAMIC / name).read_bytes())
        self.assertNotIn('exact host UID 20010053', self.document['precondition'])
        self.assertEqual(self.document['uid_mode'], 'installed-host-dynamic')

    def test_six_names_and_all_placement_aliases_excluded(self):
        self.assertEqual(set(self.document['reconciled_names']), slot.MUTABLE)
        self.assertTrue(all(Path(target).name not in slot.MUTABLE for digest, target in self.immutable))
        for row in self.document['placements']:
            if Path(row['target']).name in slot.MUTABLE:
                self.assertEqual(row['identity_check'], 'reconcile-readback')
        self.assertIn(prepare.STAGE + '/request.bin', self.document['reconciled_targets'])
        self.assertEqual(self.document['reconcile_readback']['request_offsets'], [312, 316])

    def test_archives_worker_owner_reconciler_classifier_stay_pinned(self):
        names = {Path(target).name for digest, target in self.immutable}
        self.assertTrue(set(prepare.INPUTS) <= names)
        self.assertTrue(slot.DYNAMIC <= names)
        self.assertTrue({'appspawn-x', 'screen-gate'} <= names)

    def test_two_preparations_byte_identical(self):
        second = argparse.Namespace(**dict(vars(self.args), out=self.root / 'prepared-two'))
        with patch.object(prepare, 'INPUTS', self.digests), contextlib.redirect_stdout(io.StringIO()):
            prepare.prepare(second)
        for name in ('placement.json', 'immutable.tsv'):
            self.assertEqual((self.args.out / name).read_bytes(), (second.out / name).read_bytes())

    def test_content_pin_of_request_refuses(self):
        immutable = self.args.out / 'immutable.tsv'
        immutable.write_text(immutable.read_text() + 'a' * 64 + ' ' + prepare.STAGE + '/request.bin\n')
        self.document['immutable_tsv_sha256'] = seal.sha(immutable)
        (self.args.out / 'placement.json').write_text(json.dumps(self.document))
        self.reference['sha256'] = seal.sha(self.args.out / 'placement.json')
        with self.assertRaisesRegex(ValueError, 'must not be SHA-pinned'):
            slot.payload(self.reference, self.source_pins)

    def test_dynamic_uid_and_enable_order(self):
        for uid in ('20011206', '20012345'):
            with self.subTest(uid=uid):
                self.transport.uid = uid
                receipt = slot.stage(dict(hdc='mock-hdc'), self.document, self.directory, self.immutable,
                                     self.transport, BOOT, 'a' * 64)
                self.assertEqual(receipt['host_uid'], uid)
                self.assertTrue(receipt['immutable_preserved'])
        names = [name for name, argv in self.transport.calls]
        self.assertLess(names.index('tt-disabled'), names.index('tt-stage'))
        self.assertLess(names.index('tt-reconcile'), names.index('tt-cfg-enable'))
        enable = next(argv[-1] for name, argv in self.transport.calls if name == 'tt-cfg-enable')
        self.assertIn('cp ' + slot.CFG + '.disabled ' + slot.CFG, enable)
        self.assertIn('rm -f ' + slot.ROOT + '/DISABLED', enable)
        self.assertIn('mount -o ro,remount /', enable)
        result = subprocess.run(['/bin/bash', '-n'], input=enable, text=True, capture_output=True)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertTrue(all(not argv[-1].startswith('/system/') for name, argv in self.transport.calls if name == 'tt-stage'))

    def test_reconcile_failure_never_enables(self):
        self.transport.fail_reconcile = True
        with self.assertRaisesRegex(ValueError, 'tt-reconcile exit=1'):
            slot.stage(dict(hdc='mock-hdc'), self.document, self.directory, self.immutable,
                       self.transport, BOOT, 'a' * 64)
        self.assertNotIn('tt-cfg-enable', [name for name, argv in self.transport.calls])

    def test_reconcile_modifies_immutable_never_enables(self):
        self.transport.corrupt_immutable = True
        with self.assertRaisesRegex(ValueError, 'reconcile changed immutable'):
            slot.stage(dict(hdc='mock-hdc'), self.document, self.directory, self.immutable,
                       self.transport, BOOT, 'a' * 64)
        self.assertNotIn('tt-cfg-enable', [name for name, argv in self.transport.calls])

    def test_invalid_host_uid_refuses_before_stage(self):
        self.transport.uid = 'unreadable'
        with self.assertRaisesRegex(ValueError, 'numeric'):
            slot.stage(dict(hdc='mock-hdc'), self.document, self.directory, self.immutable,
                       self.transport, BOOT, 'a' * 64)
        self.assertNotIn('tt-stage', [name for name, argv in self.transport.calls])

    def test_default_provider_preview_has_no_transport(self):
        with patch.object(seal.Transport, 'run', side_effect=AssertionError('transport forbidden')):
            with contextlib.redirect_stdout(io.StringIO()):
                self.assertEqual(slot.main([]), 0)


if __name__ == '__main__':
    unittest.main()
