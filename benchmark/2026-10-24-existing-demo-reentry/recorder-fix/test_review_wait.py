import ast
import copy
import hashlib
import json
import os
from pathlib import Path
import sys
import tempfile
import types
import unittest

import review_wait as gate
HERE=Path(__file__).resolve().parent

class Clock:
    def __init__(self, at=66.5):self.at=at;self.hook=None
    def now(self):return self.at
    def sleep(self, delay):
        self.at+=delay
        if self.hook:self.hook(self.at)

class ReviewTests(unittest.TestCase):
    def setUp(self):
        (HERE/'.fixtures').mkdir(exist_ok=True)
        self.temp=tempfile.TemporaryDirectory(dir=HERE/'.fixtures');self.run=Path(self.temp.name)
        self.data=b'\xff\xd8'+b'x'*200;(self.run/'initial.jpeg').write_bytes(self.data)
        self.expected={'run_id':self.run.name,'serial':'61b','boot':'boot','image':'initial.jpeg','image_sha256':hashlib.sha256(self.data).hexdigest()}
        self.clock={'wallclock':'2026-10-24T10:34:06.993177+08:00','monotonic':0}
        self.review={**self.expected,'verdict':'host_white','reviewer':'outer-codex','timestamp':'2026-10-24T10:35:13.381710+08:00','elapsed':66.388396}
    def tearDown(self):self.temp.cleanup()
    def write(self, value=None):
        (self.run/'outer-review.json').write_text(json.dumps(self.review if value is None else value))
    def invoke(self, clock=None, continuation=None):
        c=clock or Clock();events=[]
        def go(decision):events.append(('continue',os.getpid(),decision['deadlines']));continuation and continuation()
        def clean():events.append(('cleanup',os.getpid()))
        result=gate.reviewed_tail(self.run,self.expected,self.clock,go,clean,c.now,c.sleep)
        return result,events,c
    def test_timely_real_schema_same_process_once(self):
        self.write();r,e,c=self.invoke();self.assertEqual([x[0] for x in e],['continue','cleanup']);self.assertEqual(e[0][1],e[1][1]);self.assertEqual(e[0][2],{'review':120,'click':180,'active':360,'total':480});self.assertLess(c.at,120)
    def test_absent_deadline(self):
        r,e,c=self.invoke();self.assertEqual(e,[('cleanup',os.getpid())]);self.assertEqual(c.at,120)
    def test_invalid_fields(self):
        for field in ('run_id','serial','boot','image_sha256','image','verdict','reviewer','timestamp'):
            with self.subTest(field=field):
                bad=copy.deepcopy(self.review);bad[field]='';self.write(bad)
                r,e,c=self.invoke();self.assertEqual([x[0] for x in e],['cleanup']);self.assertEqual(c.at,120)
    def test_half_json_not_approval_then_complete(self):
        (self.run/'outer-review.json').write_text('{');c=Clock();c.hook=lambda at:self.write() if at>=67 else None
        r,e,c=self.invoke(c);self.assertEqual([x[0] for x in e],['continue','cleanup']);self.assertGreaterEqual(c.at,67)
    def test_after_deadline_even_backdated(self):
        self.write();r,e,c=self.invoke(Clock(120.1));self.assertEqual([x[0] for x in e],['cleanup'])
    def test_credential_unknown_usable_stop(self):
        for v in ('credential','unknown','usable_toutiao'):
            with self.subTest(v=v):
                (self.run/'review-consumed.json').unlink(missing_ok=True);self.review['verdict']=v;self.write();r,e,c=self.invoke();self.assertEqual([x[0] for x in e],['cleanup'])
    def test_changed_image(self):
        self.write();(self.run/'initial.jpeg').write_bytes(b'other');r,e,c=self.invoke();self.assertEqual([x[0] for x in e],['cleanup'])
    def test_explicit_cleanup(self):
        self.write();(self.run/'cleanup-now').touch();r,e,c=self.invoke();self.assertEqual([x[0] for x in e],['cleanup'])
    def test_continuation_error_cleanup_once(self):
        self.write();events=[]
        def boom(d):events.append('continue');raise RuntimeError('simulated failure')
        with self.assertRaises(RuntimeError):gate.reviewed_tail(self.run,self.expected,self.clock,boom,lambda:events.append('cleanup'),Clock().now,lambda _:None)
        self.assertEqual(events,['continue','cleanup'])
    def test_exclusive_atomic_publish(self):
        p=self.run/'receipt.json';gate.publish_once(p,{'a':1});old=p.read_bytes()
        with self.assertRaises(FileExistsError):gate.publish_once(p,{'a':2})
        self.assertEqual(p.read_bytes(),old);self.assertEqual(list(self.run.glob('.receipt.json.*')),[])
    def test_consumption_cannot_repeat(self):
        self.write();self.invoke();events=[]
        with self.assertRaises(FileExistsError):gate.reviewed_tail(self.run,self.expected,self.clock,lambda d:events.append('continue'),lambda:events.append('cleanup'),Clock().now,lambda _:None)
        self.assertEqual(events,['cleanup'])
    def test_old_actual_loop_counterexample(self):
        self.write();c=Clock()
        # Exact old waiting condition/body (captured in diagnosis with raw source SHA).
        while c.now()<self.clock['monotonic']+120:
            if (self.run/'cleanup-now').exists():break
            c.sleep(min(.25,max(0,self.clock['monotonic']+120-c.now())))
        self.assertEqual(c.at,120);self.assertTrue((self.run/'outer-review.json').exists())
    def test_candidate_real_cli_full_unlock_review_home_click_cleanup(self):
        import subprocess
        for mode in ('valid','absent','invalid','continuation_error'):
            with self.subTest(mode=mode):
                run=self.run/mode;run.mkdir()
                result=subprocess.run([sys.executable,str(HERE/'fixture_cli.py'),str(run),mode],capture_output=True,text=True,timeout=15)
                self.assertEqual(result.returncode,0,result.stderr)
                facts=json.loads((run/'fixture-result.json').read_text());labels=[x['label'] for x in facts['calls']]
                self.assertEqual(labels.count('unlock-once'),1)
                self.assertEqual(labels.count('cleanup-restore'),1);self.assertEqual(labels.count('cleanup-unlock'),1)
                self.assertEqual({x['pid'] for x in facts['calls']},{facts['pid']})
                self.assertTrue(facts['released']);self.assertEqual(facts['device_calls'],0)
                if mode=='valid':
                    self.assertEqual(labels.count('home'),1);self.assertEqual(labels.count('click-once'),1)
                    consumed=json.loads((run/'review-consumed.json').read_text());self.assertEqual(consumed['review']['image'],'unlocked.jpeg');self.assertLess(consumed['elapsed'],67)
                    self.assertLess(next(x['at'] for x in facts['calls'] if x['label']=='click-once'),180)
                    self.assertEqual(len([x for x in labels if x.startswith('s') and x.endswith('-shot')]),5)
                elif mode=='continuation_error':self.assertEqual(labels.count('home'),1);self.assertEqual(labels.count('click-once'),0)
                else:self.assertEqual(labels.count('home'),0);self.assertEqual(labels.count('click-once'),0);self.assertGreaterEqual(facts['elapsed'],120)
    def test_actual_receipt_helper_refuses_duplicate_before_execution(self):
        import importlib.util
        import shutil
        import time
        folder=self.run/'receipt-helper';folder.mkdir()
        shutil.copyfile(HERE/'receipt_candidate.py',folder/'receipt_candidate.py')
        (folder/'context.json').write_text(json.dumps({'main':str(folder),'run':str(folder)}))
        (folder/'plan.json').write_text('{}')
        (folder/'clock.json').write_text(json.dumps({'monotonic':time.monotonic()}))
        spec=importlib.util.spec_from_file_location('exclusive_receipt_test',folder/'receipt_candidate.py');mod=importlib.util.module_from_spec(spec);spec.loader.exec_module(mod)
        cmd={'argv':[sys.executable,'-c','print("synthetic-local-command")'],'timeout_seconds':2}
        rec,stdout,stderr=mod.call('fixture-only',cmd)
        self.assertEqual(rec['rc'],0);self.assertEqual(stderr,'')
        before={x.name:x.read_bytes() for x in folder.glob('fixture-only.*')}
        with self.assertRaises(FileExistsError):mod.call('fixture-only',cmd)
        self.assertEqual(before,{x.name:x.read_bytes() for x in folder.glob('fixture-only.*')})
    def test_no_pid_handoff_in_candidate(self):
        s=(HERE/'initial_stage_candidate.py').read_text();self.assertNotIn('os.kill',s);self.assertNotIn('SIGTERM',s);self.assertNotIn('oldpid',s)

if __name__=='__main__':unittest.main(verbosity=2)
