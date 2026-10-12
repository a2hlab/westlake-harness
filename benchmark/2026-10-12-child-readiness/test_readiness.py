#!/usr/bin/env python3
"""Actual POSIX candidate functions with captured-field fixtures, zero hardware."""
from pathlib import Path
import hashlib,json,os,subprocess,tempfile,threading,time,unittest
D=Path(__file__).resolve().parent;C=D/'candidate';OLD=D.parent/'2026-10-12-recovery-exe-alias/candidate'
S='a7a358c60bec293c26531b0eecbf14979f77411c227cec4767742c0c82791a0c'
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def statline(pid,ppid,birth,state='S'):return f'{pid} (fixture) {state} {ppid} '+' '.join(['0']*17)+f' {birth} 0\n'
def run_case(model,strict=False):
 with tempfile.TemporaryDirectory() as t:
  r=Path(t);f=r/'state';f.mkdir();proc=r/'proc';rt=r/'runtime';rt.mkdir()
  for pid,birth,ppid,uid in [(9544,63926,4421,model.get('uid','20011206')),(4421,500,1,'0'),(9000,777,1,'0')]:
   d=proc/str(pid);d.mkdir(parents=True);(d/'stat').write_text(statline(pid,model.get('ppid',ppid) if pid==9544 else ppid,model.get('birth',birth) if pid==9544 else birth))
   (d/'status').write_text('Uid:\t'+'\t'.join([uid]*4)+'\n')
  (proc/'sys/kernel/random').mkdir(parents=True);(proc/'sys/kernel/random/boot_id').write_text(model.get('boot','fixture-boot'))
  (proc/'9544/ns').mkdir();(proc/'1/ns').mkdir(parents=True)
  (proc/'9544/exe').symlink_to(model.get('exe','/data/local/tmp/asx/appspawn-x'))
  (proc/'4421/exe').symlink_to('/data/local/tmp/asx/appspawn-x');(proc/'4421/ns').mkdir()
  (proc/'1/ns/mnt').symlink_to('mnt:[4026531841]')
  (proc/'9544/ns/mnt').symlink_to('mnt:[4026531841]' if model.get('global_ns') else 'mnt:[4026533005]')
  (proc/'4421/ns/mnt').symlink_to('mnt:[4026533005]')
  if model.get('read_error'):(proc/'9544/status').unlink()
  if model.get('exited'):(proc/'9544/stat').write_text(statline(9544,4421,63926,'Z'))
  (f/'lock').mkdir();(f/'lock/owner').write_text('9000 777 fixture-boot\n')
  if model.get('stop'):(f/'stop').write_text('kept')
  for n in ('route-b-owner.sh','readiness-probe.sh'):
   text=(C/n).read_text().replace('PROC=/proc','PROC='+str(proc));(f/n).write_text(text)
  init=r/'init.sh';init.write_text('''
sha256sum(){ case "$1" in */9544/exe) printf '%s  %s\\n' "$CASE_SHA" "$1";; */4421/exe) echo "'''+S+'''  $1";; *) command sha256sum "$@";; esac; }
stat(){ case "$*" in *9544/root*) echo "$CASE_INODE";; *) echo '66352:423310';; esac; }
kill(){ echo forbidden >> "$CASE_VIOLATIONS"; return 99; }
''')
  env=dict(os.environ,BASH_ENV=str(init),TT_RUNTIME=str(rt),TT_OWNER_UID='20011206',CASE_SHA=model.get('sha',S),CASE_INODE=model.get('inode','66352:423310'),CASE_VIOLATIONS=str(r/'violations'))
  if model.get('transition'):
   def update():
    time.sleep(.2);p=proc/'9544/status';q=p.with_suffix('.next');q.write_text('Uid:\t'+'\t'.join(['20011206']*4)+'\n');q.replace(p)
   th=threading.Thread(target=update);th.start()
  begin=time.monotonic()
  if strict:
   text=(C/'watchdog.sh').read_text();functions=text[text.index('private_namespace() {'):text.index('release_lock()')]
   script=f'PROC={proc}; RB_PROC=$PROC; RUNTIME={rt}; RB_RUNTIME=$RUNTIME; RB_OWNER_UID=20011206; . {f}/route-b-owner.sh\n'+functions+'\nparent=4421\nchild_owned 9544 63926\n'
   p=subprocess.run(['bash','-c',script],env=env,capture_output=True,text=True)
  else:
   p=subprocess.run(['timeout','2','bash',str(f/'readiness-probe.sh'),'9544','63926','4421','500','fixture-boot','9000','777'],env=env,capture_output=True,text=True)
  elapsed=time.monotonic()-begin
  if model.get('transition'):th.join()
  rows=[json.loads(x) for x in (p.stdout+p.stderr).splitlines() if x.strip()]
  assert not (r/'violations').exists(),'signal attempted'
  return p,rows,elapsed
class TransitionTests(unittest.TestCase):
 def test_async_root_to_exact_uid(self):
  p,rows,_=run_case({'uid':'0','transition':True});self.assertEqual(p.returncode,0,p.stderr)
  self.assertTrue(any(x['phase']=='readiness_pending' and x['actual']=='0:0:0:0' for x in rows));self.assertEqual(rows[-1]['actual'],'ready')
 def test_already_ready_captured_tuple(self):
  p,rows,_=run_case({});self.assertEqual(p.returncode,0,p.stderr);self.assertEqual(rows[-1]['actual'],'ready')
 def test_root_parent_does_not_overwrite_valid_child_uid(self):
  # Actual context_guard + parent_owned + rb_uid; no context stub.
  p,rows,elapsed=run_case({'uid':'20011206'})
  self.assertEqual(p.returncode,0,p.stderr);self.assertLess(elapsed,1)
  self.assertFalse(any(x['phase']=='readiness_pending' for x in rows))
  self.assertEqual(rows[-1]['actual'],'ready')
