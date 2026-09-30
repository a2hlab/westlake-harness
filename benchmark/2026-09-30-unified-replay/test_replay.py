import copy
import hashlib
import importlib.util
import json
from pathlib import Path
import shlex
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
sys.path.insert(0, str(ROOT / 'scripts/lab'))
import replay_unified_state as r
sys.path.insert(0, str(ROOT / 'benchmark/2026-09-30-round1-plan/shard'))
import make_four_shards as four

BOOT = '12345678-1234-1234-1234-123456789012'

class FakeBoard:
    def __init__(self, recipe, depth=0):
        self.recipe = recipe
        self.boot = BOOT
        self.roots = ['/local/tmp/' + name + '/oh-adapter-runtime.jar' for name, _ in r.LAYERS[:depth]]
        self.root_view = None
        self.files = dict(recipe['expected'])
        self.files.update({'/data/local/tmp/' + name + '/oh-adapter-runtime.jar': sha for name, sha in r.LAYERS})
        self.calls = []
        self.mutations = []
        self.corrupt_send = False
        self.fail_mount = 0
        self.mounts = 0
        self.diverge_after_mount = False
        self.changed_pid = False
        self.lost_after_mount = False
        self.initial = list(self.roots)
        self.native_bad_root = False
        self.changed_native_after_mount = False

    def current_sha(self, roots):
        return self.files['/data' + roots[-1]] if roots else self.recipe['base']

    def shell(self, cmd):
        self.calls.append(cmd)
        if self.lost_after_mount and self.mounts:
            raise r.b.BatchStop('boot changed; stop batch')
        a = shlex.split(cmd)
        if a[0] == 'ps':
            return 0, 'PID PPID UID NAME\n100 1 0 appspawn-x\n200 100 20010000 appspawn-x\n300 200 0 appspawn-x\n'
        if a[:2] == ['readlink', '/proc/100/exe']:
            return 0, '/system/bin/appspawn-x'
        if a[:2] == ['cat', '/proc/100/stat']:
            start = '999' if self.changed_pid and self.mounts else '555'
            return 0, '100 (appspawn-x) ' + ' '.join(['S'] + ['0'] * 18 + [start] + ['0'] * 5)
        if a[0] == 'sha256sum':
            rows = []
            for path in a[1:]:
                root = path.startswith('/proc/100/root')
                raw = path.removeprefix('/proc/100/root')
                if raw == r.TARGET:
                    value = self.current_sha(self.root_view if root and self.root_view is not None else self.roots)
                else:
                    if raw not in self.files:
                        raise r.ReplayError('missing file: ' + raw)
                    value = self.files[raw]
                    if (root and self.native_bad_root or self.mounts and self.changed_native_after_mount) and raw in self.recipe['expected']:
                        value = 'e' * 64
                rows.append(value + '  ' + path)
            return 0, '\n'.join(rows)
        if a[0] == 'cat' and a[1].endswith('mountinfo'):
            roots = self.root_view if a[1] == '/proc/100/mountinfo' and self.root_view is not None else self.roots
            return 0, '\n'.join(f'{200+i} {199+i} 259:48 {root} {r.TARGET} rw - f2fs /dev/data rw' for i, root in enumerate(roots))
        if a[0] in ['mkdir', 'chmod']:
            self.mutations.append(cmd)
            return 0, ''
        if a[:2] == ['mount', '--bind']:
            self.mutations.append(cmd)
            self.mounts += 1
            if self.fail_mount == self.mounts:
                raise r.ReplayError('injected mount failure')
            self.roots.append(a[2].removeprefix('/data'))
            if self.diverge_after_mount:
                self.root_view = list(self.initial)
            return 0, ''
        if a[0] == 'umount':
            self.mutations.append(cmd)
            self.roots.pop()
            return 0, ''
        raise AssertionError('unexpected command ' + cmd)

    def send(self, local, remote):
        self.mutations.append('send ' + remote)
        i = self.recipe['files'].index(local)
        self.files[remote] = 'f' * 64 if self.corrupt_send else r.LAYERS[i][1]


def recipe():
    return dict(base='d' * 64, expected=dict(r.FZ1, **{'/system/android/lib64/libtest.so': 'a'*64}), files=[Path('J2'), Path('J3')])

class SuccessTests(unittest.TestCase):
    def test_base_then_idempotent(self):
        board = FakeBoard(recipe())
        result = {}
        r.replay(board, board.recipe, result)
        self.assertEqual(result['status'], 'replayed')
        self.assertEqual(len(board.roots), 2)
        self.assertIn(r.LAYERS[0][0], board.roots[0])
        self.assertIn(r.LAYERS[1][0], board.roots[1])
        writes = list(board.mutations)
        r.replay(board, board.recipe, result)
        self.assertEqual(result['status'], 'already_unified')
        self.assertEqual(board.mutations, writes)
        self.assertFalse(any('begetctl' in x or 'kill' in x or 'cp ' in x for x in board.calls))

    def test_partial_j2_only_adds_j3(self):
        board = FakeBoard(recipe(), 1)
        initial = list(board.roots)
        r.replay(board, board.recipe, {})
        self.assertEqual(board.roots[:1], initial)
        self.assertEqual(board.mounts, 1)
        self.assertEqual(sum(x.startswith('send ') for x in board.mutations), 1)

