#!/usr/bin/env python3
import copy
import hashlib
import importlib.util
import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch
ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/'scripts/lab'))
import u7_executor as u

class ProvenanceTests(unittest.TestCase):
    def receipt(self):
        entry=json.loads(u.PROVENANCE_REGISTRY.read_text())['exceptions'][0]
        return dict(entry, status='verified-with-exception', exception_id=entry['id'])
    def test_approved_exact_evidence(self):
        self.assertTrue(u.approved_provenance(self.receipt()))
    def test_unapproved_and_changed_identity(self):
        for key in ['input_jars','outputs','frozen_tools','build_command','dex2oat_sha256','evidence','exception_id']:
            with self.subTest(key=key):
                receipt=self.receipt();receipt[key]='changed'
                with self.assertRaises(ValueError):u.approved_provenance(receipt)
    def test_revoked_approval(self):
        with tempfile.TemporaryDirectory() as td:
            data=json.loads(u.PROVENANCE_REGISTRY.read_text());data['exceptions'][0]['status']='revoked'
            path=Path(td)/'registry.json';path.write_text(json.dumps(data))
            with self.assertRaises(ValueError):u.approved_provenance(self.receipt(),path)
    def test_missing_and_tampered_evidence(self):
        with patch.object(u.bundle,'sha',return_value='wrong'):
            with self.assertRaisesRegex(ValueError,'evidence drift'):u.approved_provenance(self.receipt())
        self.assertFalse(u.approved_provenance({'status':'unknown'}))

class BaselineReplayTests(unittest.TestCase):
    def state(self):
        return {'plan':{'baseline':{'/system/android/a':'a','/system/android/b':'b','/system/bin/appspawn-x':'c','/system/lib64/platform.so':'d'}},
                'before_mounts':{'/system/android':[{'root':'/local/tmp/native/android','device':'1:2'}],
                 '/system/android/a':[{'root':'/local/tmp/J3/a','device':'1:2'}],
                 '/system/bin/appspawn-x':[{'root':'/local/tmp/native/host','device':'1:2'}],
                 '/data/app/unrelated':[{'root':'/anything','device':'1:2'}]}}
    def test_directory_then_jar_and_original_platform(self):
        rows,sources=u.baseline_replay_plan(self.state())
        self.assertEqual(sources,{'/data/local/tmp/J3/a':'a','/data/local/tmp/native/android/b':'b',
                                 '/data/local/tmp/native/host':'c','/system/lib64/platform.so':'d'})
        self.assertLess([r['target'] for r in rows].index('/system/android'),[r['target'] for r in rows].index('/system/android/a'))
    def test_unknown_mount_source_rejected(self):
        state=self.state();state['before_mounts']['/system/android'][0]['root']='/foreign'
        with self.assertRaises(ValueError):u.baseline_replay_plan(state)
    def test_same_boot_and_unexpected_overlay_no_write(self):
        p=fixture();io=Fake(p)
        with tempfile.TemporaryDirectory() as td:
            state=dict(self.state(),serial=io.serial,boot_id=io.boot)
            with self.assertRaises(RuntimeError):u.replay_baseline(io,state,Path(td)/'j')
            self.assertEqual(io.log,[])
            state['boot_id']='old'
            with self.assertRaisesRegex(RuntimeError,'unexpected baseline overlays'):u.replay_baseline(io,state,Path(td)/'j')
            self.assertEqual(io.log,[])
    def test_replay_success_and_source_corruption(self):
        for corrupt in [False,True]:
            with self.subTest(corrupt=corrupt),tempfile.TemporaryDirectory() as td:
                p=fixture();io=Fake(p);io.stack={};io.values={u.HOST:'old'};io.before={}
                plan={'baseline':{u.HOST:'new'},'generation':'g','reference_paths':{'runtime':[u.HOST]}}
                state={'serial':io.serial,'boot_id':'oldboot','plan':plan,
                       'before_mounts':{u.HOST:[{'root':'/local/tmp/base/host','device':'1:2'}]}}
                io.remote={'/data/local/tmp/base/host':'new'}
                def snapshot(paths,absent=()):
                    if paths==['/data/local/tmp/base/host']:
                        return {paths[0]:'wrong' if corrupt else 'new'},[]
                    return {x:io.values[x] for x in paths},[]
                io.snapshot=snapshot
                if corrupt:
                    with self.assertRaisesRegex(RuntimeError,'source SHA mismatch'):u.replay_baseline(io,state,Path(td)/'j')
                    self.assertEqual(io.log,[])
                else:
                    result=u.replay_baseline(io,state,Path(td)/'j')
                    self.assertEqual(result['status'],'baseline_restored')
                    self.assertEqual(io.log.count('start'),1)

