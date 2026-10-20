#!/usr/bin/env python3
"""Host-only real shell tests: no Board/device execution."""
import importlib.util,json,subprocess,tempfile,unittest,hashlib
from pathlib import Path
HERE=Path(__file__).resolve().parent
s=importlib.util.spec_from_file_location('reader',HERE/'read_binding.py');m=importlib.util.module_from_spec(s);s.loader.exec_module(m)
class ReaderTests(unittest.TestCase):
 def shell_read(self,data,fail=False):
  with tempfile.TemporaryDirectory() as td:
   path=Path(td)/'bytes';path.write_bytes(data)
   cmd=m.word_command(2,8,'TEST').replace('if=/proc/2/mem',f'if={path}').replace('skip=1','skip=0')
   if fail:cmd=cmd.replace(f'if={path}',f'if={path}.absent')
   r=subprocess.run(['sh','-c',cmd],stdout=subprocess.PIPE,stderr=subprocess.STDOUT)
   self.assertEqual(r.returncode,0) # shell completion does not imply dd/read success
   return r.stdout.decode()
 def test_real_merged_shell_binary(self):
  value=b'\x00\xff\n\x80\x00\r\x19\x7f';self.assertEqual(m.parse_word(self.shell_read(value),'TEST'),int.from_bytes(value,'little'))
 def test_real_short_read(self):
  with self.assertRaises(ValueError):m.parse_word(self.shell_read(b'1234567'),'TEST')
 def test_real_dd_error_retained(self):
  raw=self.shell_read(b'',True);self.assertIn('TEST_DD_RC:1',raw)
  with self.assertRaises(ValueError):m.parse_word(raw,'TEST')
 def test_frame_missing_duplicate(self):
  raw=self.shell_read(b'12345678')
  for text in [raw.replace('TEST_END',''),raw+raw,raw.replace('TEST_DD_RC:0','TEST_DD_RC:1')]:
   with self.assertRaises(ValueError):m.parse_word(text,'TEST')
 def test_map_inode_mismatch(self):
  row={'path':'/known','device':'103:30','inode':'7'}
  self.assertEqual(m.identity('a file\n66352:7','/known','a',[row])['device_inode'],'66352:7')
  for rows in [[],[dict(row,inode='8')],[dict(row,device='00:01')]]:
   with self.assertRaises(ValueError):m.identity('a file\n66352:7','/known','a',rows)
 def profile(self):
  p=json.loads((HERE/'reader-profile.template.json').read_text());p.update(boot='00000000-0000-0000-0000-000000000000',observed_at=1,readonly_receipt_sha256='a'*64,run_sha256=m.sha(HERE/'run5cd.r9.reference.sh'),init_mnt='mnt:[1]')
  p['parent']={'pid':2,'ppid':1,'birth':3,'uid':0,'exe_sha256':m.EXE,'mnt':'mnt:[2]'}
  p['child']={'pid':4,'ppid':2,'birth':5,'uid':20011300,'exe_sha256':m.EXE,'mnt':'mnt:[2]'}
  p['libc']['sha256']='b'*64;return p
 def test_profile_good_and_foreign(self):
  p=self.profile();m.validate(p,HERE/'run5cd.r9.reference.sh')
  for mutate in [lambda p:p.update(serial='61b0657200000000000000000324012c'),lambda p:p['child'].update(uid=20011301),lambda p:p['child'].update(ppid=9),lambda p:p.update(init_mnt='mnt:[2]')]:
   p=self.profile();mutate(p)
   with self.assertRaises(ValueError):m.validate(p,HERE/'run5cd.r9.reference.sh')
 def test_only_wid_run_derivation(self):
  with tempfile.TemporaryDirectory() as td:
   path=Path(td)/'run';base=(HERE/'run5cd.r9.reference.sh').read_bytes()
   for extra in [b'',b'# foreign\n']:
    path.write_bytes(base.replace(b'WL_PARENT_ID=29\n',b'WL_PARENT_ID=44\n')+extra);p=self.profile();p['run_sha256']=m.sha(path)
    if not extra:m.validate(p,path)
    else:
     with self.assertRaises(ValueError):m.validate(p,path)
 def test_preview_no_import_board(self):
  r=subprocess.run(['python3',str(HERE/'read_binding.py')],capture_output=True);self.assertEqual(r.returncode,0);self.assertEqual(json.loads(r.stdout)['device_calls'],0)
if __name__=='__main__':unittest.main()
