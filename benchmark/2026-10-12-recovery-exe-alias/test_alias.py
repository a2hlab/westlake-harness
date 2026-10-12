#!/usr/bin/env python3
"""Captured-field replay of actual shell guards; no native execution/signals."""
import hashlib,json,os,re,subprocess,tempfile,unittest
from pathlib import Path
D=Path(__file__).resolve().parent
BASE=D.parent/'2026-10-12-recovery-executor/payload'
SHA='a7a358c60bec293c26531b0eecbf14979f77411c227cec4767742c0c82791a0c'
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def replay(filename,role='parent',**change):
 with tempfile.TemporaryDirectory() as t:
  root=Path(t);proc=root/'proc';(proc/'5153').mkdir(parents=True);(proc/'5154').mkdir()
  raw=(D/'evidence/parent-identity.txt').read_text().splitlines()[0]
  (proc/'5153/stat').write_text(raw+'\n');(proc/'5154/stat').write_text(raw.replace('5153 (main) S 1 ','5154 (child) S 5153 ',1)+'\n')
  uid=change.get('uid', '0:0:0:0' if role=='parent' else '20011206:20011206:20011206:20011206')
  for pid in ('5153','5154'):(proc/pid/'status').write_text('Uid:\t'+uid.replace(':','\t')+'\n')
  source=(D/'candidate'/filename).read_text()
  helper=(D/'candidate/route-b-owner.sh').read_text()
  if role=='parent':
   begin=source.index('private_namespace()');end=source.index('child_owned()' if filename=='watchdog.sh' else '# Existing parent reuse',begin)
   funcs=source[begin:end]; call='parent_owned 5153 '+change.get('birth','15134')
  else:
   source=(D/'candidate/watchdog.sh').read_text();begin=source.index('private_namespace()');end=source.index('release_lock()',begin)
   funcs=source[begin:end];call='child_owned 5154 '+change.get('birth','15134')
  exe=change.get('exe','/data/local/tmp/asx/appspawn-x');ns=change.get('ns','mnt:[4026533005]');inode=change.get('inode','66352:423788')
  shell='''set -u
PROC=$FIX_PROC; RB_PROC=$PROC; RUNTIME=$FIX_RT; RB_RUNTIME=$RUNTIME; RB_OWNER_UID=20011206
'''+helper+'''\nreadlink(){ case "$1" in */exe) printf '%s\\n' "$FIX_EXE";; */1/ns/mnt) echo 'mnt:[4026531841]';; */ns/mnt) printf '%s\\n' "$FIX_NS";; *) return 1;; esac; }
sha256sum(){ printf '%s  %s\\n' "$FIX_SHA" "$1"; }
stat(){ case "$*" in *root/data/local/tmp/asx/run.sh*) echo "$FIX_INODE";; *) echo '66352:423788';; esac; }
kill(){ echo FORBIDDEN_SIGNAL >&2; return 99; }
'''+funcs+'\nparent=5153\n'+call+'\n'
  env=dict(os.environ,FIX_PROC=str(proc),FIX_RT=str(root/'runtime'),FIX_EXE=exe,FIX_NS=ns,FIX_INODE=inode,FIX_SHA=change.get('sha',SHA))
  r=subprocess.run(['bash','-c',shell],env=env,capture_output=True,text=True)
  if 'FORBIDDEN_SIGNAL' in r.stderr:raise AssertionError('signal attempted')
  return r.returncode
class IdentityTests(unittest.TestCase):
 def test_actual_parent_and_legacy_exact_aliases(self):
  for f in ('launch-common.sh','watchdog.sh'):
   for exe in ('/data/local/tmp/asx/appspawn-x','/data/local/tmp/asx/asx-spawner','/data/local/tmp/asx/appspawn-x (deleted)'):
    with self.subTest(file=f,exe=exe):self.assertEqual(replay(f,exe=exe),0)
 def test_child_helper_chain_exact_aliases(self):
  for exe in ('/data/local/tmp/asx/appspawn-x','/data/local/tmp/asx/asx-spawner'):
   self.assertEqual(replay('route-b-owner.sh',role='child',exe=exe),0)
class RejectTests(unittest.TestCase):
 def test_fields_and_foreign_paths_reject(self):
  changes=[{'sha':'0'*64},{'uid':'99:99:99:99'},{'birth':'99999'},{'ns':'mnt:[4026531841]'},{'inode':'66352:999'},{'exe':'/system/bin/appspawn-x'},{'exe':'/tmp/appspawn-x'}]
  for f in ('launch-common.sh','watchdog.sh'):
   for change in changes:
    with self.subTest(file=f,change=change):self.assertNotEqual(replay(f,**change),0)
 def test_child_effective_guard_rejects(self):
  for c in ({'sha':'0'*64},{'uid':'0:0:0:0'},{'birth':'999'},{'ns':'mnt:[4026531841]'},{'inode':'1:2'},{'exe':'/system/bin/appspawn-x'}):
   with self.subTest(change=c):self.assertNotEqual(replay('route-b-owner.sh',role='child',**c),0)
class BindingTests(unittest.TestCase):
 def test_binding_closure_and_old_bytes(self):
  c=D/'candidate';entry=(c/'entry.sh').read_text()
  for n in ('watchdog.sh','route-b-owner.sh'):self.assertIn(sha(c/n),entry)
  mapping={'start-parent.sh':'start-parent-prepared.sh','spawn.sh':'spawn-prepared.sh','screen-gate':'screen-gate-feed'}
  for line in (c/'members.tsv').read_text().splitlines():
   digest,name,mode=line.split();p=c/mapping.get(name,name)
   if not p.exists():p=BASE/mapping.get(name,name)
   self.assertEqual(digest,sha(p),name)
  self.assertIn(sha(c/'members.tsv'),(c/'startup.env').read_text())
  self.assertEqual((c/'startup.expected.sha256').read_text().strip(),sha(c/'startup.env'))
  self.assertEqual(sha(BASE/'watchdog.sh'),'9763171a0b6dab1b23b72e454cb2c6256181298bc282e81b6ae8e38fa9577072')
  self.assertEqual(sha(BASE/'route-b-owner.sh'),'80a263d930a67c48fa92f5caa7b6266ee13ff75079ff5ba880e9576da72dbdc4')
 def test_only_exact_allowlist_changes(self):
  old="/data/local/tmp/asx/asx-spawner|'/data/local/tmp/asx/asx-spawner (deleted)'"
  new=old+"|/data/local/tmp/asx/appspawn-x|'/data/local/tmp/asx/appspawn-x (deleted)'"
  for name in ('watchdog.sh','route-b-owner.sh','launch-common.sh'):
   self.assertEqual((D/'candidate'/name).read_text(),(BASE/name).read_text().replace(old,new))
if __name__=='__main__':unittest.main()