class RejectionTests(unittest.TestCase):
    def test_bad_native_installer_or_daemon_root_stops_before_write(self):
        for key in list(recipe()['expected']) + ['daemon']:
            with self.subTest(key=key):
                board = FakeBoard(recipe())
                if key == 'daemon': board.native_bad_root = True
                else: board.files[key] = 'b' * 64
                with self.assertRaises(r.ReplayError): r.replay(board, board.recipe, {})
                self.assertFalse(board.mutations)

    def test_unknown_overlay_or_inconsistent_roots_stops_before_write(self):
        for mode in ['foreign', 'root', 'third', 'jar']:
            with self.subTest(mode=mode):
                board = FakeBoard(recipe(), 1)
                if mode == 'foreign': board.roots[0] = '/local/tmp/experiment/oh-adapter-runtime.jar'
                if mode == 'root': board.root_view = []
                if mode == 'third': board.roots += board.roots * 2
                if mode == 'jar': board.files['/data'+board.roots[0]] = 'e'*64
                with self.assertRaises(r.ReplayError): r.replay(board, board.recipe, {})
                self.assertFalse(board.mutations)

    def test_corrupt_transfer_never_mounts(self):
        board = FakeBoard(recipe()); board.corrupt_send = True
        result = {}
        with self.assertRaisesRegex(r.ReplayError, 'staged'): r.replay(board, board.recipe, result)
        self.assertEqual(board.mounts, 0)
        self.assertEqual(board.roots, [])

    def test_second_mount_failure_unwinds_own_first_layer(self):
        board = FakeBoard(recipe()); board.fail_mount = 2
        result = {}
        with self.assertRaisesRegex(r.ReplayError, 'mount failure'): r.replay(board, board.recipe, result)
        self.assertEqual(board.roots, [])
        self.assertTrue(result['rollback'].startswith('verified_'))

    def test_existing_j2_preserved_on_j3_failure(self):
        board = FakeBoard(recipe(), 1); board.fail_mount = 1
        original = list(board.roots)
        with self.assertRaises(r.ReplayError): r.replay(board, board.recipe, {})
        self.assertEqual(board.roots, original)
        self.assertFalse(any(x.startswith('umount') for x in board.mutations))

    def test_mount_applied_but_remote_status_failed_unwinds_by_observed_stack(self):
        board = FakeBoard(recipe(), 1)
        original = list(board.roots)
        real_shell = board.shell
        def lost_status(cmd):
            out = real_shell(cmd)
            if cmd.startswith('mount --bind'):
                raise r.b.BatchStop('HDC lost remote status marker')
            return out
        board.shell = lost_status
        result = {}
        with self.assertRaises(r.b.BatchStop): r.replay(board, board.recipe, result)
        self.assertEqual(board.roots, original)
        self.assertTrue(result['rollback'].startswith('verified_'))

    def test_unpropagated_bind_rolls_back(self):
        board = FakeBoard(recipe()); board.diverge_after_mount = True
        result = {}
        with self.assertRaisesRegex(r.ReplayError, 'mount stacks differ'): r.replay(board, board.recipe, result)
        self.assertEqual(board.roots, [])
        self.assertTrue(result['rollback'].startswith('verified_'))

    def test_boot_or_pid_change_never_claims_rollback(self):
        for flag in ['lost_after_mount', 'changed_pid']:
            board = FakeBoard(recipe()); setattr(board, flag, True)
            result = {}
            with self.assertRaises((r.ReplayError, r.b.BatchStop)): r.replay(board, board.recipe, result)
            self.assertTrue(result['rollback'].startswith('unverified:'))
            self.assertFalse(any(x.startswith('umount') for x in board.mutations))

    def test_native_changed_during_replay_is_not_success(self):
        board = FakeBoard(recipe()); board.changed_native_after_mount = True
        result = {}
        with self.assertRaisesRegex(r.ReplayError, 'SHA mismatch'): r.replay(board, board.recipe, result)
        self.assertEqual(board.roots, [])
        self.assertNotIn('status', result)

    def test_transport_lock_target_and_boot_guards(self):
        for mode in ['wrong-lock', 'detached', 'reboot', 'missing-marker']:
            with self.subTest(mode=mode):
                board = object.__new__(r.Transport)
                board.serial, board.lane, board.hdc, board.lock = 'OH-SERIAL', 'cx-bms', ['hdc'], ['lock']
                board.boot = BOOT
                def command(argv, timeout=60):
                    if argv[0] == 'lock': return 0, 'other' if mode=='wrong-lock' else 'cx-bms'
                    if argv[1:3] == ['list','targets']: return 0, 'other' if mode=='detached' else 'OH-SERIAL'
                    raise AssertionError(argv)
                board.command = command
                board.raw_shell = lambda cmd: (0, '87654321-1234-1234-1234-123456789012' if mode=='reboot' else BOOT)
                if mode=='missing-marker':
                    board.command=lambda argv,timeout=60:(0,'Connect server failed')
                    with self.assertRaisesRegex(r.b.BatchStop,'status marker'): r.b.Board.raw_shell(board,'true')
                else:
                    with self.assertRaises(r.b.BatchStop): board.ready()

    def test_missing_and_changed_local_artifacts(self):
        with tempfile.TemporaryDirectory() as tmp:
            work = Path(tmp)
            with self.assertRaisesRegex(r.ReplayError,'missing N2'): r.inputs(work, work/'frozen.json')
            p = work/'westlake-generation-n2-51a78bde/package.json';p.parent.mkdir()
            p.write_text('{}')
            with self.assertRaisesRegex(r.ReplayError,'N2 manifest SHA differs'): r.inputs(work, work/'frozen.json')
            realw = r.lab_paths.workspaces()
            source = realw/'westlake-generation-n2-51a78bde/package.json';p.write_bytes(source.read_bytes())
            reg = realw/'westlake-harness/knowledge/frozen/frozen.json'
            with self.assertRaisesRegex(r.ReplayError,'missing j2'): r.inputs(work,reg)
            for name,_ in r.LAYERS:
                dest=work/'vm-copies'/name/'oh-adapter-runtime.jar';dest.parent.mkdir(parents=True)
                dest.write_bytes((realw/'vm-copies'/name/'oh-adapter-runtime.jar').read_bytes())
            self.assertEqual(len(r.inputs(work,reg)['files']),2)
            dest.write_bytes(b'changed J3')
            with self.assertRaisesRegex(r.ReplayError,'j3.*SHA differs'): r.inputs(work,reg)

    def test_wrapper_local_mode_is_one_json_line(self):
        out = subprocess.run(['bash',str(ROOT/'scripts/lab/replay_unified_state.sh'),'--check-inputs'],capture_output=True,text=True,check=True)
        self.assertEqual(len(out.stdout.splitlines()),1)
        row=json.loads(out.stdout)
        self.assertEqual(row['status'],'inputs_verified')
        self.assertEqual(row['device_validation'],'unverified')
        with tempfile.TemporaryDirectory() as tmp:
            out = subprocess.run(['bash',str(ROOT/'scripts/lab/replay_unified_state.sh'),'--check-inputs'],env=dict(__import__('os').environ,WORKSPACES=tmp),capture_output=True,text=True)
            self.assertNotEqual(out.returncode,0)
            self.assertIn('missing N2',json.loads(out.stdout)['reason'])

    def test_local_mode_out_never_overwrites_an_existing_receipt(self):
        with tempfile.TemporaryDirectory() as tmp:
            argv=['bash',str(ROOT/'scripts/lab/replay_unified_state.sh'),'--check-inputs','--out',tmp]
            out=subprocess.run(argv,capture_output=True,text=True,check=True)
            original=Path(tmp,'receipt.json').read_bytes()
            self.assertEqual(json.loads(out.stdout)['status'],'inputs_verified')
            out=subprocess.run(argv,capture_output=True,text=True)
            self.assertNotEqual(out.returncode,0)
            self.assertIn('fresh directory',json.loads(out.stdout)['reason'])
            self.assertEqual(Path(tmp,'receipt.json').read_bytes(),original)

