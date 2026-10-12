import copy,hashlib,importlib.util,json,os,subprocess,sys,tempfile,time,unittest
from pathlib import Path
D=Path(__file__).resolve().parents[1]
spec=importlib.util.spec_from_file_location('executor',D/'executor.py');e=importlib.util.module_from_spec(spec);spec.loader.exec_module(e)
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()

class PlanTests(unittest.TestCase):
 def fixture(self):
  t=tempfile.TemporaryDirectory();self.addCleanup(t.cleanup);root=Path(t.name);source=root/'candidate';source.write_text('new control\n');old=root/'preimage';old.write_text('old control\n')
  driver=Path(os.environ.get('WORKSPACES',str(D.parents[2])))/'westlake-harness-wiki/scripts/lab/demo_seal_61b.py'
  before=dict(exists=True,sha256=sha(old),source=str(old),mode='550',uid=0,gid=0,label='u:object_r:data_file:s0')
  target=e.ROOT+'/entry.sh';member=dict(source=str(source),sha256=sha(source),target=target,before=before,after={k:before[k] for k in ('mode','uid','gid','label')})
  p=dict(execution_enabled=True,serial=e.SERIAL,boot_id='ac87bbbe-5f9b-496f-8002-43279e072042',scope={'61b':20,'5cd_existing_reference':128,'boat':False},hdc=str(D/'tests/record_hdc.py'),control_targets=[],members=[member],preserved=[],prerequisites=[],tools={'driver':{'path':str(driver),'sha256':sha(driver)},'hdc':{'path':str(D/'tests/record_hdc.py'),'sha256':sha(D/'tests/record_hdc.py')}})
  plan=root/'plan.json';plan.write_text(json.dumps(p));auth=root/'auth.json';a=dict(approved_by='outer(codex)',plan_sha256=sha(plan),serial=e.SERIAL,boot_id=p['boot_id'],expires_epoch=time.time()+600,actions=['place-only','one-reboot','rollback-safe']);auth.write_text(json.dumps(a))
  device=root/'device.json';device.write_text(json.dumps({'serial':e.SERIAL,'boot':p['boot_id'],'objects':{target:{**before,'hex':old.read_bytes().hex()}},'events':[]}));return root,p,plan,auth,device
 def run_cli(self,plan,auth,device,out,extra=()):
  return subprocess.run([sys.executable,str(D/'executor.py'),'--execute','--plan',str(plan),'--authorization',str(auth),'--authorization-sha256',sha(auth),'--out',str(out),*extra],env={**os.environ,'RECOVERY_TEST_DEVICE':str(device)},capture_output=True,text=True)
 def test_real_file_sha_cli_apply_then_rollback(self):
  root,p,plan,auth,device=self.fixture();out=root/'transaction';x=self.run_cli(plan,auth,device,out);self.assertEqual(x.returncode,0,x.stderr)
  tx=json.loads((out/'transaction.json').read_text());self.assertEqual(tx['plan_sha256'],sha(plan));self.assertEqual(sha(out/'backup-000'),p['members'][0]['before']['sha256'])
  events=json.loads(device.read_text())['events'];recv=next(i for i,a in enumerate(events) if a[2:4]==['file','recv']);send=next(i for i,a in enumerate(events) if a[2:4]==['file','send']);self.assertLess(recv,send)
  x=self.run_cli(plan,auth,device,out,('--action','rollback'));self.assertEqual(x.returncode,0,x.stderr);self.assertEqual(json.loads(device.read_text())['objects'][p['members'][0]['target']]['sha256'],p['members'][0]['before']['sha256'])
 def test_default_preview_no_transport(self):
  root,p,plan,auth,device=self.fixture();x=subprocess.run([sys.executable,str(D/'executor.py'),'--plan',str(plan)],capture_output=True,text=True);self.assertEqual(x.returncode,0);self.assertEqual(json.loads(x.stdout)['device_calls'],0);self.assertEqual(json.loads(device.read_text())['events'],[])

