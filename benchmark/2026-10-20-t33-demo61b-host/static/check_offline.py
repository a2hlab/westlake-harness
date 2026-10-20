#!/usr/bin/env python3
"""Local policy/dispatch checks; never imports the device entrypoint."""
import ast,json,re,sys,tempfile,types,unittest
from pathlib import Path
HERE=Path(__file__).resolve().parent
TREE=ast.parse((HERE/'window_ops.py').read_text())
FUNCTIONS={n.name:n for n in TREE.body if isinstance(n,ast.FunctionDef)}
ns={'re':re}
for name in ['wid_normalize','hexbytes','stat_fields','parse_hashes']:
 exec(compile(ast.Module(body=[FUNCTIONS[name]],type_ignores=[]),'actual-window-ops','exec'),ns)
DISPATCH=next(n for n in TREE.body if isinstance(n,ast.If) and ast.unparse(n.test)=="a.action == 'intake'")
class Checks(unittest.TestCase):
 def test_real_run_wid_only(self):
  raw=(HERE/'reference-run.sh').read_bytes();other=raw.replace(b'WL_PARENT_ID=33',b'WL_PARENT_ID=41')
  self.assertEqual(ns['wid_normalize'](raw)[0],ns['wid_normalize'](other)[0])
  self.assertEqual(ns['wid_normalize'](other)[1],41)
 def test_nonwid_drift(self):
  raw=(HERE/'reference-run.sh').read_bytes()
  self.assertNotEqual(ns['wid_normalize'](raw)[0],ns['wid_normalize'](raw.replace(b'20011206',b'20011300'))[0])
 def test_duplicate_wid(self):
  with self.assertRaises(AssertionError):ns['wid_normalize'](b'export WL_PARENT_ID=33\nexport WL_PARENT_ID=29\n')
 def test_hex_invalid(self):
  with self.assertRaises(AssertionError):ns['hexbytes']('tr inaccessible')
 def test_dead_stat(self):
  with self.assertRaises(AssertionError):ns['stat_fields']('1 (name with spaces) Z '+'1 '*25)
 def test_hash_error(self):
  with self.assertRaises(AssertionError):ns['parse_hashes']('sha256sum: missing file')
 def drive(self,action,current):
  calls=[];records={};state=[current];old='a'*64;new='b'*64
  with tempfile.TemporaryDirectory(dir=HERE) as t:
   out=Path(t);local=out/'input.hap';local.write_bytes(b'fixture')
   def read(label,live=True):
    calls.append(('read',label,live));d=out/label;d.mkdir();(d/'data-metadata.txt').write_text('identical')
    return state[0],{'uid':20011206,'gid':20011206,'appId':'same','applicationInfo':{'accessTokenId':1}}
   class Board:
    def shell(self,cmd,**kw):
     calls.append(('shell',cmd))
     if cmd.startswith('bm install'):state[0]=new if action=='install' else old;return 0,'success'
     if cmd.startswith('sha256sum'):return 0,state[0]+'  /hap' if cmd=='sha256sum /hap' else (new if action=='install' else old)+'  /uploaded'
     return 0,''
    def send(self,*args):calls.append(('send',))
   env={'a':types.SimpleNamespace(action=action,extra=[str(local)]),'Path':Path,'old':old,'new':new,'sha':lambda p:new if action=='install' else old,'bd':Board(),'HAP':'/hap','parse_hashes':ns['parse_hashes'],'save':lambda p,x:records.update({p.name:x}),'out':out,'time':types.SimpleNamespace(time=lambda:1),'read':read,'c':{'remote':'/stage'},'sys':sys,'print':lambda *a:None}
   try:exec(compile(ast.Module(body=[DISPATCH],type_ignores=[]),'actual-dispatch','exec'),env)
   except SystemExit:pass
   except AssertionError:records['refused']=True
  return calls,records
 def test_install_requires_live(self):
  calls,records=self.drive('install','a'*64)
  self.assertIn(('read','before',True),calls);self.assertIn(('read','after',False),calls);self.assertIn('hap-before-operation.json',records);self.assertNotIn('refused',records)
 def test_rollback_no_host(self):
  calls,records=self.drive('rollback','b'*64)
  self.assertIn(('read','before',False),calls);self.assertIn(('send',),calls);self.assertNotIn('refused',records)
 def test_rollback_already_old(self):
  calls,records=self.drive('rollback','a'*64)
  self.assertNotIn(('send',),calls);self.assertIn('rollback-already-original.json',records)
 def test_foreign_recorded_no_send(self):
  calls,records=self.drive('rollback','c'*64)
  self.assertIn('hap-before-operation.json',records);self.assertIn('refused',records);self.assertNotIn(('send',),calls)
if __name__=='__main__':unittest.main()