class ShardTests(unittest.TestCase):
    def test_four_shards_cover_current_66_and_are_portable(self):
        plan = four.make_plan(r.lab_paths.workspaces())
        again = four.make_plan(r.lab_paths.workspaces())
        self.assertEqual(plan,again)
        shards=plan['shards'];flat=[k for s in shards for k in s['keys']]
        self.assertEqual(len(flat),len(set(flat)))
        self.assertEqual(set(flat),set(plan['expected_keys']))
        self.assertEqual([len(s['keys']) for s in shards],[17,17,16,16])
        self.assertIsNone(shards[-1]['serial'])
        self.assertTrue(plan['expected_apk_sha256']['subwaysurfers'].startswith('ffd32287'))
        self.assertNotIn(str(Path.home()),json.dumps(plan))
        with tempfile.TemporaryDirectory() as tmp:
            out=Path(tmp)/'plan';four.write_plan(plan,out)
            for s in shards:
                self.assertEqual((out/s['keys_file']).read_text().splitlines(),s['keys'])
                self.assertEqual(r.digest(out/s['keys_file']),s['keys_sha256'])
            with self.assertRaises(ValueError):four.write_plan(plan,out)

    def test_android_or_duplicate_fourth_is_rejected(self):
        for serial in ['N100CU025C18D000128','5ea34a4500000000000000001123012c','unknown']:
            with self.assertRaises(ValueError): four.make_plan(r.lab_paths.workspaces(),serial)

if __name__ == '__main__':
    unittest.main()
