#!/usr/bin/env python3
import pathlib,unittest,tempfile,subprocess,os,re,hashlib
P=pathlib.Path(__file__).resolve().parent
class Tests(unittest.TestCase):
 def test_base_unchanged(self):
  self.assertEqual(hashlib.sha256((P.parent/'prepare_jit51-owner-5cd.sh').read_bytes()).hexdigest(),'78261c5222f533c3af07eb6bdab0d50272cc05323105f4c0680124ac42b18aa6')
 def gate(self,args,host,data,ok):
  with tempfile.TemporaryDirectory() as td:
   root=pathlib.Path(td);(root/'data/data').mkdir(parents=True);bin=root/'bin';bin.mkdir()
   tool=bin/'stat';tool.write_text('#!/bin/sh\ncase "$*" in *org.westlake.imehost) printf "%s\\n" "$HOST";; *) printf "%s\\n" "$DATA";; esac\n');tool.chmod(0o755)
   src=(P/'prepare_jit51-owner.sh').read_text().split('# Validate all existing explicit directories')[0]+'\nexit 0\n'
   src=re.sub(r'(?<![\w/])/data',lambda _:str(root/'data'),src)
   r=subprocess.run(['sh','-c',src,'fixture',*args],env={**os.environ,'PATH':str(bin)+':'+os.environ['PATH'],'HOST':host,'DATA':data},capture_output=True)
   self.assertEqual(r.returncode==0,ok,r.stderr)
 def test_61b(self):self.gate(['--expected-uid','20011206'],'20011206:20011206','20011206:20011206',True)
 def test_5cd(self):self.gate(['--expected-uid','20011300'],'20011300:20011300','20011300:20011300',True)
 def test_wrong_uid(self):self.gate(['--expected-uid','20011206'],'20011300:20011300','20011300:20011300',False)
 def test_wrong_namespace(self):self.gate(['--expected-uid','20011300'],'20011300:20011300','1000:1000',False)
 def test_missing(self):self.gate([],'20011300:20011300','20011300:20011300',False)
 def test_invalid(self):self.gate(['--expected-uid','0'],'0:0','0:0',False)
if __name__=='__main__':unittest.main(verbosity=2)
