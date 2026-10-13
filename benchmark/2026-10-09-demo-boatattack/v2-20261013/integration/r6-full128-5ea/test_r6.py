"""File-only actual5ea R6 preview and unchanged failure paths; no deployment."""
import ast,copy,json,os,subprocess,sys,tempfile,unittest
from pathlib import Path
from unittest.mock import patch
HERE=Path(__file__).resolve().parent;os.environ.setdefault('WORKSPACES',str(HERE.parents[5]));sys.path.insert(0,str(HERE))
import candidate_identity as c
import run_candidate_post_reboot as d
OLD=c.WS/'westlake-harness-bms/benchmark/2026-10-09-demo-boatattack/v2-20261013/integration/identity-r4'
class Tests(unittest.TestCase):
 @classmethod
 def setUpClass(cls):
  (HERE/'tmp').mkdir(exist_ok=True);(HERE/'evidence').mkdir(exist_ok=True);cls.temp=tempfile.TemporaryDirectory(dir=HERE/'tmp');cls.root=Path(cls.temp.name);cls.preview=cls.root/'preview';cls.smoke10=cls.root/'smoke10'
  command=[sys.executable,str(HERE/'no_device_cli.py'),str(HERE/'prepare.py'),'--request',str(HERE/'request.disabled.json'),'--out',str(cls.preview)]
  prepared=subprocess.run(command,capture_output=True,text=True);(HERE/'evidence/landed-prepare.stdout.txt').write_text(prepared.stdout);(HERE/'evidence/landed-prepare.stderr.txt').write_text(prepared.stderr)
  if prepared.returncode or 'OFFLINE_TRANSPORT_ATTEMPTS=0' not in prepared.stderr:raise AssertionError('landed prepare failed: '+prepared.stdout+prepared.stderr)
  cls.proof=c.read(cls.preview/'identity/candidate-proof.json');cls.round=c.read(cls.preview/'round/round.json');cls.original=c.read(c.pinned(cls.proof['original_r4_proof']))
  command=[sys.executable,str(HERE/'no_device_cli.py'),str(HERE/'prepare_smoke10.py'),'--out',str(cls.smoke10),'--candidate-proof',str(cls.preview/'identity/candidate-proof.json'),'--candidate-proof-sha256',c.sha(cls.preview/'identity/candidate-proof.json'),'--boot-before',cls.round['boot_before_reboot'],'--install-index',str(c.pinned(cls.round['bindings']['install_index']))]
  prepared=subprocess.run(command,capture_output=True,text=True);(HERE/'evidence/landed-smoke10.stdout.txt').write_text(prepared.stdout);(HERE/'evidence/landed-smoke10.stderr.txt').write_text(prepared.stderr)
  if prepared.returncode or 'OFFLINE_TRANSPORT_ATTEMPTS=0' not in prepared.stderr:raise AssertionError('landed smoke10 prepare failed: '+prepared.stdout+prepared.stderr)

 @classmethod
 def tearDownClass(cls):cls.temp.cleanup()
 def test_original_driver_and_failure_functions_ast(self):
  src=c.pinned(self.round['bindings']['driver']);old=c.MAIN/'benchmark/2026-10-09-demo-boatattack/v2-20261013/integration/fresh128-handoff-r2/run_candidate_post_reboot.py'
  def nodes(p):return [n for n in ast.parse(p.read_text()).body if not isinstance(n,ast.Assign) or not any(isinstance(t,ast.Name) and t.id=='LOCAL' for t in n.targets)]
  self.assertEqual([ast.dump(n) for n in nodes(src)],[ast.dump(n) for n in nodes(old)])
  before={n.name:ast.dump(n) for n in ast.parse((OLD/'candidate_identity.py').read_text()).body if isinstance(n,ast.FunctionDef)};after={n.name:ast.dump(n) for n in ast.parse((HERE/'candidate_identity.py').read_text()).body if isinstance(n,ast.FunctionDef)}
  for name in ['check','main','load_proof','parse_hashes','parts','fp','valid_rows']:self.assertEqual(before[name],after[name],name)
  self.assertEqual((OLD/'absence_reader.py').read_bytes(),(HERE/'absence_reader.py').read_bytes())
 def test_actual_driver_cli_preserves_128_and_eight_windows(self):
  proof=self.preview/'identity/candidate-proof.json';refs=self.round['bindings'];out=self.root/'driver-cli'
  args=[sys.executable,str(HERE/'no_device_cli.py'),str(HERE/'run_candidate_post_reboot.py'),'--out',str(out),'--serial',c.SPARE,'--manifest',str(c.pinned(refs['manifest'])),'--tiers',str(c.pinned(refs['tiers'])),'--install-index',str(c.pinned(refs['install_index'])),'--smoke',str(self.preview/'identity/smoke.json'),'--boot-before',self.round['boot_before_reboot'],'--candidate-proof',str(proof),'--candidate-proof-sha256',c.sha(proof)]
  got=subprocess.run(args,capture_output=True,text=True);(HERE/'evidence/driver.stdout.txt').write_text(got.stdout);(HERE/'evidence/driver.stderr.txt').write_text(got.stderr);self.assertEqual(got.returncode,0,got.stdout+got.stderr);self.assertIn('OFFLINE_TRANSPORT_ATTEMPTS=0',got.stderr)
  cfg=c.read(out/'round.json');self.assertFalse(cfg['execution_enabled']);self.assertEqual((cfg['serial'],cfg['apps'],len(cfg['windows'])),(c.SPARE,128,8))
  apps=c.read(out/'batch-apps.json')['apps'];original=[a for a in c.read(c.pinned(refs['manifest']))['apps'] if a.get('install') is not False];self.assertEqual([r['key'] for r in apps],[r['key'] for r in original]);self.assertEqual(next(r['apk_sha256'] for r in apps if r['key']=='fd-noice'),'8e11b3136977e9f5dc897de85c26add9a219ea61884feabcbcd4e33566d5d2ca')
  tiers=c.read(out/'shot-tiers.json')['apps'];self.assertEqual((sum(r['screenshot_seconds']==10 for r in tiers),sum(r['screenshot_seconds']==20 for r in tiers)),(121,7))
  for ref in cfg['windows']:
   p=c.read(d.expand(ref));self.assertFalse(p['execution_enabled']);self.assertEqual(p['after_lock'][:4],['orb','-m','a2hlab','env']);self.assertEqual(p['before_unlock'][:4],['orb','-m','a2hlab','env'])
 def test_exact_four_delta_and_original_smoke(self):
  c.validate(self.proof);self.assertEqual(set(self.proof['expected']),set(self.original['expected']));delta={t for t,h in self.proof['expected'].items() if h!=self.original['expected'][t]};self.assertEqual(delta,{c.RUNTIME,c.OWN+'/sources/liboh_android_runtime.so',c.OWN+'/worker.sh',c.OWN+'/binds.tsv'});self.assertEqual(self.proof['absent_files'],self.original['absent_files'])
  old=c.read(c.pinned(self.original['smoke']));new=c.read(self.preview/'identity/smoke.json');self.assertEqual({k:v for k,v in old.items() if k not in ['expect','probe']},{k:v for k,v in new.items() if k not in ['expect','probe']})
 def test_any_missing_or_foreign_or_extended_delta_rejects(self):
  for fault in ['319','extra','absence','serial','generation','successor','runtime','protected','enabled']:
   p=copy.deepcopy(self.proof)
   if fault=='319':p['expected'].pop(next(iter(c.read(c.BASE)['expected'])))
   elif fault=='extra':p['additional_files'].pop()
   elif fault=='absence':p['absent_files']=[]
   elif fault=='serial':p['serial']='5cd1e3dd00000000000000000923012c'
   elif fault=='generation':p['generation_sha256']='a'*64
   elif fault=='successor':p['successor_program']['sha256']='a'*64
   elif fault=='runtime':p['expected'][c.RUNTIME]=self.original['expected'][c.RUNTIME]
   elif fault=='protected':p['protected_files']['sha256']='a'*64
   elif fault=='enabled':p['execution_enabled']=True
   with self.subTest(fault=fault),self.assertRaises((ValueError,KeyError)):c.validate(p)
 def record(self,fault=None):
  expected=self.proof['expected'];runtime,boot=c.parts({t:expected[t] for t in c.read(c.BASE)['expected']});calls=[];old=self.round['boot_before_reboot'];new='22222222-2222-2222-2222-222222222222'
  class Reader:
   def absent(self,path):calls.append('absent '+path);return fault!='absence'
   def shell(self,cmd):
    calls.append(cmd)
    if fault=='rc':return 1,''
    if cmd.startswith('cat '):return 0,old if fault=='oldboot' else ('33333333-3333-3333-3333-333333333333' if fault=='boot' and sum(x.startswith('cat ') for x in calls)==2 else new)
    if cmd.startswith('sha256sum '):
     rows=runtime if '*.so' in cmd else boot if '/arm64/*' in cmd else {t:expected[t] for t in cmd.split()[1:]};rows=dict(rows)
     if fault=='broad' and '*.so' in cmd:rows.pop(next(iter(rows)))
     lines=[h+'  '+t for t,h in rows.items()]
     if fault=='missing' and len(rows)==24:lines.pop()
     if fault=='sha' and len(rows)==24:lines[0]='a'*64+lines[0][64:]
     return 0,'\n'.join(lines)
    if cmd.startswith('ps '):return 0,'PID PPID UID NAME\n10 1 0 appspawn-x\n'+('11 1 0 appspawn-x\n' if fault=='parent' else '')
    if cmd.startswith('readlink '):return 0,'/system/bin/appspawn-x'
    if cmd.startswith('df '):return 0,'/data 100000 1 99999'
    if cmd.startswith('param '):return 0,'wrong' if fault=='version' else 'OpenHarmony-6.1.0.31'
    raise AssertionError(cmd)
  out=self.root/('record-'+str(fault));out.mkdir()
  with patch.object(c,'validate',return_value=expected),patch('subprocess.run',side_effect=AssertionError('NO DEVICE')):result=c.check(Reader(),self.proof,out,old)
  return result,calls
 def test_original_runtime_read_failure_gates(self):
  result,calls=self.record();self.assertTrue(result['passed']);(HERE/'evidence/recording.json').write_text(json.dumps({'status':'OFFLINE_RECORDING_NOT_DEVICE_PASS','synthetic':True,'device_calls':0,'call_equivalents':len(calls),'sha_targets':len(self.proof['expected']),'calls':calls},indent=2)+'\n')
  for fault in ['rc','oldboot','missing','broad','absence']:
   with self.subTest(fault=fault),self.assertRaises(ValueError):self.record(fault)
  for fault in ['sha','boot','parent','version']:
   with self.subTest(fault=fault):self.assertFalse(self.record(fault)[0]['passed'])
 def test_smoke10_original_preparer_only_first_plan_t20(self):
  out=self.smoke10;receipt=c.read(out/'smoke10-preparation.json');plan=c.read(c.expand(receipt['first_plan']));controls=c.read(HERE/'smoke10-controls-t20.json')['apps'];actual=[key for row in plan['shards'] for key in c.expand(row['keys_file']).read_text().split()]
  self.assertEqual(actual,[r['key'] for r in controls]);self.assertEqual(len(actual),10);self.assertFalse(plan['execution_enabled']);tiers={r['key']:r for r in c.read(out/'shot-tiers.json')['apps']};self.assertTrue(all(tiers[k]['screenshot_seconds']==20 for k in actual));self.assertEqual(len(c.read(out/'round.json')['windows']),13)
 def test_prepare_cli_cannot_enable(self):
  out=self.root/'must-not-create';r=subprocess.run([sys.executable,str(HERE/'no_device_cli.py'),str(HERE/'prepare.py'),'--request',str(HERE/'request.disabled.json'),'--out',str(out),'--execute'],capture_output=True,text=True);self.assertNotEqual(r.returncode,0);self.assertFalse(out.exists());self.assertIn('OFFLINE_TRANSPORT_ATTEMPTS=0',r.stderr)
if __name__=='__main__':unittest.main(verbosity=2)