class RejectTests(unittest.TestCase):
 fixture=PlanTests.fixture
 run_cli=PlanTests.run_cli
 def test_wrong_binding_before_device_calls(self):
  for fault in ['serial','expiry','plan_sha','member_sha','missing_preimage']:
   with self.subTest(fault=fault):
    root,p,plan,auth,device=self.fixture();a=json.loads(auth.read_text())
    if fault=='serial':p['serial']='wrong'
    elif fault=='expiry':a['expires_epoch']=0
    elif fault=='plan_sha':a['plan_sha256']='0'*64
    elif fault=='member_sha':p['members'][0]['sha256']='0'*64
    else:p['members'][0]['before'].pop('source')
    plan.write_text(json.dumps(p))
    if fault!='plan_sha':a['plan_sha256']=sha(plan)
    auth.write_text(json.dumps(a));x=self.run_cli(plan,auth,device,root/'transaction');self.assertNotEqual(x.returncode,0);self.assertEqual(json.loads(device.read_text())['events'],[],x.stderr)
 def test_live_preimage_or_boot_drift_no_send(self):
  for fault in ['sha','boot']:
   root,p,plan,auth,device=self.fixture();obj=json.loads(device.read_text())
   if fault=='sha':obj['objects'][p['members'][0]['target']]['sha256']='0'*64
   else:obj['boot']='01234567-1111-2222-3333-444444444444'
   device.write_text(json.dumps(obj));x=self.run_cli(plan,auth,device,root/'transaction');self.assertNotEqual(x.returncode,0);self.assertFalse(any(a[2:4]==['file','send'] for a in json.loads(device.read_text())['events']))
 def test_corrupt_backup_rollback_no_write(self):
  root,p,plan,auth,device=self.fixture();out=root/'transaction';self.assertEqual(self.run_cli(plan,auth,device,out).returncode,0);(out/'backup-000').write_text('wrong')
  count=len(json.loads(device.read_text())['events']);x=self.run_cli(plan,auth,device,out,('--action','rollback'));self.assertNotEqual(x.returncode,0);self.assertFalse(any(a[2:4]==['file','send'] for a in json.loads(device.read_text())['events'][count:]))