class Crash(BaseException): pass

class Fake:
    def __init__(self, plan):
        self.serial='fake';self.boot='boot';self.values=dict(plan['baseline']);self.running=True
        self.stack={'/system/android':[{'root':'native-baseline'}],
                    u.bundle.FW+'oh-adapter-runtime.jar':[{'root':'r8b'},{'root':'J3'}]}
        self.original=copy.deepcopy(self.stack);self.log=[];self.remote={};self.before={}
        self.fail=None;self.count=0;self.verify_fail=False
    def guard(self,boot=None):
        if boot and self.boot!=boot:raise RuntimeError('boot drift')
    def snapshot(self,paths,absent=()):
        missing=[p for p in paths if p not in self.values]
        if not set(missing)<=set(absent):raise RuntimeError('missing')
        return {p:self.values[p] for p in paths if p in self.values},missing
    def mounts(self):return copy.deepcopy(self.stack)
    def stopped(self):return not self.running
    def stop(self):self.log.append('stop');self.running=False
    def start(self,digest):
        if self.values[u.HOST]!=digest:raise RuntimeError('wrong host')
        self.log.append('start');self.running=True
    def stage(self,plan,remote):
        result={}
        for i,row in enumerate(plan['changes']):
            path=remote+'/f'+str(i);result[row['target']]=path;self.remote[path]=row['sha256']
        return result
    def check_ticket(self,plan):pass
    def check_restore(self,plan):pass
    def placeholder(self,target):
        if target in self.values:raise RuntimeError('exists')
        self.values[target]=u.EMPTY
    def bind(self,remote,target):
        assert not self.running
        self.count+=1
        if self.fail==('before',self.count):raise RuntimeError('before bind')
        self.before[target]=self.values.get(target)
        self.stack.setdefault(target,[]).append({'root':remote})
        self.values[target]=self.remote[remote];self.log.append(('bind',target))
        if self.fail==('after',self.count):raise RuntimeError('lost bind response')
        if self.fail==('crash',self.count):raise Crash()
    def assert_owned(self,op):
        s=self.stack.get(op['target'],[])
        if s!=op['before']+[{'root':op['remote']}]:raise RuntimeError('foreign mount')
    def unbind(self,target):
        assert not self.running
        self.stack[target].pop()
        if not self.stack[target]:del self.stack[target]
        self.values[target]=self.before[target];self.log.append(('unbind',target))
    def remove_placeholder(self,target):
        if target in self.values:
            if self.values[target]!=u.EMPTY:raise RuntimeError('modified placeholder')
            del self.values[target]
    def verify(self,expected,generation):
        self.log.append('verify')
        if self.verify_fail:
            self.verify_fail=False;raise RuntimeError('child failed')
        if self.values!=expected:raise RuntimeError('child identity')
        return {'passed':True}


