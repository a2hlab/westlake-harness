#!/usr/bin/env python3
"""No device calls: real long local shell payloads and transport fault injection."""
import hashlib
import json
from pathlib import Path
import subprocess
import tempfile
import time
from types import SimpleNamespace
import unittest

import file_transport as ft

class Tests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory(prefix='t34-transport-')
        self.addCleanup(self.temp.cleanup)
        self.folder=Path(self.temp.name).resolve()
        self.events=[]
        self.payload=None
    def scope(self,mode):
        return SimpleNamespace(mode=mode,boot='3394710e-965c-47cc-a9f5-2b06f3d6c3f1',
                               holder='inner(cc-video) 999 2026-10-21T02:00:00+08:00',
                               start=1792519200,deadline=time.monotonic()+1000)
    def board(self,scope):
        owner=self
        class Board:
            serial=ft.SERIAL
            boot=scope.boot
            def ready(self):owner.events.append(('ready',None))
            def send(self,local,remote):
                owner.payload=local.read_bytes();owner.events.append(('send',remote))
        return Board()
    def original(self,board,command,timeout=60):
        self.events.append(('short',command))
        self.assertLess(len(command.encode()),ft.THRESHOLD)
        if '/system/bin/sh -eu ' in command:
            self.assertIn(hashlib.sha256(self.payload).hexdigest(),command)
            self.events.append(('execute',None))
            p=self.folder/'local-exact.sh';p.write_bytes(self.payload)
            r=subprocess.run(['bash','-eu',str(p)],capture_output=True)
            return r.returncode,r.stdout.decode()+r.stderr.decode()
        return 0,''
    def long(self,rc=0):
        return '( set -eu;\n#'+('x'*76038)+f'\nprintf "REAL_LOCAL_BODY\\n"; exit {rc}\n)'
    def test_apply_long_exact_bytes(self):
        s=self.scope('apply');text=self.long()
        rc,out=ft.adapter(self.original,s,self.folder)(self.board(s),text,60)
        self.assertEqual((rc,out),(0,'REAL_LOCAL_BODY\n'))
        self.assertEqual(self.payload,text.encode())
        self.assertEqual(sum(k=='execute' for k,_ in self.events),1)
    def test_rollback_long_exact_nonzero_rc(self):
        s=self.scope('rollback');text=self.long(37)
        rc,out=ft.adapter(self.original,s,self.folder)(self.board(s),text,60)
        self.assertEqual(rc,37);self.assertEqual(out,'REAL_LOCAL_BODY\n')
        receipt=json.loads((self.folder/'payload-01.json').read_text())
        self.assertEqual(receipt['remote_rc'],37)
        self.assertEqual(receipt['retries'],0)
    def test_lost_marker_never_retries_write(self):
        s=self.scope('apply');count=0
        def original(board,command,timeout):
            nonlocal count
            if '/system/bin/sh -eu ' in command:
                count+=1;raise RuntimeError('HDC lost remote status marker')
            return self.original(board,command,timeout)
        with self.assertRaisesRegex(RuntimeError,'lost remote'):
            ft.adapter(original,s,self.folder)(self.board(s),self.long(),60)
        self.assertEqual(count,1)
        rec=json.loads((self.folder/'payload-01.json').read_text())
        self.assertTrue(rec['device_writes_may_have_executed'])
        self.assertEqual(rec['execution_status'],'FAILED_OR_UNKNOWN_NO_RETRY')
    def test_send_or_sha_failure_does_not_execute(self):
        for fault in ('send','sha'):
            with self.subTest(fault=fault):
                folder=self.folder/fault;folder.mkdir()
                s=self.scope('apply');board=self.board(s)
                def original(b,command,timeout):
                    if fault=='sha' and 'sha256sum' in command:return 1,'hash mismatch'
                    return self.original(b,command,timeout)
                if fault=='send':
                    def send(*args):raise RuntimeError('send failed')
                    board.send=send
                with self.assertRaises((RuntimeError,AssertionError)):
                    ft.adapter(original,s,folder)(board,self.long(),60)
                self.assertEqual(sum(k=='execute' for k,_ in self.events),0)
    def test_expired_or_wrong_board_zero_dispatch(self):
        for fault in ('time','serial','boot'):
            with self.subTest(fault=fault):
                s=self.scope('apply');board=self.board(s)
                if fault=='time':s.deadline=time.monotonic()+500
                if fault=='serial':board.serial='5cd'
                if fault=='boot':board.boot='foreign'
                with self.assertRaises(AssertionError):
                    ft.adapter(self.original,s,self.folder)(board,self.long(),60)
                self.assertEqual(self.events,[])
    def test_short_command_keeps_original_path(self):
        s=self.scope('apply');board=self.board(s)
        self.assertEqual(ft.adapter(self.original,s,self.folder)(board,'printf short',7),(0,''))
        self.assertEqual(self.events,[('short','printf short')]);self.assertIsNone(self.payload)
    def test_explicit_no_remote_limit_claim_and_preview(self):
        root=Path(__file__).resolve().parents[1]
        r=subprocess.run(['python3',str(Path(__file__).with_name('file_transport.py')),
                          '--executor',str(root/'deployment/executor61b.py'),'--','apply'],capture_output=True)
        self.assertEqual(r.returncode,0,r.stderr)
        self.assertEqual(json.loads(r.stdout)['device_calls'],0)

if __name__=='__main__':unittest.main(verbosity=2)