class FailureTests(unittest.TestCase):
 fixture=PlanTests.fixture
 run_cli=PlanTests.run_cli
 def test_null_after_label_refuses_before_transport(self):
  root,p,plan,auth,device=self.fixture();p['members'][0]['after']['label']=None;plan.write_text(json.dumps(p));a=json.loads(auth.read_text());a['plan_sha256']=sha(plan);auth.write_text(json.dumps(a));x=self.run_cli(plan,auth,device,root/'transaction');self.assertNotEqual(x.returncode,0);self.assertEqual(json.loads(device.read_text())['events'],[])
 def test_first_mkdir_failure_no_members_changed_closes_without_stop(self):
  root,p,plan,auth,device=self.fixture();target=p['members'][0]['target'];p['members'][0]['before']={'exists':False,'proof':'verified ancestor absent'};plan.write_text(json.dumps(p));a=json.loads(auth.read_text());a['plan_sha256']=sha(plan);auth.write_text(json.dumps(a));d=json.loads(device.read_text());d['objects'].pop(target);d['mkdir_fail_once']=True;device.write_text(json.dumps(d));out=root/'transaction';self.assertNotEqual(self.run_cli(plan,auth,device,out).returncode,0);self.assertFalse(any(a[2:4]==['file','send'] for a in json.loads(device.read_text())['events']));x=self.run_cli(plan,auth,device,out,('--action','rollback'));self.assertEqual(x.returncode,0,x.stderr);self.assertEqual(json.loads((out/'rollback.json').read_text())['state'],'NO_MEMBER_CHANGES_NO_DONOR_RESTART');self.assertNotIn(e.ROOT+'/stop',json.loads(device.read_text())['objects'])
 def test_partial_send_exact_observation_restores(self):
  root,p,plan,auth,device=self.fixture();d=json.loads(device.read_text());d['partial_send_once']=True;device.write_text(json.dumps(d));out=root/'transaction'
  x=self.run_cli(plan,auth,device,out);self.assertNotEqual(x.returncode,0);self.assertTrue((out/'failed-000.json').is_file())
  f=json.loads((out/'failed-000.json').read_text());self.assertNotEqual(f['observation']['sha256'],p['members'][0]['sha256'])
  x=self.run_cli(plan,auth,device,out,('--action','rollback'));self.assertEqual(x.returncode,0,x.stderr);self.assertEqual(json.loads(device.read_text())['objects'][p['members'][0]['target']]['sha256'],p['members'][0]['before']['sha256'])
 def test_partial_changes_after_observation_reject(self):
  root,p,plan,auth,device=self.fixture();d=json.loads(device.read_text());d['partial_send_once']=True;device.write_text(json.dumps(d));out=root/'transaction';self.assertNotEqual(self.run_cli(plan,auth,device,out).returncode,0)
  d=json.loads(device.read_text());d['objects'][p['members'][0]['target']]['sha256']='1'*64;count=len(d['events']);device.write_text(json.dumps(d));x=self.run_cli(plan,auth,device,out,('--action','rollback'));self.assertNotEqual(x.returncode,0);self.assertFalse(any(a[2:4]==['file','send'] for a in json.loads(device.read_text())['events'][count:]))
 def test_all_backups_checked_before_first_restore(self):
  root,p,plan,auth,device=self.fixture();p['members'].append(copy.deepcopy(p['members'][0]));p['members'][1]['target']=e.ROOT+'/another-control.sh';d=json.loads(device.read_text());d['objects'][p['members'][1]['target']]=copy.deepcopy(d['objects'][p['members'][0]['target']]);device.write_text(json.dumps(d));plan.write_text(json.dumps(p));a=json.loads(auth.read_text());a['plan_sha256']=sha(plan);auth.write_text(json.dumps(a));out=root/'transaction';self.assertEqual(self.run_cli(plan,auth,device,out).returncode,0)
  (out/'backup-000').write_bytes(b'corrupt');count=len(json.loads(device.read_text())['events']);x=self.run_cli(plan,auth,device,out,('--action','rollback'));self.assertNotEqual(x.returncode,0);self.assertEqual(len(json.loads(device.read_text())['events']),count+1) # only boot read
 def test_rollback_idempotent_controls(self):
  root,p,plan,auth,device=self.fixture();out=root/'transaction';self.assertEqual(self.run_cli(plan,auth,device,out).returncode,0);self.assertEqual(self.run_cli(plan,auth,device,out,('--action','rollback')).returncode,0);count=len(json.loads(device.read_text())['events']);x=self.run_cli(plan,auth,device,out,('--action','rollback'));self.assertEqual(x.returncode,0,x.stderr);self.assertFalse(any(a[2:4]==['file','send'] for a in json.loads(device.read_text())['events'][count:]))

class FormatTests(unittest.TestCase):
 def test_actual_decoder_same_c_source(self):
  with tempfile.TemporaryDirectory() as tmp:
   exe=Path(tmp)/'gate';x=subprocess.run(['clang','-O2',str(D/'src/screen_gate_jpeg.c'),'-o',str(exe),'-lm'],capture_output=True,text=True);self.assertEqual(x.returncode,0,x.stderr)
   for name,expected_rc,expected in [('decoder-probe.png',0,'feed'),('decoder-probe.jpeg',0,'feed'),('corrupt.jpeg',5,''),('missing.jpeg',5,'')]:
    x=subprocess.run([str(exe),str(D/'evidence'/name)],capture_output=True,text=True);self.assertEqual(x.returncode,expected_rc);self.assertEqual(x.stdout.strip(),expected)
 def test_frozen_watchdog_and_budget(self):
  self.assertEqual(sha(D/'payload/watchdog.sh'),'9763171a0b6dab1b23b72e454cb2c6256181298bc282e81b6ae8e38fa9577072')
  s=(D/'payload/start-parent-prepared.sh').read_text();self.assertIn('"$n" -lt 10',s);self.assertIn('"$n" -lt 8',s);self.assertNotIn('"$n" -lt 40',s)
  self.assertNotIn('AUTH_CAPTURE_FORMAT_VERIFIED',(D/'payload/entry.sh').read_text())

if __name__=='__main__':unittest.main(argv=[sys.argv[0]]+(['-v'] if len(sys.argv)==1 else ['-v',*sys.argv[1:]]))