def fixture():
    base={u.HOST:'a'*64,u.bundle.FW+'oh-adapter-runtime.jar':'b'*64,
          '/system/android/lib64/libx.so':'c'*64,'/system/lib64/route/libx.so':'c'*64}
    expected=dict(base);expected[u.HOST]='d'*64
    expected[u.bundle.FW+'oh-adapter-runtime.jar']='e'*64
    expected['/system/android/lib64/libx.so']=expected['/system/lib64/route/libx.so']='f'*64
    for p in u.bundle.IMAGE_TARGETS|{u.bundle.FW+'adapter-mainline-stubs.jar'}:
        base[p]='1'*64;expected[p]='2'*64
    added='/system/android/lib64/libnew.so';expected[added]='3'*64
    return dict(root='/fake',generation='g',baseline=base,expected=expected,additions=[added],
        changes=[dict(source=str(i),target=p,sha256=v) for i,(p,v) in enumerate(sorted(expected.items()))],
        reference_paths={'runtime':[u.HOST,u.bundle.FW+'oh-adapter-runtime.jar'],
                         'boot':sorted(u.bundle.IMAGE_TARGETS)})

class TransactionTests(unittest.TestCase):
    def test_success_and_explicit_rollback(self):
        p=fixture();io=Fake(p)
        with tempfile.TemporaryDirectory() as td:
            tx=u.Transaction(io,Path(td)/'journal.json',p);tx.apply()
            self.assertEqual(io.log.count('start'),1)
            self.assertGreater(io.log.index('start'),max(i for i,x in enumerate(io.log) if isinstance(x,tuple)))
            tx.rollback();self.assertEqual(io.values,p['baseline']);self.assertEqual(io.stack,io.original)
            self.assertEqual(tx.state['status'],'rolled_back')
    def test_reject_baseline_before_stop(self):
        p=fixture();io=Fake(p);io.values[u.HOST]='wrong'
        with tempfile.TemporaryDirectory() as td:
            with self.assertRaises(RuntimeError):u.Transaction(io,Path(td)/'j',p).apply()
        self.assertEqual(io.log,[])
    def test_aliases_share_transaction(self):
        p=fixture();io=Fake(p)
        with tempfile.TemporaryDirectory() as td:
            u.Transaction(io,Path(td)/'j',p).apply()
            self.assertEqual(io.values['/system/android/lib64/libx.so'],io.values['/system/lib64/route/libx.so'])
            self.assertEqual(io.log.count('stop'),1)

