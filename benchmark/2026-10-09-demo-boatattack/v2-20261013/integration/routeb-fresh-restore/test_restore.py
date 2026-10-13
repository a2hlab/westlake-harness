import collections,contextlib,copy,hashlib,io,json,os,re,shlex,shutil,subprocess,sys,tempfile,time,unittest
from pathlib import Path
from unittest.mock import patch
import prepare as p
import executor as e
H=Path(__file__).resolve().parent
class Fake:
 def __init__(self,plan,out,fail=False):
  self.plan=plan;self.out=out;self.calls=[];self.fail=fail;self.core=p.load(p.OLD/'executor.py','fake_core_helpers')
  self.rows={r['target']:copy.deepcopy(r['before']) for r in plan['members']+plan['preserved']}
  self.sources={r['target']:p.resolve(r['before']['source']) for r in plan['members']}
  for r in plan['prerequisites']:self.rows.setdefault(r['target'],dict(exists=True,sha256=r['sha256']))
 def probe(self,target):self.calls.append(('probe',target));return copy.deepcopy(self.rows.get(target,dict(exists=False)))
 def recv(self,name,target,dest):self.calls.append(('recv',target));shutil.copyfile(self.sources[target],dest)
 def send(self,name,source,target):
  self.calls.append(('send',target));sha=p.sha(source)
  self.rows[target]=dict(exists=True,sha256=sha,mode='600',uid=0,gid=0,label='u:object_r:data_file:s0')
  if self.fail:
   self.fail=False;self.rows[target]['sha256']='f'*64;raise ValueError('recording interrupted send')
 def shell(self,name,script):
  self.calls.append((name,script))
  if name=='boot':return self.plan['_active_boot']
  if name in ('exact-existing-directory','existing-host-directory'):
   target=next(t for t in sorted(self.plan['fresh_rebase']['all_directories'],key=len,reverse=True) if shlex.quote(t) in script)
   d=self.plan['fresh_rebase']['all_directories'][target]
   if name=='exact-existing-directory':return ':'.join(str(d[k]) for k in ('mode','uid','gid','label','identity'))
   return ':'.join(str(d[k]) for k in ('mode','uid','gid'))+'\n'+d['label']
  if name=='atomic-stage-metadata':
   target=shlex.split(script)[-1];row=next(r for r in self.plan['members'] if e.stage_path(self.plan,r['target'])==target);self.rows[target].update(row['after']);return ''
  if name=='atomic-cas-rename':
   tokens=shlex.split(script);target=tokens[tokens.index('mv')+2].rstrip(';');row=next(r for r in self.plan['members'] if r['target']==target);stage=e.stage_path(self.plan,target);self.rows[stage].update(row['after'])
   assert self.core.equal(self.rows[target],row['before']);assert self.core.equal(self.rows[stage],dict(exists=True,sha256=row['sha256'],**row['after']))
   self.rows[target]=copy.deepcopy(self.rows[stage])
   if target!=self.core.CFG:del self.rows[stage]
   return ''
  raise AssertionError('unhandled real command '+name)

