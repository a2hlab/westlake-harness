#!/usr/bin/env python3
import argparse,importlib.util,json,subprocess,tempfile,unittest
from pathlib import Path
import collect_reader_profile as c
H=Path(__file__).resolve().parent
class CollectorTests(unittest.TestCase):
 def args(self):return argparse.Namespace(boot='00000000-0000-0000-0000-000000000000',parent=2,parent_birth=3,child=4,child_birth=5,host=6,host_birth=7,holder='outer(codex) 5cd1e3dd00000000000000000923012c 1970-01-01T00:00:01+00:00',start=1)
 def process(self,pid,birth,uid,ppid=1):return f'{pid} (name with spaces) S {ppid} '+' '.join(['0']*17)+f' {birth}\nTracerPid:\t0\nUid:\t{uid}\t{uid}\t{uid}\t{uid}\nmnt:[2]\n'+c.r.EXE+f' /proc/{pid}/exe'
 def test_process_actual_status_order(self):
  p=c.parse_process(self.process(4,5,20011300,2),4,5,20011300);self.assertEqual(p['ppid'],2)
 def test_birth_uid_tracer_state(self):
  s=self.process(4,5,20011300,2)
  for bad in [s.replace(') S ',') Z '),s.replace('TracerPid:\t0','TracerPid:\t9'),s.replace('Uid:\t20011300','Uid:\t0'),s.replace('0 5\n','0 6\n')]:
   with self.assertRaises(ValueError):c.parse_process(bad,4,5,20011300)
 def test_explicit_identity_and_holder(self):
  c.validate_args(self.args())
  for key,value in [('parent',None),('child_birth',None),('host',4),('start',2)]:
   a=self.args();setattr(a,key,value)
   with self.assertRaises((ValueError,TypeError)):c.validate_args(a)
 def test_complete_sections(self):
  self.assertEqual(c.sections('TOK_DATA\nabc\nTOK_COMPLETE','TOK')['DATA'],'abc')
  for text in ['TOK_DATA\nabc\n','TOK_DATA\na\nTOK_DATA\nb\nTOK_COMPLETE\n']:
   with self.assertRaises(ValueError):c.sections(text,'TOK')
 def test_script_syntax_readonly(self):
  text=c.script(self.args(),'TOK');p=subprocess.run(['sh','-n'],input=text.encode(),capture_output=True);self.assertEqual(p.returncode,0,p.stderr)
  for forbidden in ['kill ','reboot','file send','mkdir ','power-shell','uitest','tee ','/mem'] :self.assertNotIn(forbidden,text)
 def test_derive_fixture(self):
  a=self.args();parts={'INIT_MNT':'mnt:[1]','INIT_MNT_AFTER':'mnt:[1]','RUN_HEX':(H/'run5cd.r9.reference.sh').read_bytes().hex()}
  for phase in ['BEFORE','AFTER']:
   for role,uid in [('parent',0),('child',20011300),('host',20011300)]:parts[phase+'_'+role.upper()]=self.process(getattr(a,role),getattr(a,role+'_birth'),uid,2 if role=='child' else 1)
   parts[phase+'_RUN']=c.r.sha(H/'run5cd.r9.reference.sh')+' file\n66352:11\n66352:11\n66352:11'
   rows=[]
   for i,(key,(path,digest)) in enumerate(c.MODULES.items()):
    for label in ['PHYSICAL','PRIVATE']:parts[phase+'_'+key.upper()+'_'+label]=(digest or 'a'*64)+' file\n66352:'+str(20+i)
    rows.append({'path':path,'device':'103:30','inode':str(20+i),'lo':i*4096,'hi':(i+1)*4096})
   parts[phase+'_MAPS']=json.dumps(rows)
  class Donor:
   map_rows=staticmethod(json.loads)
  with tempfile.TemporaryDirectory() as t:
   p,files=c.derive(a,parts,Path(t),'a'*64,Donor);self.assertEqual(p['child']['pid'],4);self.assertEqual(len(files),4)
   parts['AFTER_RUN']=parts['AFTER_RUN'].replace('66352:11','66352:12')
   with self.assertRaises(ValueError):c.derive(a,parts,Path(t),'a'*64,Donor)
 def test_missing_module_rejected(self):
  with self.assertRaises(ValueError):c.r.identity('a file\n66352:7','/missing','a',[])
 def test_preview_zero_devices(self):
  p=subprocess.run(['python3',str(H/'collect_reader_profile.py')],capture_output=True);self.assertEqual(p.returncode,0);self.assertEqual(json.loads(p.stdout)['device_calls'],0)
if __name__=='__main__':unittest.main()
