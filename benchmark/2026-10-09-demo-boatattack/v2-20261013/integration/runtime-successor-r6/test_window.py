import contextlib,hashlib,importlib.util,io,json,os,shutil,subprocess,sys,tempfile,time,unittest
from pathlib import Path
H=Path(__file__).resolve().parent
WS=next(p for p in H.parents if (p/'westlake-harness').is_dir());os.environ['WORKSPACES']=str(WS)
s=importlib.util.spec_from_file_location('r6_tests',H/'successor.py');m=importlib.util.module_from_spec(s);s.loader.exec_module(m)
class Tests(unittest.TestCase):
 def failed_boot(self,mode):
  import argparse
  with tempfile.TemporaryDirectory(dir=H) as td:
   d=Path(td);rt=WS/'westlake-inputs/generations/boat-v2-runtime-f28bd1b3-20261013/liboh_android_runtime.so'
   with contextlib.redirect_stdout(io.StringIO()):m.prepare(argparse.Namespace(main=str(WS/'westlake-harness'),runtime=rt,runtime_sha256=m.sha(rt),hdc='/fixture/hdc',out=d/'package'))
   p=m.read(d/'package/plan.disabled.json');p['execution_enabled']=True;pf=d/'enabled.json';pf.write_text(json.dumps(p));psha=m.sha(pf)
   tx=d/'tx';tx.mkdir();backups=[];state={r['target']:r['before'] for r in p['preserved']};meta={}
   for i,r in enumerate(p['members']):
    shutil.copyfile(m.resolve(r['before']['source']),tx/('backup-%03d'%i))
    backups.append(dict(target=r['target'],before=r['before'],backup='backup-%03d'%i,candidate_sha256=r['sha256']))
    state[r['target']]=dict(exists=True,sha256=r['sha256'],**r['after']);meta[r['target']]=r['after']
   (tx/'transaction.json').write_text(json.dumps(dict(plan_sha256=psha,serial=p['serial'],boot_id=p['boot_id'],backups=backups)))
   live={r['target']:r['before']['sha256'] for r in p['binds']}
   if mode=='partial-bind':
    for r in p['binds'][:3]:live[r['target']]=r['sha256']
   boot='11111111-2222-3333-4444-555555555555'
   fixture=d/'fixture.json';fixture.write_text(json.dumps(dict(state=state,metadata=meta,boot=boot,live=live)))
   auth=dict(approved_by='outer(codex)',plan_sha256=psha,action='rollback',serial=p['serial'],origin_boot_id=p['boot_id'],boot_id=boot,live_runtime_sha256=live[m.RT],source_restore_only=True,holder='outer(codex) 123 2026-10-13T00:00:00',expires_epoch=time.time()+300)
   af=d/'auth.json';af.write_text(json.dumps(auth))
   argv=[sys.executable,str(H/'fake_cli.py'),str(fixture),'run','--plan',str(pf),'--action','rollback','--out',str(tx),'--execute','--authorization',str(af),'--authorization-sha256',m.sha(af)]
   r=subprocess.run(argv,capture_output=True,text=True);self.assertEqual(r.returncode,0,r.stderr)
   result=m.read(fixture.with_suffix('.result.json'));self.assertEqual(result['live'],live)
   for row in p['members']:
    for k in ['sha256',*m.META]:self.assertEqual(result['state'][row['target']][k],row['before'][k])
   self.assertEqual(result['events'].count('atomic-replace'),3)
   receipt=m.read(next(tx.glob('source-rollback-*.json')));self.assertFalse(receipt['complete_runtime_rollback']);self.assertEqual(receipt['state'],'SOURCE_RESTORED_COLD_BOOT_REQUIRED')
 def test_boot_before_bind_cli(self):self.failed_boot('before-bind')
 def test_partial_bind_cli(self):self.failed_boot('partial-bind')
 def test_runner_only_two_parameter_changes(self):
  before=(WS/'westlake-harness/benchmark/2026-10-09-demo-boatattack/v2-20261013/integration/experiment-r5-stock187/interaction_runner.py').read_text()
  after=(H/'window-final4-disabled/interaction_runner.py').read_text()
  self.assertEqual(after,before.replace('5cd1e3dd00000000000000000923012c','5ea34a4500000000000000001123012c').replace('18763dd4b3a48aefaaf80c9f9630b849e282175eea8da04f7918d6d2cfa3fbae','f28bd1b3d44e2944f77911c2ad71376869f7f3ebc6dcd8434dfea869f4056db0'))
 def test_hooks_final_gate_and_readonly_no_intent(self):
  h=(H/'window_hooks.py').read_text();self.assertIn("self.verify('no-placement',self.inst.OLD,'before',worker=False)",h)
  section=h[h.index(' def before_unlock'):];self.assertLess(section.index("self.action('rollback')"),section.index("self.preboot('baseline-return')"));self.assertLess(section.index("self.verify('restored'"),section.index("self.run('restored-hw-zz'"))
if __name__=='__main__':unittest.main()