class RejectTests(unittest.TestCase):
 def test_permanent_root_times_out(self):
  p,rows,elapsed=run_case({'uid':'0'});self.assertNotEqual(p.returncode,0);self.assertLess(elapsed,2.5)
  self.assertTrue(any(x['field']=='uid' and x['actual']=='0:0:0:0' for x in rows));self.assertFalse(any(x['actual']=='ready' for x in rows))
 def test_eight_failure_fields(self):
  cases=[({'uid':'20010053'},'uid'),({'sha':'0'*64},'exe_sha'),({'exe':'/system/bin/appspawn-x'},'exe'),({'ppid':1},'ppid'),({'global_ns':True},'namespace'),({'inode':'1:2'},'private_inode'),({'birth':123},'birth'),({'boot':'changed'},'boot'),({'read_error':True},'uid'),({'exited':True},'birth'),({'stop':True},'stop')]
  for model,field in cases:
   with self.subTest(model=model):
    p,rows,_=run_case(model);self.assertNotEqual(p.returncode,0);self.assertTrue(any(x['field']==field for x in rows),rows)
    self.assertFalse(any(x['actual']=='ready' for x in rows))
 def test_foreign_while_root_never_waits(self):
  p,rows,elapsed=run_case({'uid':'0','sha':'0'*64});self.assertNotEqual(p.returncode,0);self.assertLess(elapsed,1)
  self.assertEqual(rows[-1]['field'],'exe_sha');self.assertFalse(any(x['phase']=='readiness_pending' for x in rows))
class BindingTests(unittest.TestCase):
 def test_attach_strict_root_rejection_no_wait(self):
  p,rows,elapsed=run_case({'uid':'0'},strict=True);self.assertNotEqual(p.returncode,0);self.assertLess(elapsed,1);self.assertEqual(rows[-1]['field'],'uid')
  s=(C/'watchdog.sh').read_text();attach=s[s.index('# Explicit attach'):s.index('attempt=$((attempt+1))')]
  self.assertEqual(attach.count('timeout 2 sh'),1);self.assertLess(attach.index('else\n'),attach.index('timeout 2 sh'))
  self.assertIn('child_owned "$child" "$child_birth" ||',attach)
 def test_final_strict_guard_remains_authoritative(self):
  p,_,_=run_case({});self.assertEqual(p.returncode,0)
  p,rows,_=run_case({'uid':'0'},strict=True);self.assertNotEqual(p.returncode,0);self.assertEqual(rows[-1]['field'],'uid')
 def test_complete_composition_includes_new_worker(self):
  import importlib.util
  spec=importlib.util.spec_from_file_location('compose_new_candidate',D/'compose.py');m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)
  base=D.parent/'2026-10-12-recovery-executor'
  with tempfile.TemporaryDirectory() as t:
   r=Path(t);old=json.loads((base/'plan.disabled.json').read_text());target=next(x['target'] for x in old['members'] if x['target'].endswith('/watchdog.sh') and '/recovery-attempts/' in x['target']).rsplit('/',1)[0]+'/readiness-probe.sh'
   pre=r/'worker-preimage.json';pre.write_text(json.dumps({'target':target,'exists':False,'proof':'isolated fresh fixture'}))
   result=m.compose(base,base/'plan.disabled.json',sha(base/'plan.disabled.json'),pre,sha(pre),r/'new')
   self.assertEqual(result['members'],24);self.assertFalse(result['execution_enabled'])
   plan=json.loads((r/'new/plan.disabled.json').read_text());worker=[x for x in plan['members'] if x['target']==target]
   self.assertEqual(len(worker),1);self.assertEqual(worker[0]['sha256'],sha(C/'readiness-probe.sh'))
   self.assertEqual(worker[0]['after']['mode'],'550');self.assertIn(' readiness-probe.sh 550',(r/'new/payload/members.tsv').read_text())
 def test_binding_closure_and_history(self):
  for n in ('watchdog.sh','route-b-owner.sh'):self.assertIn(sha(C/n),(C/'entry.sh').read_text())
  mapping={'start-parent.sh':'start-parent-prepared.sh','spawn.sh':'spawn-prepared.sh','screen-gate':'screen-gate-feed'};base=D.parent/'2026-10-12-recovery-executor/payload'
  for line in (C/'members.tsv').read_text().splitlines():
   digest,name,_=line.split();p=C/mapping.get(name,name)
   if not p.exists():p=base/mapping.get(name,name)
   self.assertEqual(digest,sha(p),name)
  self.assertIn(sha(C/'members.tsv'),(C/'startup.env').read_text())
  self.assertEqual((C/'startup.expected.sha256').read_text().strip(),sha(C/'startup.env'))
  self.assertEqual(sha(base/'watchdog.sh'),'9763171a0b6dab1b23b72e454cb2c6256181298bc282e81b6ae8e38fa9577072')
  self.assertEqual(sha(OLD/'watchdog.sh'),'9a54b2fc470a483e55caa93cfc952cc6e14d2530ed3ffaf6a758c21e08837ff2')
if __name__=='__main__':unittest.main()
