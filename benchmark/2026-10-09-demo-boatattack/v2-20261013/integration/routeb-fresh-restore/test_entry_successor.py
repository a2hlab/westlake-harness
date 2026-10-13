import argparse,copy,json,subprocess,sys,tempfile,unittest
from pathlib import Path
import executor as e
import prepare_stage as s
import receipt_check as rc
import restore_entry as entry
import test_restore as base_tests
Fake=base_tests.Fake
p=e.p;H=Path(__file__).resolve().parent

class SuccessorTests(unittest.TestCase):
 @classmethod
 def setUpClass(cls):
  cls.temp=tempfile.TemporaryDirectory(dir=H);cls.root=Path(cls.temp.name);cls.out=cls.root/'current487';p.build(H/'request.5cd.disabled.json',cls.out);cls.recipe=cls.out/'recipe.json';cls.plan=p.read(cls.out/'plan.disabled.json')
  obj=argparse.Namespace(root=cls.root,out=cls.out,recipe=cls.recipe,plan=cls.plan)
  a,d=base_tests.RestoreTests.docs(obj);cls.txn=cls.root/'transaction'
  cls.receipt,code=e.execute(cls.recipe,p.sha(cls.recipe),a,p.sha(a),d,p.sha(d),cls.txn,'apply',device_factory=Fake,lock_runner=lambda *a,**k:subprocess.CompletedProcess(a,0,'outer(codex) 123 2026-10-13T20:00:00Z\n',''))
  assert code==0;cls.receipt_path=cls.txn/'recipe-receipt.json'
  cls.main=p.MAIN/'benchmark/2026-10-09-demo-boatattack/v2-20261013/outer/final-v2-f28-main'
  dep=p.read(cls.main/'deployment.disabled.json');cls.enabled_plan=cls.root/'boat-plan-enabled.json';plan=p.read(p.checked(dep['providers'][0]['prepared']));plan['execution_enabled']=True;cls.enabled_plan.write_text(json.dumps(plan))
  dep['execution_enabled']=True;dep['providers'][0]['prepared']=p.pin(cls.enabled_plan);cls.deployment=cls.root/'deployment-enabled.json';cls.deployment.write_text(json.dumps(dep))
 @classmethod
 def tearDownClass(cls):cls.temp.cleanup()
 def args(self,name,resume=True,enabled=False):
  dep=self.deployment if enabled else self.main/'deployment.disabled.json';seal=self.main/'composed/seal-candidate.json';hdc=Path('/Applications/DevEco-Studio.app/Contents/sdk/default/openharmony/toolchains/hdc')
  return argparse.Namespace(directory_recipe=self.recipe,directory_recipe_sha256=p.sha(self.recipe),deployment=dep,deployment_sha256=p.sha(dep),seal=seal,seal_sha256=p.sha(seal),hdc=hdc,hdc_sha256=p.sha(hdc),completed_receipt=self.receipt_path if resume else None,completed_receipt_sha256=p.sha(self.receipt_path) if resume else None,out=self.root/name)
 def invoke(self,file,out,execute=False):return argparse.Namespace(v2_recipe=file,recipe_sha256=p.sha(file),out=self.root/out,execute=execute)
 def test_current_receipt_and_actual_cli_preview(self):
  args=self.args('resume');file=s.build(args)
  result=subprocess.run([sys.executable,str(H/'restore_entry.py'),'--v2-recipe',str(file),'--recipe-sha256',p.sha(file),'--out',str(self.root/'cli-out')],capture_output=True,text=True)
  self.assertEqual(result.returncode,0,result.stderr);v=json.loads(result.stdout);self.assertEqual([x['name'] for x in v['steps']],['route-b-selfcheck','boat-placement']);self.assertEqual(v['device_calls'],0);self.assertFalse((self.root/'cli-out').exists())
  self.assertFalse(rc.admit(self.recipe,p.sha(self.recipe),self.receipt_path,p.sha(self.receipt_path))['execution_authority'])
 def test_full_chain_order_and_fresh_recipe_dispatch(self):
  file=s.build(self.args('whole',False));data,plan,path,steps=entry.prepare(self.invoke(file,'whole-out'))
  self.assertEqual([n for n,_ in steps],['route-b-complete','route-b-selfcheck','boat-placement'])
  self.assertIn('--recipe',steps[0][1]);self.assertNotIn('--directory-recipe',steps[0][1]);self.assertEqual(steps[0][1][1],str(H/'executor.py'))
  self.assertEqual(steps[-1][1][2:4],['--seal',str(self.main/'composed/seal-candidate.json')])
 def test_missing_record_and_changed_origin_refuse(self):
  f=self.txn/'placed-000.json';orig=f.read_bytes();f.unlink()
  try:
   with self.assertRaisesRegex(ValueError,'exact487'):rc.admit(self.recipe,p.sha(self.recipe),self.receipt_path,p.sha(self.receipt_path))
  finally:f.write_bytes(orig)
  v=p.read(self.receipt_path);v['boot_id']='43bc0000-0000-0000-0000-000000000000';bad=self.root/'bad-receipt.json';bad.write_text(json.dumps(v))
  with self.assertRaisesRegex(ValueError,'scope boot_id'):rc.admit(self.recipe,p.sha(self.recipe),bad,p.sha(bad))
 def test_real_entry_stop_then_checked_order(self):
  file=s.build(self.args('dispatch',enabled=True));data=p.read(file);data['execution_enabled']=True;file.write_text(json.dumps(data));calls=[]
  def fail(argv,**kw):calls.append(argv);return subprocess.CompletedProcess(argv,2,'','recording refusal')
  self.assertEqual(entry.run(self.invoke(file,'fail-out',True),runner=fail),2);self.assertEqual(len(calls),1)
  calls.clear();runout=self.root/'ok-out';q=p.read(self.main/'request.json')
  def runner(argv,**kw):
   calls.append(argv)
   if '--checker' in argv:
    (runout/'route-b-selfcheck.json').write_bytes(p.checked(q['base']['selfcheck']).read_bytes())
   else:
    (runout/'boat').mkdir();(runout/'boat/receipt.json').write_text(json.dumps(dict(executor_rc=0,status='PLACED_PENDING_AUTHORIZED_SINGLE_BOOT',restored=False,reboots=0,serial=entry.SERIAL,plan_sha256=p.sha(self.enabled_plan))))
   return subprocess.CompletedProcess(argv,0,'recording transport only','')
  self.assertEqual(entry.run(self.invoke(file,'ok-out',True),runner=runner),0);self.assertEqual(len(calls),2)
  self.assertEqual(p.read(runout/'staged-receipt.json')['status'],'PLACED_PENDING_AUTHORIZED_SINGLE_BOOT_AND_FINAL_SELFCHECK')

if __name__=='__main__':unittest.main(verbosity=2)
