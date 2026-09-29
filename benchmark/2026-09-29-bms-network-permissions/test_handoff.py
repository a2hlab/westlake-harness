"""Exercise actual handoff apply/rollback with an in-memory board; no device I/O."""
import contextlib
import io
import importlib.util
import json
from pathlib import Path
import shlex
import tempfile
import unittest
from unittest.mock import patch

E = Path(__file__).resolve().parent
spec = importlib.util.spec_from_file_location('b89_swap', E/'swap_services.py')
s = importlib.util.module_from_spec(spec)
spec.loader.exec_module(s)

class FakeBoard:
    live = {}
    failed = False
    fail_once = False
    lane = None
    writes = []
    def __init__(self, serial, hdc, lock, lane, out):
        assert serial == s.SERIAL
        self.boot = 'test-boot'
        FakeBoard.lane = lane
    def ready(self): pass
    def send(self, path, target): self.live[target] = s.b.sha(path)
    def shell(self, cmd, **kwargs):
        args = shlex.split(cmd)
        if args[0] == 'sha256sum':
            return 0, '\n'.join(self.live[p]+'  '+p for p in args[1:])
        self.writes.append(cmd)
        if '&&' in args:
            for segment in cmd.split(' && '):
                part = shlex.split(segment)
                if part[0] == 'test': assert part[-1] not in self.live
                if part[0] == 'cp': self.live[part[-1]] = self.live[part[-2]]
                if part[0] == 'mv':
                    if self.fail_once and not self.failed:
                        FakeBoard.failed = True
                        raise RuntimeError('injected rename failure')
                    self.live[part[-1]] = self.live.pop(part[-2])
        return 0, ''

class HandoffTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        s.BASE = Path(self.tmp.name)/'state'
        s.KIT = Path(self.tmp.name)/'kit';s.KIT.mkdir()
        for n in s.LIBS: (s.KIT/n).write_bytes(n.encode())
        s.LIBS = {n:s.b.sha(s.KIT/n) for n in s.LIBS}
        FakeBoard.live = {p:s.MANIFEST['baseline'][Path(p).name] for p in s.PATHS}
        FakeBoard.live.update({p:'a'*64 for p in ['/system/bin/appspawn-x','/system/android/framework/oh-adapter-runtime.jar','/system/android/lib64/liboh_adapter_bridge.so']})
        FakeBoard.failed=False;FakeBoard.fail_once=False;FakeBoard.writes=[]
    def tearDown(self): self.tmp.cleanup()
    def run_action(self, action):
        with patch.object(s.b,'Board',FakeBoard), patch('sys.argv',['swap',action]), contextlib.redirect_stdout(io.StringIO()):s.main()
    def test_apply_and_exact_rollback(self):
        self.run_action('apply')
        self.assertEqual(FakeBoard.lane,'cc-wiki')
        for p in s.PATHS:self.assertEqual(FakeBoard.live[p],s.LIBS[Path(p).name])
        self.run_action('rollback')
        for p in s.PATHS:self.assertEqual(FakeBoard.live[p],s.MANIFEST['baseline'][Path(p).name])
    def test_partial_apply_restores_pair(self):
        FakeBoard.fail_once=True
        with self.assertRaisesRegex(RuntimeError,'injected'):self.run_action('apply')
        for p in s.PATHS:self.assertEqual(FakeBoard.live[p],s.MANIFEST['baseline'][Path(p).name])
    def test_changed_baseline_rejected_before_writes(self):
        FakeBoard.live[s.PATHS[0]]='b'*64
        with self.assertRaisesRegex(AssertionError,'baseline'):self.run_action('apply')
        self.assertFalse(FakeBoard.writes)
    def test_changed_candidate_rejected_before_writes(self):
        (s.KIT/next(iter(s.LIBS))).write_bytes(b'changed')
        with self.assertRaisesRegex(RuntimeError,'candidate'):self.run_action('apply')
        self.assertFalse(FakeBoard.writes)

if __name__=='__main__':unittest.main()
