import argparse,contextlib,copy,hashlib,io,json,os,subprocess,sys,tempfile,unittest
from pathlib import Path
from unittest.mock import patch
HERE=Path(__file__).resolve().parent
sys.path.insert(0,str(HERE));import restore_entry as e
WS=Path(os.environ.get('WORKSPACES',str(HERE.parents[5]))).resolve();MAIN=WS/'westlake-harness'
REPO=next(p for p in HERE.parents if (p/'scripts/lab/demo_restore.sh').is_file())
def dump(p,obj):p.write_text(json.dumps(obj));return pin(p)
def pin(p):return {'path':str(p),'sha256':e.sha(p)}
class EntryTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.root=Path(self.tmp.name);self.boot='11111111-1111-1111-1111-111111111111'
        self.proof=self.root/'proof.json';dump(self.proof,{'schema':'exact-realization/v1','parameters':{'serial':e.SERIAL,'boot_id':self.boot}})
        self.plan=self.root/'plan.json';exe=HERE.parent/'final-v2-candidate-r2/installer.py'
        dump(self.plan,{'serial':e.SERIAL,'boot_id':self.boot,'execution_enabled':True,'installer_sha256':e.sha(exe),'preserved':[{'target':'/route-b-required','before':{'sha256':'a'*64}}],'binds':[]})
        self.seal=self.root/'seal.json';dump(self.seal,{'serial':e.SERIAL,'seal_stage':'v2'})
        self.dep=self.root/'dep.json';provider=HERE.parent/'final-v2-candidate-r2/boat_provider.py'
        dump(self.dep,{'execution_enabled':True,'providers':[{'layer':'boatattack','program':pin(provider),'executor':pin(exe),'action':'apply','prepared':pin(self.plan)}]})
        self.data={'schema':'boat-v2-staged-restore/v1','phase':'placement','serial':e.SERIAL,'boot_id':self.boot,'signed_by':None,'execution_enabled':True,
                   'route_b':{'mode':'verify-existing','entry':pin(MAIN/'benchmark/2026-10-12-toutiao-recovery-review/r5-binary-collector/selfcheck_entry.py'),'realization':pin(self.proof),'hdc':pin(HERE/'count_union.py')},
                   'boat':{'seal':pin(self.seal),'deployment':pin(self.dep),'program':pin(provider)}}
    def tearDown(self):self.tmp.cleanup()
    def args(self,execute=True):
        recipe=self.root/'recipe.json';dump(recipe,self.data)
        return argparse.Namespace(v2_recipe=recipe,recipe_sha256=e.sha(recipe),out=self.root/'run',execute=execute)
    def runner(self,fail=None,bad=None):
        calls=[]
        def run(argv,**kw):
            name=Path(argv[1]).name;calls.append(name)
            self.assertNotIn('timeout',kw) # Preserve the child transaction's own budget.
            if name==fail:return subprocess.CompletedProcess(argv,3,'failed','controlled')
            out=Path(argv[argv.index('--out')+1])
            if name=='selfcheck_entry.py':
                dump(out,dict(realization=pin(self.proof),mode='live-readonly',status='FAIL' if bad=='route' else 'PASS',passed=True,serial=e.SERIAL,boot_before=self.boot,boot_after=self.boot,checks=[{'target':'/route-b-required','actual':'a'*64,'equal':True}]))
            elif name=='exact_realization.py':
                out.mkdir();dump(Path(str(out)+'.realization-receipt.json'),{'executor_rc':0,'action':'apply'})
                for n in range(487):dump(out/('placed-%03d.json'%n),{'synthetic_test_boundary':True})
            elif name=='build_binding.py':dump(out,{'schema':'exact-activation-selfcheck-binding/v1','member_receipts':[{}]*487})
            elif name=='boat_provider.py':
                out.mkdir();dump(out/'receipt.json',dict(executor_rc=0,status='BAD' if bad=='boat' else 'PLACED_PENDING_AUTHORIZED_SINGLE_BOOT',restored=False,reboots=0,serial=e.SERIAL,plan_sha256=e.sha(self.plan)))
            elif name=='prepare_boat.py':
                out.mkdir();dump(out/'preinstall-receipt.json',dict(status='PREINSTALL_COMPLETE_PENDING_FRESH_CAPTURE',serial=e.SERIAL,boot_id=self.boot,stock_libraries_preserved=True,provider_compiled=False))
            else:raise AssertionError(name)
            return subprocess.CompletedProcess(argv,0,'fixture boundary','')
        return run,calls
    def test_verified_route_b_then_boat(self):
        runner,calls=self.runner();self.assertEqual(e.run(self.args(),runner),0)
        self.assertEqual(calls,['selfcheck_entry.py','boat_provider.py']);self.assertFalse(e.read(self.root/'run/staged-receipt.json')['restored'])
    def test_each_failure_stops_and_no_false_success(self):
        for fail,bad,wanted in [('selfcheck_entry.py',None,1),('boat_provider.py',None,2),(None,'route',1),(None,'boat',2)]:
            with self.subTest(fail=fail,bad=bad):
                args=self.args();args.out=self.root/('run-'+str(fail)+'-'+str(bad));runner,calls=self.runner(fail,bad)
                self.assertEqual(e.run(args,runner),2);self.assertEqual(len(calls),wanted)
    def test_restore_history_then_boat_and_history_failure(self):
        base=MAIN/'benchmark/2026-10-12-exact-realization';rb=self.data['route_b'];rb.update(mode='restore',entry=pin(base/'r2-timeout/exact_realization.py'),history_builder=pin(base/'r3-activation-selfcheck/build_binding.py'),restore_adapter=pin(base/'r2-timeout/restore.py'),execution_cwd=str(self.root))
        for field in ['prepared_manifest','admission','authorization','lock_tool']:f=self.root/(field+'.json');dump(f,{});rb[field]=pin(f)
        for fail,expected in [(None,3),('build_binding.py',2),('exact_realization.py',1)]:
            args=self.args();args.out=self.root/('restore-'+str(fail));runner,calls=self.runner(fail)
            self.assertEqual(e.run(args,runner),0 if fail is None else 2);self.assertEqual(len(calls),expected)
    def test_preinstall_is_a_capture_barrier(self):
        request=self.root/'preinstall.json';dump(request,{'serial':e.SERIAL,'boot_id':self.boot})
        self.data.update(phase='preinstall',preinstall={'program':pin(HERE/'prepare_boat.py'),'request':pin(request)})
        runner,calls=self.runner();self.assertEqual(e.run(self.args(),runner),0);self.assertEqual(calls,['prepare_boat.py'])
        self.assertEqual(e.read(self.root/'run/staged-receipt.json')['status'],'PREINSTALL_COMPLETE_PENDING_FRESH_CAPTURE')
    def test_default_preview_zero_calls(self):
        with contextlib.redirect_stdout(io.StringIO()) as output, patch('subprocess.run',side_effect=AssertionError('no devices')):
            self.assertEqual(e.run(self.args(False)),0)
        self.assertTrue(json.loads(output.getvalue()))
        self.assertFalse((self.root/'run').exists())
    def test_wrapper_v1_unchanged_and_all_dispatch(self):
        wrapper=REPO/'scripts/lab/demo_restore.sh';original=(HERE/'demo_restore.v1.sh').read_bytes()
        s=wrapper.read_text();start=s.index('# Explicit v2 staging;');end=s.index('# Explicit directory-complete recipe;')
        self.assertEqual((s[:start]+s[end:]).encode(),original)
        subprocess.run(['bash','-n',str(wrapper)],check=True)
        shim=self.root/'python3';shim.write_text('#!/bin/sh\nprintf "%s\\n" "$@" > "$ARGV_LOG"\n');shim.chmod(0o755)
        for argv,entry in [(['--seal','seal x.json'],'t5/restore.py'),(['--realization','r.json'],'r2-timeout/exact_realization.py'),(['--realization=r.json'],'r2-timeout/exact_realization.py'),(['--directory-recipe','d.json'],'r4b-directory-logdir/restore_recipe.py'),(['--v2-recipe','v.json'],'final-v2-entry/restore_entry.py'),(['--v2-recipe=v.json'],'final-v2-entry/restore_entry.py')]:
            log=self.root/'argv';env=dict(os.environ,PATH=str(self.root)+':'+os.environ['PATH'],ARGV_LOG=str(log))
            subprocess.run(['bash',str(wrapper),*argv],env=env,check=True)
            got=log.read_text().splitlines();self.assertTrue(got[0].endswith(entry));self.assertEqual(got[1:],argv)
if __name__=='__main__':unittest.main(verbosity=2)