class RecoveryTests(unittest.TestCase):
    def test_activation_marker_loss_is_failsafe_without_replaying_write(self):
        source=ROOT/'benchmark/2026-09-28-bms-route-deploy/batch/bms_batch.py'
        spec=importlib.util.spec_from_file_location('marker_loss_batch',source)
        batch=importlib.util.module_from_spec(spec);spec.loader.exec_module(batch)
        p=fixture();io=Fake(p)
        with tempfile.TemporaryDirectory() as td:
            transport=batch.Board(sorted(batch.SERIALS)[0],'hdc','board-note','cx-t0',Path(td))
            calls=[]
            def missing(argv,timeout=60):
                calls.append(argv)
                return 0,'response lost after remote mutation'
            transport.command=missing
            original=io.verify
            def verify(expected,generation):
                if expected==p['expected']:
                    transport.raw_shell('mount --bind /candidate /target')
                return original(expected,generation)
            io.verify=verify
            tx=u.Transaction(io,Path(td)/'journal.json',p)
            with self.assertRaisesRegex(batch.BatchStop,'HDC lost remote status marker'):
                tx.apply()
            self.assertEqual(len(calls),1)
            self.assertEqual(io.values,p['baseline'])
            self.assertEqual(io.stack,io.original)
            self.assertTrue(io.running)
            self.assertEqual(tx.state['status'],'rolled_back')

    def test_every_bind_boundary(self):
        p=fixture()
        for position in ['before','after','crash']:
            for n in range(1,len(p['changes'])+1):
                with self.subTest(position=position,n=n),tempfile.TemporaryDirectory() as td:
                    io=Fake(p);io.fail=(position,n);path=Path(td)/'j';tx=u.Transaction(io,path,p)
                    with self.assertRaises((RuntimeError,Crash)):tx.apply()
                    if position=='crash':
                        self.assertFalse(io.running)
                        u.Transaction(io,path).rollback()
                    self.assertEqual(io.values,p['baseline']);self.assertEqual(io.stack,io.original)
                    self.assertEqual(json.loads(path.read_text())['status'],'rolled_back')
    def test_failed_child_rolls_back(self):
        p=fixture();io=Fake(p);io.verify_fail=True
        with tempfile.TemporaryDirectory() as td:
            tx=u.Transaction(io,Path(td)/'j',p)
            with self.assertRaisesRegex(RuntimeError,'child failed'):tx.apply()
            self.assertEqual(io.values,p['baseline']);self.assertTrue(io.running)
    def test_foreign_mount_retains_stop(self):
        p=fixture();io=Fake(p)
        with tempfile.TemporaryDirectory() as td:
            tx=u.Transaction(io,Path(td)/'j',p);tx.apply();target=p['changes'][-1]['target']
            io.stack[target].append({'root':'foreign'})
            with self.assertRaisesRegex(RuntimeError,'foreign'):tx.rollback()
            self.assertFalse(io.running);self.assertEqual(tx.state['status'],'recovery_required')
    def test_stage_corruption_and_restore_gate_failure(self):
        p=fixture();io=Fake(p)
        with tempfile.TemporaryDirectory() as td:
            tx=u.Transaction(io,Path(td)/'j',p)
            io.stage=lambda *a: (_ for _ in ()).throw(RuntimeError('staging corrupt'))
            with self.assertRaisesRegex(RuntimeError,'staging corrupt'):tx.apply()
            self.assertEqual(io.values,p['baseline'])
            self.assertFalse(any(isinstance(x,tuple) for x in io.log))
        io=Fake(p)
        with tempfile.TemporaryDirectory() as td:
            tx=u.Transaction(io,Path(td)/'j',p);tx.apply()
            io.check_restore=lambda *a: (_ for _ in ()).throw(RuntimeError('restore gate'))
            with self.assertRaisesRegex(RuntimeError,'restore gate'):tx.rollback()
            self.assertFalse(io.running);self.assertEqual(tx.state['status'],'recovery_required')
    def test_modified_absent_placeholder_not_deleted(self):
        p=fixture();io=Fake(p)
        with tempfile.TemporaryDirectory() as td:
            tx=u.Transaction(io,Path(td)/'j',p);tx.apply()
            target=p['additions'][0];io.before[target]='foreign contents'
            with self.assertRaisesRegex(RuntimeError,'modified placeholder'):tx.rollback()
            self.assertFalse(io.running);self.assertEqual(io.values[target],'foreign contents')
    def test_boot_drift_no_writes(self):
        p=fixture();io=Fake(p)
        with tempfile.TemporaryDirectory() as td:
            tx=u.Transaction(io,Path(td)/'j',p);tx.apply();before=list(io.log);io.boot='new'
            with self.assertRaisesRegex(RuntimeError,'boot drift'):tx.rollback()
            self.assertEqual(io.log,before)
    def test_rollback_interruption_resumes(self):
        p=fixture();io=Fake(p)
        with tempfile.TemporaryDirectory() as td:
            path=Path(td)/'j';tx=u.Transaction(io,path,p);tx.apply();original=io.unbind
            def crash(target):original(target);raise Crash()
            io.unbind=crash
            with self.assertRaises(Crash):tx.rollback()
            io.unbind=original;u.Transaction(io,path).rollback()
            self.assertEqual(io.values,p['baseline']);self.assertEqual(io.stack,io.original)

