"""Narrow5cd delta tests. Real source inventories; fake child process boundary only."""
import argparse,contextlib,copy,importlib.util,io,json,os,subprocess,sys,tempfile,unittest
from pathlib import Path
from unittest.mock import patch
HERE=Path(__file__).resolve().parent
REPO=next(p for p in HERE.parents if (p/'scripts/lab/lab_paths.py').is_file())
os.environ.setdefault('WORKSPACES',str(REPO.parent))
sys.path[:0]=[str(HERE/'entry'),str(HERE/'provider')]
import restore_entry as e, candidate_contract as c, source_5cd as src, prepare

def dump(p,x):p.write_text(json.dumps(x));return pin(p)
def pin(p):return {'path':str(p),'sha256':e.sha(p)}
class Tests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.root=Path(self.tmp.name);self.source=src.validate_sources();refs=self.source['refs'];self.boot=self.source['current_boot']
        self.plan=self.root/'plan.json';old=c.sources()[3]
        dump(self.plan,{'serial':e.SERIAL,'boot_id':self.boot,'execution_enabled':True,'installer_sha256':e.sha(HERE/'provider/installer.py'),'preserved':[{'target':t,'before':dict(exists=True,sha256=h,**self.source['metadata'][t])} for t,h in self.source['protected'].items()],'binds':old['binds']})
        self.seal=self.root/'seal.json';dump(self.seal,{'serial':e.SERIAL,'seal_stage':'v2'})
        self.dep=self.root/'dep.json';dump(self.dep,{'execution_enabled':True,'providers':[{'layer':'boatattack','program':pin(HERE/'provider/boat_provider.py'),'executor':pin(HERE/'provider/installer.py'),'action':'apply','prepared':pin(self.plan)}]})
        main=REPO.parent/'westlake-harness'
        self.data={'schema':'boat-v2-staged-restore/v1','phase':'placement','serial':e.SERIAL,'boot_id':self.boot,'signed_by':None,'execution_enabled':True,'route_b':{'mode':'verify-existing','entry':pin(main/'benchmark/2026-10-12-toutiao-recovery-review/r5-binary-collector/selfcheck_entry.py'),'realization':refs['realization'],'activation_binding':refs['activation_binding'],'hdc':pin(HERE/'test_rehearsal.py')},'boat':{'seal':pin(self.seal),'deployment':pin(self.dep),'program':pin(HERE/'provider/boat_provider.py')}}
    def tearDown(self):self.tmp.cleanup()
    def args(self,name='run',execute=True):
        p=self.root/(name+'.json');dump(p,self.data)
        return argparse.Namespace(v2_recipe=p,recipe_sha256=e.sha(p),out=self.root/name,execute=execute)
    def runner(self,fail=None,bad=False):
        calls=[]
        def run(argv,**kw):
            name=Path(argv[1]).name;calls.append(name);self.assertNotIn('timeout',kw)
            if name==fail:return subprocess.CompletedProcess(argv,2,'controlled failure','')
            out=Path(argv[argv.index('--out')+1])
            if name=='selfcheck_entry.py':
                self.assertEqual(argv[argv.index('--checker')+1],'activation');self.assertNotIn('--realization',argv)
                self.assertEqual(argv[argv.index('--boot-id')+1],self.boot)
                dump(out,dict(mode='live-readonly',status='PASS',passed=True,serial=e.SERIAL,boot_before=self.boot,boot_after=self.boot,activation={'realization':self.data['route_b']['realization'],'binding':{'sha256':'0'*64} if bad else self.data['route_b']['activation_binding']},checks=[dict(target=t,actual=h,equal=True) for t,h in self.source['all940'].items()]))
            elif name=='restore_recipe.py':
                out.mkdir();b=out/'activation-binding.json';dump(b,{'schema':'exact-activation-selfcheck-binding/v1','synthetic':False,'member_receipts':[{}]*487});(out/'directory-transaction').mkdir();a=out/'directory-transaction/applied.json';dump(a,{'executor_rc':0,'state':'ALREADY_EQUAL'});dump(out/'recipe-receipt.json',{'complete':not bad,'core_rc':0,'executor_rc':0,'reboots':0,'history_binding_sha256':e.sha(b),'directory_receipt_sha256':e.sha(a)})
            else:
                self.assertEqual(name,'boat_provider.py');out.mkdir();dump(out/'receipt.json',{'executor_rc':0,'status':'PLACED_PENDING_AUTHORIZED_SINGLE_BOOT','restored':False,'reboots':0,'serial':e.SERIAL,'plan_sha256':e.sha(self.plan)})
            return subprocess.CompletedProcess(argv,0,'recording runner, not device evidence','')
        return run,calls
    def test_actual5cd_inventory_control_and_observed_WID(self):
        self.assertEqual(len(self.source['all940']),940);self.assertEqual(len(self.source['protected']),488)
        self.assertEqual(self.source['host_uid'],20011300);self.assertEqual(self.source['historical_observed_window_id'],29)
        self.assertNotEqual(self.source['placement_boot'],self.boot)
        for t in self.source['protected']:
            if '/recovery-attempts/' in t:self.assertTrue(t.startswith(src.CONTROL+'/'))
        self.assertEqual(self.source['protected'][c.RT+'/run.sh'],'5a3aef638000e49f2a966b2179d57fe7628c29a4897921209fec539bd5dc1b79')
    def test_preview_and_real_activation_argv(self):
        with patch('subprocess.run',side_effect=AssertionError('NO DEVICE')),contextlib.redirect_stdout(io.StringIO()) as output:self.assertEqual(e.run(self.args(execute=False)),0)
        result=json.loads(output.getvalue());self.assertEqual(result['steps'][0]['argv'][3],'activation');self.assertFalse((self.root/'run').exists())
        runner,calls=self.runner();self.assertEqual(e.run(self.args(),runner),0);self.assertEqual(calls,['selfcheck_entry.py','boat_provider.py'])
    def test_activation_failure_or_binding_drift_stops_before_boat(self):
        for n,(fail,bad) in enumerate([('selfcheck_entry.py',False),(None,True)]):
            runner,calls=self.runner(fail,bad);self.assertEqual(e.run(self.args('fail'+str(n)),runner),2);self.assertEqual(len(calls),1)
    def test_wrong_serial_and_61b_proof_rejected(self):
        self.data['serial']='61b0657200000000000000000324012c'
        with self.assertRaises(ValueError):e.prepare(self.args())
        self.data['serial']=e.SERIAL;p=self.root/'foreign.json';actual=c.read(c.pinned(self.source['refs']['realization']));actual['parameters']['control_root']='/data/westlake-demo/toutiao/recovery-attempts/FOREIGN';self.data['route_b']['realization']=dump(p,actual)
        with self.assertRaises(ValueError):e.prepare(self.args())
    def test_original_full_restore_and_directory_completion_before_boat(self):
        main=REPO.parent/'westlake-harness';manifest=self.root/'directory-manifest.json';dump(manifest,{'serial':e.SERIAL,'boot_id':self.boot})
        recipe=self.root/'directory-recipe.json';dump(recipe,{'mode':'restore-then-complete','core':{'realization':self.data['route_b']['realization']},'supplement':{'manifest':pin(manifest)}})
        self.data['route_b'].update(mode='restore-directory-complete',entry=pin(main/'benchmark/2026-10-12-exact-realization/r4b-directory-logdir/restore_recipe.py'),directory_recipe=pin(recipe))
        for name,fail,bad in [('ok',None,False),('rc','restore_recipe.py',False),('incomplete',None,True)]:
            runner,calls=self.runner(fail,bad);self.assertEqual(e.run(self.args(name),runner),0 if name=='ok' else 2)
            self.assertEqual(calls,['restore_recipe.py','boat_provider.py'] if name=='ok' else ['restore_recipe.py'])
    def test_940_reduction_rejected(self):
        original=src.read
        def edited(p):
            x=original(p)
            if Path(p).name=='result.json' and 'expected' in x:x['actual'].pop(next(iter(x['actual'])))
            return x
        with patch.object(src,'read',side_effect=edited),self.assertRaises(ValueError):src.validate_sources()
if __name__=='__main__':unittest.main(verbosity=2)
