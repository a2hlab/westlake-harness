"""Narrow offline r4 delta checks against root's captured inputs; never uses Device."""
import copy,importlib.util,json,os,shutil,subprocess,tempfile,unittest
from pathlib import Path
import prepare as p
import installer as i

class R4(unittest.TestCase):
 @classmethod
 def setUpClass(cls):
  cls.tmp=tempfile.TemporaryDirectory();cls.out=Path(cls.tmp.name);window=p.MAIN/'benchmark/2026-10-09-demo-boatattack/v2-20261013/outer/candidate-window1'
  path=p.HERE/'captured.json';cls.captured=i.read(path);cls.plan=p.build(path,cls.out/'package');cls.plan['_sha']=i.sha(cls.out/'package/plan.disabled.json');cls.core=i.core_for(cls.plan);cls.core.HERE=cls.out/'package'
 @classmethod
 def tearDownClass(cls):cls.tmp.cleanup()
 def test_eleven_members_seven_binds_libandroid_last(self):
  self.assertEqual(len(self.plan['members']),11);self.assertEqual(len(self.plan['binds']),7);self.assertEqual(self.plan['binds'][-1]['target'],p.LIBANDROID)
  self.assertEqual(self.plan['binds'][-1]['before']['mode'],self.captured['libandroid_before']['mode']);self.assertEqual(self.plan['binds'][-1]['sha256'],p.ADC)
  original=i.read(p.MAIN/'benchmark/2026-10-09-demo-boatattack/v2-20261013/outer/candidate-window2/plan.json')
  for old,new in zip(original['binds'],self.plan['binds']):self.assertEqual({**old,'source':old['source'].replace('/data/westlake-demo/u13/boat-v2-20261013-r3',i.ROOT)},new)
  self.assertTrue(self.plan['members'][6]['source'].startswith('$WORKSPACES/../00.Workspace-games-ad1ab0a7/'));self.assertNotIn('/Users/',json.dumps(self.plan));self.assertNotIn('/home/',json.dumps(self.plan))
  self.assertEqual(self.plan['members'][-1]['target'],i.CFG);self.assertFalse(self.plan['execution_enabled'])
 def test_real_cli_preview_and_shell(self):
  env=dict(os.environ,WORKSPACES=str(p.WS));root=self.out/'package'
  r=subprocess.run(['python3',str(root/'installer.py'),'--plan',str(root/'plan.disabled.json')],env=env,capture_output=True,text=True);self.assertEqual(r.returncode,0,r.stderr);self.assertEqual(json.loads(r.stdout)['device_calls'],0)
  for name in ['worker.sh','recover-v3-boat.sh']:self.assertEqual(subprocess.run(['bash','-n',str(root/name)]).returncode,0)
 def test_r2_guards_and_caps_preserved(self):
  cfg=json.loads((p.HERE/'recover.cfg').read_text());self.assertTrue(all(s['caps'][-1]=='SYS_PTRACE' for s in cfg['services']))
  w=(self.out/'package/worker.sh').read_text();self.assertIn('fail INIT_MOUNT_NS_READ',w);self.assertIn('fail NOT_INIT_MOUNT_NS',w);self.assertIn('fail U13_PARENT_ALREADY_RUNNING',w);self.assertIn('        no_parent;;',w);self.assertIn('    no_parent\n    mount -o bind',w);self.assertIn('|| fail \"BIND_$n\"\n    no_parent',w);self.assertIn('done < \"$TABLE\"\nno_parent\nprintf',w)
  self.assertLess(w.index('# All inputs'),w.index('mount -o bind'));self.assertIn("'layers=7'",w)
 def test_phase_specific_runtime_guards(self):
  w=(self.out/'package/worker.sh').read_text();stock=next(x.strip() for x in w.splitlines() if 'fail STOCK_RUNTIME' in x);candidate=next(x.strip() for x in w.splitlines() if 'fail CANDIDATE_RUNTIME' in x)
  android_stock=next(x.strip() for x in w.splitlines() if 'fail STOCK_LIBANDROID' in x);android_candidate=next(x.strip() for x in w.splitlines() if 'fail CANDIDATE_LIBANDROID' in x)
  for guard,wanted in [(stock,p.STOCK),(candidate,p.PORT),(android_stock,p.ANDROID_BASE),(android_candidate,p.ADC)]:
   for actual in [p.STOCK,p.PORT,p.ANDROID_BASE,p.ADC]:
    script='sha(){ echo "$ACTUAL"; }; fail(){ exit 7; }; '+guard
    rc=subprocess.run(['bash','-c',script],env=dict(os.environ,ACTUAL=actual)).returncode;self.assertEqual(rc,0 if actual==wanted else 7)
 def recording(self,fail=False):
  plan=self.plan;core=self.core
  class Fake:
   def __init__(self):
    self.states={r['target']:copy.deepcopy(r['before']) for r in plan['members']+plan['preserved']}
    for r in plan['prerequisites']:self.states[r['target']]={'exists':True,'sha256':r['sha256'],**self.states.get(r['target'],{})}
    self.created=0;self.last=None;self.calls=[]
   def probe(self,target):return copy.deepcopy(self.states.get(target,{'exists':False}))
   def recv(self,name,target,dest):shutil.copyfile(i.resolve(plan['members'][-1]['before']['source']),dest)
   def send(self,name,source,target):
    self.last=target;self.states[target]={'exists':True,'sha256':i.sha(source)}
    if fail and target==i.ROOT+'/sources/'+('libandroid.so' if fail=='android' else 'liboh_android_runtime.so'):
     self.states[target]={'exists':True,'sha256':'f'*64,'mode':'600','uid':0,'gid':0,'label':'u:object_r:data_file:s0'};raise OSError('controlled runtime partial')
   def shell(self,name,cmd):
    self.calls.append(name)
    if name=='boot':return plan['boot_id']
    if name=='directory-create':self.created+=1
    if name=='directory-readback':
     m=plan['directories'][self.created-1]['after'];return ':'.join(str(m[k]) for k in ['mode','uid','gid'])+'\n'+m['label']+'\n1:'+str(self.created)
    if name=='control-metadata':self.states[self.last].update(next(r['after'] for r in plan['members'] if r['target']==self.last))
    if name=='cfg-atomic-remount':r=plan['members'][-1];self.states[i.CFG]={'exists':True,'sha256':r['sha256'],**r['after']}
    return ''
  with tempfile.TemporaryDirectory() as tmp:
   out=Path(tmp);dev=Fake()
   if fail:
    with self.assertRaisesRegex(ValueError,'placement failed'):core.apply(plan,dev,out)
    self.assertTrue((out/('failed-006.json' if fail=='android' else 'failed-005.json')).exists());tx,current=i.rollback_preflight(plan,dev,out,core);self.assertEqual(len(tx['backups']),11);self.assertEqual(current[i.ROOT+'/sources/'+('libandroid.so' if fail=='android' else 'liboh_android_runtime.so')]['sha256'],'f'*64)
   else:
    core.apply(plan,dev,out);self.assertEqual(len(list(out.glob('placed-*.json'))),11);self.assertEqual(dev.calls[-1],'cfg-atomic-remount')
   self.assertEqual(i.sha(out/'backup-010'),plan['members'][-1]['before']['sha256'])
   for r in plan['binds']:self.assertTrue(core.equal(dev.probe(r['target']),r['before']))
 def test_existing_executor_eleven_placements(self):self.recording()
 def test_runtime_partial_uses_exact_existing_rollback_rule(self):self.recording(True)
 def test_libandroid_partial_uses_exact_existing_rollback_rule(self):self.recording('android')
 def test_bad_libandroid_preimage_refused(self):
  with tempfile.TemporaryDirectory() as tmp:
   path=Path(tmp)/'captured.json';d=copy.deepcopy(self.captured);d['libandroid_before']['sha256']=p.ADC;path.write_text(json.dumps(d))
   with self.assertRaisesRegex(ValueError,'libandroid9cc actual preimage'):p.build(path,Path(tmp)/'package')
if __name__=='__main__':unittest.main()