class RestoreTests(unittest.TestCase):
 @classmethod
 def setUpClass(cls):
  cls.temp=tempfile.TemporaryDirectory(dir=H);cls.root=Path(cls.temp.name);cls.out=cls.root/'compiled';p.build(H/'request.5cd.disabled.json',cls.out);cls.recipe=cls.out/'recipe.json';cls.plan=p.read(cls.out/'plan.disabled.json')
 @classmethod
 def tearDownClass(cls):cls.temp.cleanup()
 def setUp(self):self.tmp=tempfile.TemporaryDirectory(dir=H);self.root=Path(self.tmp.name)
 def tearDown(self):self.tmp.cleanup()
 def docs(self,action='apply'):
  lock=p.MAIN/'scripts/lab/board_note.sh'
  auth=dict(approved_by='outer(codex)',recipe_sha256=p.sha(self.recipe),plan_sha256=p.sha(self.out/'plan.disabled.json'),executor_sha256=p.sha(H/'executor.py'),serial=self.plan['serial'],boot_id=self.plan['boot_id'],action=action,holder='outer(codex) 123 2026-10-13T20:00:00Z',expires_epoch=time.time()+2600,apply_deadline_epoch=time.time()+1900,lock_tool=p.pin(lock),actions=['place-only','one-reboot','rollback-safe'])
  a=self.root/(action+'-authorization.json');a.write_text(json.dumps(auth));ad=dict(auth,signed_by='outer(claude)',admitted=True,authorization_sha256=p.sha(a),target_sha256={r['target']:r['sha256'] for r in self.plan['members']});d=self.root/(action+'-admission.json');d.write_text(json.dumps(ad));return a,d
 def held(self,*args,**kwargs):return subprocess.CompletedProcess(args[0],0,'outer(codex) 123 2026-10-13T20:00:00Z\n','')
 def test_compile_actual_and_cli_preview(self):
  self.assertEqual(len(self.plan['members']),487);self.assertEqual(len(self.plan['directory_prerequisites']),29);self.assertFalse(self.plan['directories']);self.assertFalse(self.plan['execution_enabled']);self.assertTrue(all(r['before']['sha256']==r['sha256'] for r in self.plan['members']))
  command=[sys.executable,str(H/'executor.py'),'--recipe',str(self.recipe),'--recipe-sha256',p.sha(self.recipe),'--out',str(self.root/'unused')]
  result=subprocess.run(command,capture_output=True,text=True);self.assertEqual(result.returncode,0,result.stderr);self.assertEqual(json.loads(result.stdout)['device_calls'],0);self.assertFalse((self.root/'unused').exists())
 def test_foreign_before_zero_send_and_inode_guard(self):
  core=p.load(p.OLD/'executor.py','test_original');plan=copy.deepcopy(self.plan);plan['_sha']=p.sha(self.out/'plan.disabled.json');plan['_active_boot']=plan['boot_id'];dev=Fake(plan,self.root);row=plan['members'][0];dev.rows[row['target']]['sha256']='e'*64
  with self.assertRaisesRegex(ValueError,'preimage'):e.atomic_place(core,dev,row,row['before'],plan,self.root)
  self.assertFalse(any(n=='send' for n,_ in dev.calls))
  dev=Fake(plan,self.root);orig=dev.shell
  def bad(name,script):
   v=orig(name,script);return v+':99' if name=='exact-existing-directory' else v
  dev.shell=bad
  with self.assertRaisesRegex(ValueError,'inode'):e.directory_check(core,dev,plan)
 def test_real_shell_protocol_rejects_host_rc_only(self):
  core=p.load(p.OLD/'executor.py','protocol_original');dev=object.__new__(core.Device);dev.hdc='fake-hdc';dev.serial=self.plan['serial'];calls=[]
  def run(name,argv):calls.append(argv);return 'apparently successful\n'
  dev.command=run
  with self.assertRaisesRegex(ValueError,'remote status'):dev.shell('read','true')
  self.assertIn('RE_REMOTE_RC',calls[0][-1]);self.assertNotIn('awk',calls[0][-1])
 def test_authorization_scope_and_rollback_reserve(self):
  a,d=self.docs();recipe=p.read(self.recipe);recipe['_sha']=p.sha(self.recipe);plan=dict(self.plan,_sha=p.sha(self.out/'plan.disabled.json'))
  e.guard(recipe,plan,a,p.sha(a),d,p.sha(d),'apply')
  auth=p.read(a);ad=p.read(d);auth['apply_deadline_epoch']=auth['expires_epoch'];a.write_text(json.dumps(auth));ad.update(authorization_sha256=p.sha(a),apply_deadline_epoch=auth['apply_deadline_epoch']);d.write_text(json.dumps(ad))
  with self.assertRaisesRegex(ValueError,'reserve'):e.guard(recipe,plan,a,p.sha(a),d,p.sha(d),'apply')
  auth['boot_id']='43bc3915-04bd-42ca-895e-26e8292911fa';a.write_text(json.dumps(auth));ad['authorization_sha256']=p.sha(a);d.write_text(json.dumps(ad))
  with self.assertRaisesRegex(ValueError,'boot_id'):e.guard(recipe,plan,a,p.sha(a),d,p.sha(d),'apply')
 def run_transaction(self,fail=False):
  a,d=self.docs();out=self.root/'transaction';devices=[];orig=p.load
  def load(path,name):
   core=orig(path,name)
   if name=='routeb_original487_executor':
    def factory(plan,root):
     obj=Fake(plan,root,fail);devices.append(obj);return obj
    core.Device=factory
   return core
  argv=['executor','--recipe',str(self.recipe),'--recipe-sha256',p.sha(self.recipe),'--authorization',str(a),'--authorization-sha256',p.sha(a),'--admission',str(d),'--admission-sha256',p.sha(d),'--out',str(out),'--execute']
  with patch.object(p,'load',side_effect=load),patch.object(e.subprocess,'run',side_effect=self.held),patch.object(sys,'argv',argv),contextlib.redirect_stdout(io.StringIO()):
   # execute's default lock_runner is captured; replace held itself, not live transport.
   with patch.object(e,'held',side_effect=lambda auth,runner=None:None):rc=e.main()
  return out,devices[0],rc
 def test_full487_real_cli_recording_and_missing_receipt(self):
  out,dev,rc=self.run_transaction();self.assertEqual(rc,0)
  result=p.read(out/'recipe-receipt.json');self.assertEqual((result['complete'],result['placed_count'],result['reboots']),(True,487,0));self.assertEqual(len(result['member_receipts']),487)
  sends=[v for n,v in dev.calls if n=='send'];self.assertEqual(len(sends),487);self.assertFalse(set(sends)&{r['target'] for r in self.plan['members']})
  if os.environ.get('ROUTEB_RECORD_CALLS'):
   record=Path(os.environ['ROUTEB_RECORD_CALLS']);record.write_text(json.dumps(dict(schema='actual-cli-recording/v1',synthetic=True,device_calls=0,hdc_operations_if_executed=len(dev.calls),counts=dict(collections.Counter(n for n,_ in dev.calls)),calls=dev.calls),indent=2)+'\n')
  scripts=[v for n,v in dev.calls if n=='atomic-cas-rename'];self.assertEqual(len(scripts),487)
  for script in scripts:self.assertIn('sha256sum',script);self.assertIn('stat -c',script);self.assertIn('mv ',script);self.assertNotIn('awk',script);subprocess.run(['bash','-n'],input=script,text=True,check=True)
  core=p.load(p.OLD/'executor.py','receipt_core');plan=dict(self.plan,_sha=p.sha(self.out/'plan.disabled.json'));(out/'placed-486.json').unlink()
  with self.assertRaises((ValueError,FileNotFoundError)):e.member_receipts(core,plan,out)
 def test_partial_stage_rollback_and_unknown_audit_reject(self):
  out,dev,rc=self.run_transaction(fail=True);self.assertEqual(rc,2);self.assertTrue((out/'failed-000.json').is_file());self.assertTrue((out/'atomic-failed-000.json').is_file())
  self.assertFalse(any(n=='atomic-cas-rename' for n,_ in dev.calls));a,d=self.docs('rollback')
  prior=len(dev.calls)
  with patch.object(e,'held',side_effect=lambda auth,runner=None:None):result,rc=e.execute(self.recipe,p.sha(self.recipe),a,p.sha(a),d,p.sha(d),out,'rollback',device_factory=lambda plan,root:dev)
  if os.environ.get('ROUTEB_RECORD_CALLS'):
   Path(os.environ['ROUTEB_RECORD_CALLS']).with_name('rollback-recording.json').write_text(json.dumps(dict(synthetic=True,device_calls=0,hdc_operations_if_executed=len(dev.calls)-prior,counts=dict(collections.Counter(n for n,_ in dev.calls[prior:])),calls=dev.calls[prior:]),indent=2)+'\n')
  self.assertEqual(rc,0);self.assertTrue(result['complete']);self.assertEqual(len(result['retained_audit']),1);self.assertFalse(any(n=='atomic-cas-rename' for n,_ in dev.calls))
  target=result['retained_audit'][0]['target'];dev.rows[target]['sha256']='a'*64
  with patch.object(e,'held',side_effect=lambda auth,runner=None:None):result,rc=e.execute(self.recipe,p.sha(self.recipe),a,p.sha(a),d,p.sha(d),out,'rollback',device_factory=lambda plan,root:dev)
  self.assertEqual(rc,2);self.assertIn('foreign stage',result['error'])
if __name__=='__main__':unittest.main(verbosity=2)
