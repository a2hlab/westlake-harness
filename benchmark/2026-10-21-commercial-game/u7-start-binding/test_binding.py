#!/usr/bin/env python3
"""Real DeviceIO -> Deployment.start -> apply_recipe; memory transport only.
Existing trusted U7 state-machine and label-shell fixtures are reused. Native
approval is stubbed; original ticket hashing and inherited start are not.
"""
import argparse,copy,hashlib,importlib.util,json,sys,tempfile,unittest
from contextlib import ExitStack
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch
HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[2]
sys.path.insert(0,str(ROOT/'scripts/lab'))
import u7_executor as u
import test_selinux_label_audit as label

def load(path,name):
    s=importlib.util.spec_from_file_location(name,path);m=importlib.util.module_from_spec(s);s.loader.exec_module(m);return m
legacy=load(ROOT/'benchmark/2026-10-01-u7-executor/test_executor.py','g22_legacy')
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def dump(p,data):p.parent.mkdir(parents=True,exist_ok=True);p.write_text(json.dumps(data,sort_keys=True)+'\n')

class MemoryIO(legacy.Fake,u.DeviceIO):
    start=u.DeviceIO.start
    check_ticket=u.DeviceIO.check_ticket
    check_restore=u.DeviceIO.check_restore
    def __init__(self,plan,out):
        legacy.Fake.__init__(self,plan);self.a=argparse.Namespace(no_label_recipe=False);self.m=None;self._start_context=None;self.out=out
        _,labels=label.fixture()
        for kind in ['candidate','baseline']:labels['/system/etc/g22-'+kind+'.json']='u:object_r:system_etc_file:s0'
        self.label_shell=label.FakeShell(labels);self.starts=[]
    def shell(self,command):
        if command=='begetctl start_service appspawn-x':
            reports=list(self.out.glob('label-recipe-*/after.json'));assert reports and all(json.loads(p.read_text())['status']=='PASS' for p in reports)
            latest=max(reports,key=lambda p:p.parent.name).parent/'plan.tsv'
            side=self._start_context['side'];other='baseline' if side=='candidate' else 'candidate'
            assert '/system/etc/g22-'+side+'.json' in latest.read_text()
            assert '/system/etc/g22-'+other+'.json' not in latest.read_text()
            self.starts.append(self._start_context['side']);self.running=True
        return self.label_shell(command)
    def ps(self):return [{'name':'appspawn-x','uid':0,'pid':123}] if self.running else []
    def hashes(self,paths):return {p:self.values[u.HOST] for p in paths}

