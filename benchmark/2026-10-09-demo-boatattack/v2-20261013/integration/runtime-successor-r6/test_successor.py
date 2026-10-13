import importlib.util,json,os,tempfile,unittest
from pathlib import Path
S=Path(__file__).with_name('successor.py')
spec=importlib.util.spec_from_file_location('successor',S);m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)
# Locate sibling main from the workspaces directory without a user-specific path.
MAIN=next(p for p in S.resolve().parents if (p/'westlake-harness').is_dir())/'westlake-harness'
CAP=MAIN/'benchmark/2026-10-09-demo-boatattack/v2-20261013/outer/r6-5ea-readonly/control'
class Tests(unittest.TestCase):
 def test_actual_derivation(self):
  t=(CAP/'binds.tsv').read_text();w=(CAP/'worker.sh').read_text();nt,nw=m.derive(t,w,'a'*64)
  self.assertEqual(sum(a!=b for a,b in zip(t.splitlines(),nt.splitlines())),1)
  self.assertEqual(sum(a!=b for a,b in zip(w.splitlines(),nw.splitlines())),2)
  self.assertEqual(nw.count('no_parent'),w.count('no_parent'))
  self.assertIn('18763dd4',nw);self.assertIn('9ccf64f8',nw)
 def test_partial_table_rejected(self):
  with self.assertRaises(ValueError):m.derive('\n'.join((CAP/'binds.tsv').read_text().splitlines()[:6]),(CAP/'worker.sh').read_text(),'a'*64)
 def test_worker_extra_pin_rejected(self):
  with self.assertRaises(ValueError):m.derive((CAP/'binds.tsv').read_text(),(CAP/'worker.sh').read_text()+m.OLD,'a'*64)
 def test_recover_and_cfg_no_worker_hash(self):
  w=m.sha(CAP/'worker.sh')
  for f in ['recover-v3-boat.sh','00_westlake_u13_recover-v3.cfg']:
   txt=(CAP/f).read_text();self.assertNotIn(w,txt);self.assertIn(m.ROOT+'/worker.sh',txt)
 def test_actual_prepare_preview(self):
  import argparse,contextlib,io
  with tempfile.TemporaryDirectory(dir=S.parent) as td:
   d=Path(td);candidate=d/'candidate.so';candidate.write_bytes(b'OFFLINE FIXTURE ONLY')
   old=os.environ.get('WORKSPACES');os.environ['WORKSPACES']=str(MAIN.parent)
   try:
    a=argparse.Namespace(main=str(MAIN),runtime=candidate,runtime_sha256=m.sha(candidate),hdc='/fixture/hdc',out=d/'package')
    with contextlib.redirect_stdout(io.StringIO()):m.prepare(a)
    p=m.read(a.out/'plan.disabled.json');m.validate(p)
    self.assertFalse(p['execution_enabled']);self.assertEqual(len(p['members']),3);self.assertEqual(len(p['expected319']),319)
    p['members'][2]['after']['mode']='777'
    with self.assertRaises(ValueError):m.validate(p)
   finally:
    if old is None:os.environ.pop('WORKSPACES',None)
    else:os.environ['WORKSPACES']=old
 def test_foreign_preimage_rejected_without_send(self):
  class C:
   equal=staticmethod(lambda a,b:all(a.get(k)==v for k,v in b.items()))
  class D:
   def probe(self,p):return dict(exists=True,sha256='foreign')
   def send(self,*a):self.fail('send must never occur')
   def shell(self,*a):raise AssertionError('shell must never occur')
  with self.assertRaisesRegex(ValueError,'signed preimage'):
   m.atomic_place(C,D(),dict(target='/fixture',before=dict(exists=True,sha256='approved')))
 def test_atomic_old_open_inode_preserved(self):
  import shlex,shutil
  with tempfile.TemporaryDirectory() as td:
   d=Path(td);target=d/'runtime';target.write_bytes(b'old-mapped');source=d/'new';source.write_bytes(b'new-object')
   meta=dict(mode='755',uid=0,gid=0,label='u:object_r:system_lib_file:s0');events=[]
   class C:
    q=staticmethod(shlex.quote);resolve=staticmethod(Path)
    equal=staticmethod(lambda a,b:all(a.get(k)==v for k,v in b.items()))
   class D:
    def probe(self,p):return dict(exists=True,sha256=m.sha(p),**meta)
    def send(self,n,s,t):events.append((n,t));self.stage=t;shutil.copyfile(s,t)
    def shell(self,n,script):
     events.append((n,script))
     if n=='atomic-replace':
      self.assertions(script);os.replace(self.stage,target)
    def assertions(self,script):
     assert 'mv ' in script and 'sha256sum' in script and 'stat -c %d:%i' in script
   with target.open('rb') as original:
    inode=target.stat().st_ino;m.atomic_place(C,D(),dict(target=str(target),source=str(source),sha256=m.sha(source),after=meta,before=dict(exists=True,sha256=m.sha(target),**meta)))
    self.assertEqual(original.read(),b'old-mapped');self.assertEqual(target.read_bytes(),b'new-object');self.assertNotEqual(inode,target.stat().st_ino)
   self.assertTrue(all(t!=str(target) for n,t in events if n=='atomic-stage'))
if __name__=='__main__':unittest.main()
