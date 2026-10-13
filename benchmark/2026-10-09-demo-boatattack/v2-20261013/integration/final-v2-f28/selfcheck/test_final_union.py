"""Whole940 actual source admission, synthetic Boat expected changes; zero device calls."""
import copy,json,subprocess,sys,tempfile,unittest
from pathlib import Path
import compile_selfcheck as c
HERE=Path(__file__).resolve().parent
class Tests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.q=c.read(HERE/'request.5cd.pending.json');cls.binary,cls.r3=c.dependencies();base=cls.q['base'];binding=c.pin(base['activation_binding'],HERE)
        cls.proof,cls.history=cls.r3.admit(binding,c.sha(binding),True)
        cls.checked=c.read(c.pin(base['selfcheck'],HERE));cls.original={x['target']:x['actual'] for x in cls.checked['checks']}
        cls.seal=c.read(c.pin(cls.q['v1_seal'],HERE));pp=HERE.parent/'board5cd/provider/r4-reference/plan.disabled.json';cls.plan=c.read(pp)
        # The following is deliberately only a pure-union fixture, never admitted as an actual5cd plan.
        cls.q['placement_plan']=c.pinned(pp);cls.plan['synthetic']=True
        cls.observed_path=c.pin(base['observation'],HERE)
    def setUp(self):self.tmp=tempfile.TemporaryDirectory();self.root=Path(self.tmp.name)
    def tearDown(self):self.tmp.cleanup()
    def fixture(self):
        planned,seal=c.compose(self.q,self.plan,self.seal,self.proof,self.original,self.binary)
        sealpath=self.root/'candidate.json';c.save(sealpath,seal);request=self.root/'request.json';c.save(request,self.q)
        proof=c.runtime_view(self.proof,self.plan,sealpath,request,'a'*64)
        observation=c.read(self.observed_path);observation['synthetic']=True
        observation['files']=dict(planned['all_expected_sha256']);observation['packages']['com.Unity3d.BoatAttackDay']={'version_code':'1'}
        return planned,proof,observation
    def compare(self,proof,observation):return self.binary.original.compare(proof,observation,self.observed_path.parent,self.q['serial'],self.checked['current_boot'],True)
    def test_actual_source940_and_original487_history(self):
        self.assertEqual(self.history['history']['placed_count'],487);self.assertEqual(self.history['history']['executor_rc'],0)
        result=self.compare(self.proof,c.read(self.observed_path));self.assertTrue(result['passed']);self.assertEqual(result['file_count'],940)
    def test_one954_union_including_private3_and_T0_interface(self):
        planned,proof,obs=self.fixture();self.assertEqual(set(planned['inputs']),{'v1_seal','plan'});self.assertFalse(planned['signed'])
        self.assertEqual(planned['status'],'EXPECTED_UNION_NOT_OBSERVED');self.assertEqual(len(planned['all_expected_sha256']),954)
        self.assertEqual(sum('BoatAttackDay/android/lib/' in t for t in planned['all_expected_sha256']),3)
        result=self.compare(proof,obs);self.assertTrue(result['passed']);self.assertEqual(result['status'],'OFFLINE_MATCH');self.assertEqual(result['file_count'],954);self.assertTrue(result['synthetic'])
    def test_missing_private_and_unknown_runtime_SHA_fail(self):
        for fault in ['private','run']:
            with self.subTest(fault=fault):
                self.tmp.cleanup();self.tmp=tempfile.TemporaryDirectory();self.root=Path(self.tmp.name)
                planned,proof,obs=self.fixture()
                target=next(t for t in obs['files'] if 'BoatAttackDay/android/lib/' in t) if fault=='private' else next(t for t in obs['files'] if t.endswith('/run.sh'))
                if fault=='private':obs['files'].pop(target)
                else:obs['files'][target]='0'*64
                self.assertFalse(self.compare(proof,obs)['passed'])
    def test_Boat_APK_and_version_nonfile_gates_preserved(self):
        planned,proof,obs=self.fixture();obs['packages']['com.Unity3d.BoatAttackDay']['version_code']='2'
        with self.assertRaises(ValueError):self.compare(proof,obs)
        obs['packages']['com.Unity3d.BoatAttackDay']['version_code']='1';obs['files'][c.APK]='f'*64
        with self.assertRaises(ValueError):self.compare(proof,obs)
    def test_source_member_reduction_rejected(self):
        source=dict(self.original);source.pop(next(iter(source)))
        with self.assertRaises(ValueError):c.compose(self.q,self.plan,self.seal,self.proof,source,self.binary)
    def test_independent_current_WID_not_run_sh_guess(self):
        observation=c.read(self.observed_path);ref=observation['parameter_evidence']
        files,dynamic=self.binary.original.realization.running_files(self.proof,ref,self.observed_path.parent,self.checked['current_boot'])
        self.assertEqual(files[dynamic['target']],self.original[dynamic['target']])
        source=c.pin(ref,self.observed_path.parent);data=c.read(source);data['window_id']+=1
        for reading in data['readings'].values():
            if 'stdout' in reading:reading['stdout']['path']=str(c.path(reading['stdout']['path'],source.parent).resolve())
        changed=self.root/'forged-window.json';c.save(changed,data)
        with self.assertRaises(ValueError):self.binary.original.realization.running_files(self.proof,c.pinned(changed),self.root,self.checked['current_boot'])
    def test_pending_or_unregistered_plan_cannot_compile(self):
        for short in ['61b','5cd']:
            out=self.root/short
            p=subprocess.run([sys.executable,str(HERE/'compile_selfcheck.py'),'--request',str(HERE/('request.'+short+'.pending.json')),'--out',str(out)],capture_output=True,text=True)
            self.assertEqual(p.returncode,2,p.stderr);self.assertFalse(out.exists())
if __name__=='__main__':unittest.main(verbosity=2)