class PreflightTests(unittest.TestCase):
    def test_gate_reject_never_constructs_device(self):
        for mode in ['--dry-run','--apply']:
            with tempfile.TemporaryDirectory() as td,patch.object(u,'preflight',side_effect=RuntimeError('N2 refused')),patch.object(u,'DeviceIO') as dev:
                rc=u.main([mode,'--package','x','--baseline-native','y','--out',td+'/r'])
                self.assertEqual(rc,2);dev.assert_not_called()
    def test_unknown_receipt_blocks_apply_only(self):
        plan=dict(deployable=False,device_io=False,gates_passed=True,bundle_sha256='a'*64)
        with tempfile.TemporaryDirectory() as td,patch.object(u,'preflight',return_value=plan),patch.object(u,'DeviceIO') as dev:
            args=['--package','x','--baseline-native','y','--out',td+'/r']
            self.assertEqual(u.main(['--dry-run']+args),0)
            self.assertEqual(u.main(['--apply']+args),2);dev.assert_not_called()
    def test_real_adapter_guard_and_child_view(self):
        from types import SimpleNamespace
        from unittest.mock import Mock
        io=u.DeviceIO.__new__(u.DeviceIO)
        io.board=SimpleNamespace(ready=Mock(),boot='a')
        with self.assertRaisesRegex(RuntimeError,'boot changed'):io.guard('b')
        io.board.ready.assert_called_once()
        generation='a'*64
        route='/system/lib64/westlake/route-a/'+generation+'/'
        expected={u.HOST:'1'*64,'/system/android/lib64/liboh_adapter_bridge.so':'2'*64}
        paths=[route+'libart.so',route+'libopenjdkjvm.so','/system/android/lib64/liboh_adapter_bridge.so']
        maps='\n'.join(f'1000-2000 r-xp 00000000 00:00 1 {p}' for p in paths)
        calls=[]
        def launch(board,app,remote,out,record,pages=10):calls.append(app['package'])
        io.b=SimpleNamespace(parse_bundle=lambda text,pkg:dict(uid=20001,desktop_activity='Main'),
                             cold_stop=lambda board,pkg,uid,out,tag:True,desktop_launch=launch)
        io.ps=lambda:[dict(pid=1,uid=0,ppid=0,name='appspawn-x'),dict(pid=2,uid=20001,ppid=1,name='appspawn-x')]
        io.shell=lambda c:maps if '/maps' in c else ''
        io.hashes=lambda p:{x:'1'*64 for x in p}
        io.snapshot=lambda p:({x:expected[x.split('/root',1)[1]] for x in p},[])
        with tempfile.TemporaryDirectory() as td,patch.object(u.time,'sleep'):
            io.out=Path(td);result=io.verify(expected,generation)
            self.assertEqual(result['child'],2);self.assertTrue(result['maps']['passed'])
            self.assertEqual(calls,['com.example.helloworld'])
    def test_mutation_during_gate_refused(self):
        with tempfile.TemporaryDirectory() as td:
            root=Path(td);(root/'bundle.json').write_text(json.dumps({'native':{'directory':'native'}}))
            plan=dict(expected={},baseline={},additions=[],rollout_ready=True,build_receipt={'status':'verified'})
            for changed in ['bundle','policy']:
                variants=[plan,dict(plan,rollout_ready=False)] if changed=='bundle' else [plan,plan]
                policies=['a','b'] if changed=='policy' else ['a','a']
                with patch.object(u,'prepare',side_effect=variants),patch.object(u,'policy_binding',side_effect=policies),patch.object(u.bundle,'image_checks',return_value={'G1':True,'G2':True}),patch.object(u.native_gate,'check',return_value={}),patch.object(u.native,'check_frozen_package'),patch.object(u.native,'check_frozen_restore'):
                    with self.assertRaisesRegex(RuntimeError,'changed during preflight'):u.preflight(root,root/'base',None)
    def test_ticket_drift(self):
        with patch.object(u,'prepare',return_value={'bundle_sha256':'changed'}):
            with self.assertRaisesRegex(RuntimeError,'drift'):u.unchanged({'root':'x','baseline_native':'y','bundle_sha256':'old'})
    def test_staging_sha_mismatch(self):
        effects=[]
        with self.assertRaisesRegex(RuntimeError,'staged SHA'):
            u.stage_file(lambda *a:effects.append('send'),lambda c:effects.append(c),lambda p:{p[0]:'wrong'},'local','remote','expected')
        self.assertEqual(effects,['send'])

if __name__=='__main__':unittest.main()