class BindingTests(unittest.TestCase):
    def setUp(self):
        self.patches=ExitStack();self.addCleanup(self.patches.close)
        self.temp=tempfile.TemporaryDirectory();self.addCleanup(self.temp.cleanup);self.root=Path(self.temp.name)
        self.base=self.package('baseline');self.candidate=self.package('candidate')
        host=sha(self.base/'payload/runtime/appspawn-x');self.host=host
        old={u.HOST:host,'/system/android/lib64/libx.so':'1'*64};new=dict(old);new['/system/android/lib64/libx.so']='2'*64
        self.plan=dict(root=str(self.candidate.parent),baseline_native=str(self.base),baseline=old,expected=new,additions=[],generation='a'*64,changes=[dict(source='unused',target='/system/android/lib64/libx.so',sha256='2'*64)],reference_paths={'runtime':sorted(old)},native_tickets=[self.ticket(self.candidate),self.ticket(self.base)])
        self.io=MemoryIO(self.plan,self.root/'evidence');self.io.out.mkdir()
        def checked(plan):
            for ticket in plan['native_tickets']:u.native_gate.assert_unchanged(ticket)
        def native_check(package,expected_binding=None):
            ticket=self.ticket(Path(package));self.assertEqual(ticket['binding'],expected_binding);return ticket
        self.patches.enter_context(patch.object(u,'unchanged',side_effect=checked))
        self.patches.enter_context(patch.object(u.native_gate,'check',side_effect=native_check))
        self.patches.enter_context(patch.object(u.native,'check_frozen_package'))
        self.patches.enter_context(patch.object(u.native,'check_frozen_restore'))
        self.patches.enter_context(patch.object(u.native.time,'sleep'))
    def package(self,kind):
        root=self.root/kind/'native';plan,_=label.fixture();files={}
        for i,row in enumerate(plan['mounts']):
            if row['target']==u.HOST:name='payload/runtime/appspawn-x';content=b'same-host'
            elif row['target']=='/system/android':name='payload/android';content=b'bridge'
            else:name='payload/fixture'+str(i);content=b'unchanged'
            row['source']=name
            path=name+'/member' if row['kind']=='directory' else name
            if name=='payload/android':path=name+'/lib64/liboh_adapter_bridge.so'
            p=root/path;p.parent.mkdir(parents=True,exist_ok=True);p.write_bytes(content);files[path]=sha(p)
        name='payload/labels.json';(root/name).write_text(kind);files[name]=sha(root/name)
        plan['mounts'].append({'source':name,'target':'/system/etc/g22-'+kind+'.json','kind':'file'})
        bridge=files['payload/android/lib64/liboh_adapter_bridge.so']
        plan.update(schema=1,generation='a'*64,runtime_identity='deployment-only',bridge_sha256=bridge,files=files,live_hashes={u.HOST:files['payload/runtime/appspawn-x'],'/system/android/lib64/liboh_adapter_bridge.so':bridge},prerequisites={})
        dump(root/'package.json',plan);dump(root/'native-checks/native-gates.json',{})
        dump(root.parent/'bundle.json',{'native':{'directory':'native'}});return root
    def ticket(self,root):return {'package':str(root),'binding':u.native_gate.binding(root),'report':{'package_manifest_sha256':sha(root/'package.json')}}
    def check_targets(self,side):
        plans=[p.read_text() for p in self.io.out.glob('label-recipe-*/plan.tsv')]
        self.assertTrue(any('/system/etc/g22-'+side+'.json' in p for p in plans))
    def test_apply_uses_candidate_real_start(self):
        self.assertNotEqual(sha(self.base/'package.json'),sha(self.candidate/'package.json'))
        self.assertEqual(self.plan['expected'][u.HOST],self.plan['baseline'][u.HOST])
        state=u.Transaction(self.io,self.root/'journal',self.plan).apply()
        self.assertEqual(state['status'],'active_verified');self.assertEqual(self.io.starts,['candidate']);self.check_targets('candidate')
    def test_failed_apply_binds_baseline_before_real_restore_start(self):
        self.io.verify_fail=True
        with self.assertRaisesRegex(RuntimeError,'child failed'):u.Transaction(self.io,self.root/'journal',self.plan).apply()
        self.assertEqual(self.io.starts,['candidate','baseline']);self.check_targets('baseline')
        self.assertEqual(json.loads((self.root/'journal').read_text())['status'],'rolled_back')
    def test_explicit_rollback_uses_journal_baseline(self):
        u.Transaction(self.io,self.root/'journal',self.plan).apply()
        self.io._start_context=None;self.io.m=None
        state=u.Transaction(self.io,self.root/'journal').rollback()
        self.assertEqual(state['status'],'rolled_back');self.assertEqual(self.io.starts,['candidate','baseline']);self.check_targets('baseline')
    def test_baseline_replay_real_start(self):
        self.io.stack={};self.io.before={};self.io.values=dict(self.plan['baseline']);self.io.values[u.HOST]='0'*64
        source='/data/local/tmp/base/host';self.io.remote[source]=self.host;original=self.io.snapshot
        self.io.snapshot=lambda paths,absent=():({source:self.host},[]) if paths==[source,'/system/android/lib64/libx.so'] else original(paths,absent)
        # replay sources include unchanged platform values as well as the recorded host overlay.
        def snapshot(paths,absent=()):
            if source in paths:return {p:self.host if p==source else self.plan['baseline'][p] for p in paths},[]
            return original(paths,absent)
        self.io.snapshot=snapshot
        previous={'serial':self.io.serial,'boot_id':'oldboot','plan':self.plan,'before_mounts':{u.HOST:[{'root':'/local/tmp/base/host','device':'1:2'}]}}
        state=u.replay_baseline(self.io,previous,self.root/'replay')
        self.assertEqual(state['status'],'baseline_restored');self.assertEqual(self.io.starts,['baseline']);self.check_targets('baseline')
    def test_unbound_start_rejected_without_transport_and_readonly_works(self):
        io=u.DeviceIO.__new__(u.DeviceIO);io.shell=lambda command:'12 1 1:2 /root /system/android rw - tmpfs x rw'
        self.assertIn('/system/android',io.mounts())
        io.shell=lambda command:self.fail('unbound must not send any shell command')
        with self.assertRaisesRegex(RuntimeError,'verified manifest binding'):io.start(self.host)
    def test_constructor_stays_readonly_without_start_binding(self):
        board=SimpleNamespace(boot='boot',ready=lambda:None)
        module=SimpleNamespace(Board=lambda *args:board)
        spec=SimpleNamespace(loader=SimpleNamespace(exec_module=lambda m:None))
        with patch.object(u.sys,'platform','linux'),patch.object(u.importlib.util,'spec_from_file_location',return_value=spec),patch.object(u.importlib.util,'module_from_spec',return_value=module):
            io=u.DeviceIO(next(iter(u.native.SERIALS)),'offline-test',self.root/'readonly')
        io.guard();self.assertIsNone(io.m);self.assertIsNone(io._start_context)
        self.assertIs(io.a.no_label_recipe,False)
        with self.assertRaisesRegex(RuntimeError,'verified manifest binding'):io.start(self.host)
    def test_failed_restore_gate_clears_candidate_binding(self):
        self.io.check_ticket(self.plan)
        with patch.object(u.native_gate,'check',side_effect=RuntimeError('restore gate refused')):
            with self.assertRaisesRegex(RuntimeError,'restore gate refused'):self.io.check_restore(self.plan)
        with self.assertRaisesRegex(RuntimeError,'verified manifest binding'):self.io.start(self.host)
        self.assertEqual(self.io.label_shell.commands,[])
    def test_manifest_payload_sidecar_and_memory_drift_before_shell(self):
        for what in ['manifest','payload','sidecar','memory','host']:
            with self.subTest(what=what):
                self.io.check_ticket(self.plan);file=None
                if what=='manifest':file=self.candidate/'package.json'
                if what=='payload':file=self.candidate/'payload/runtime/appspawn-x'
                if what=='sidecar':file=self.candidate/'native-checks/native-gates.json'
                if file:before=file.read_bytes();file.write_bytes(before+b' ')
                if what=='memory':self.io.m['generation']='b'*64
                try:
                    with self.assertRaises(RuntimeError):self.io.start('f'*64 if what=='host' else self.host)
                    self.assertEqual(self.io.label_shell.commands,[])
                finally:
                    if file:file.write_bytes(before)
    def test_ticket_wrong_package_or_manifest_and_failed_rebind_clear_context(self):
        for change in ['package','manifest','gate']:
            with self.subTest(change=change):
                self.io.check_ticket(self.plan);p=copy.deepcopy(self.plan)
                if change=='package':p['native_tickets'][0]=copy.deepcopy(p['native_tickets'][1])
                if change=='manifest':p['native_tickets'][0]['report']['package_manifest_sha256']='0'*64
                if change=='gate':p['native_tickets'][0]['binding']='0'*64
                with self.assertRaises(RuntimeError):self.io.check_ticket(p)
                with self.assertRaisesRegex(RuntimeError,'verified manifest binding'):self.io.start(self.host)
                self.assertEqual(self.io.label_shell.commands,[])
    def test_label_rejection_keeps_service_stopped(self):
        self.io.check_ticket(self.plan);del self.io.label_shell.labels[label.GUARD]
        with self.assertRaisesRegex(RuntimeError,'missing mocked target'):self.io.start(self.host)
        self.assertNotIn('begetctl start_service appspawn-x',self.io.label_shell.commands)
        self.assertTrue(list(self.io.out.glob('label-recipe-*/failure.json')))

if __name__=='__main__':unittest.main(verbosity=2)
