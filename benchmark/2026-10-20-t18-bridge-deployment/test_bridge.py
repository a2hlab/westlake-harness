"""Exercise the actual generated fifth-artifact transaction using host filesystem seams."""
import ast,hashlib,json,os,subprocess,sys,tempfile,unittest
from pathlib import Path
from test_executor import helpers,SOURCE,TREE,B
from derive import derive
class BridgeTests(unittest.TestCase):
 def test_donor_drift(self):
  with self.assertRaises(AssertionError):derive(b'foreign source')
 def test_guards_and_helpers_preserved(self):
  self.assertIn("age<1200",SOURCE);self.assertIn("1800-age",SOURCE)
  self.assertIn("-(0 if a.mode=='rollback' else 600)",SOURCE)
  self.assertIn("bridge_before_sha']==BBEFORE",SOURCE)
  self.assertIn("assert bactual in (BBEFORE,BAFTER)",SOURCE)
  self.assertIn("(BRIDGE,bridge_backup,BBEFORE,bmeta,blabel,bactual)",SOURCE)
  self.assertIn("missing backup for changed target",SOURCE)
  self.assertIn("same execution window/source",SOURCE)
  self.assertIn("PHYSICAL_FILES_RESTORED_REQUIRES_FRESH_BOOT",SOURCE)
 def test_candidate_and_closure_refusal_before_board(self):
  for digest,word in [(None,b'candidate pin required'),('a'*64,b'production closure required')]:
   with tempfile.TemporaryDirectory(dir=B) as td:
    root=Path(td).resolve();(root/'executor.py').write_text(SOURCE)
    c=json.loads((B/'bridge-candidate.json').read_text());c['after_sha256']=digest;c['production_refs']=[]
    (root/'bridge-candidate.json').write_text(json.dumps(c))
    args=[sys.executable,str(root/'executor.py'),'apply','--execute','--boot','x','--parent','1','--birth','2','--hdc','NEVER_RUN','--holder','x','--out',str(root/'out'),'--repo',str(root),'--inputs',str(root),'--admission',str(root/'missing.json'),'--start','1']
    got=subprocess.run(args,capture_output=True)
    self.assertNotEqual(got.returncode,0);self.assertIn(word,got.stderr);self.assertFalse((root/'out').exists())
 def transaction(self,env):
  start=SOURCE.index('script=pre\n');end=SOURCE.index("completion=",start)
  exec(compile(SOURCE[start:end],'actual-transaction','exec'),env)
  return env['script']
 def test_partial_swap_then_original_restore(self):
  for cut in (1,2,3,4):
   with self.subTest(cut=cut),tempfile.TemporaryDirectory() as td:
    root=Path(td).resolve();stage=root/'stage';stage.mkdir();e=helpers(root)
    names={'BRIDGE':'liboh_adapter_bridge.so','MEDIA':'media.so','PLAYER':'player.so','DSO':'compat.so'}
    before=b'original-run';after=b'candidate-run';old={name:('before-'+name).encode() for key,name in names.items() if key!='DSO'};new={name:('after-'+name).encode() for name in names.values()}
    (root/'run.sh').write_bytes(before);(stage/'run.sh').write_bytes(after)
    for name,data in old.items():(root/name).write_bytes(data)
    for name,data in new.items():(stage/name).write_bytes(data)
    # The real transaction's staged media/player basenames are fixed.
    (stage/'libmffmpeg.so').write_bytes(new[names['MEDIA']]);(stage/'libttmplayer.so').write_bytes(new[names['PLAYER']])
    meta=f'644:{os.getuid()}:{os.getgid()}';label='u:object_r:appdat:s0'
    e.update(names,stage=str(stage),pre='',meta=meta,label=label,dlabel=label,bmeta=meta,blabel=label,mmeta=meta,mlabel=label,pmeta=meta,plabel=label,expected=e['sha'](before),actual=e['sha'](before),before=before,after=after,new=after,parent_guard='',dso_present=False)
    for k,name in [('B',names['BRIDGE']),('M',names['MEDIA']),('P',names['PLAYER'])]:e[k+'BEFORE']=e['sha'](old[name]);e[k+'AFTER']=e['sha'](new[name]);e[k.lower()+'actual']=e[k+'BEFORE']
    e['DSHA']=e['sha'](new[names['DSO']]);e['a'].mode='apply'
    shim='''stat() { /usr/bin/stat -f '%Lp:%u:%g' "$3"; }
ls() { printf 'u:object_r:appdat:s0 %s\\n' "$2"; }
chcon() { return 0; }
chown() { return 0; }
'''
    # Each original backup must already exist when the first real rename happens.
    guard='; '.join('test -f '+e['q'](str(root/name)+'.t18-5cd-before-12345678') for name in ['run.sh',names['BRIDGE'],names['MEDIA'],names['PLAYER']])
    fail=f'moved=0; mv() {{ {guard}; command mv "$@"; moved=$((moved+1)); test "$moved" -lt {cut}; }}\n'
    got=subprocess.run(['sh','-c','set -eu\n'+shim+fail+self.transaction(e)],capture_output=True)
    self.assertNotEqual(got.returncode,0)
    for name,data in {'run.sh':before,**old}.items():self.assertEqual(Path(str(root/name)+'.t18-5cd-before-12345678').read_bytes(),data)
    e['a'].mode='rollback';e['new']=before;(stage/'run.sh').write_bytes(before)
    for k,name in [('b',names['BRIDGE']),('m',names['MEDIA']),('p',names['PLAYER'])]:e[k+'actual']=e['sha']((root/name).read_bytes())
    e['actual']=e['expected']=e['sha']((root/'run.sh').read_bytes());e['dso_present']=(root/names['DSO']).exists()
    got=subprocess.run(['sh','-c','set -eu\n'+shim+self.transaction(e)],capture_output=True)
    self.assertEqual(got.returncode,0,got.stderr)
    for name,data in {'run.sh':before,**old}.items():self.assertEqual((root/name).read_bytes(),data)
    self.assertFalse((root/names['DSO']).exists())
if __name__=='__main__':unittest.main()
