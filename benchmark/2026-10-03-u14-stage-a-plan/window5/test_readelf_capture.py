"""Capture preserves production return values and failure evidence."""
import importlib.util,subprocess,tempfile,unittest,json
from pathlib import Path

class CaptureTests(unittest.TestCase):
 def test_empty_stdout_preserved_and_recorded(self):
  with tempfile.TemporaryDirectory() as td:
   root=Path(td);tool=root/'llvm-readelf';tool.write_bytes(b'tool');elf=root/'input.so';elf.write_bytes(b'elf')
   argv=[str(tool),'-d','--wide',str(elf)];completed=subprocess.CompletedProcess(argv,0,'','');seen=[]
   original=subprocess.run
   def fake(*args,**kwargs):seen.append((args,kwargs));return completed
   spec=importlib.util.spec_from_file_location('capture',Path(__file__).parent/'common/readelf_capture.py');m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)
   try:
    subprocess.run=fake;m.install(root/'capture');result=subprocess.run(argv,capture_output=True,text=True,env={'LC_ALL':'C'})
    self.assertIs(result,completed);self.assertEqual(seen[0][0][0],argv);self.assertEqual(seen[0][1]['env'],{'LC_ALL':'C'})
    row=json.loads((root/'capture/0001.json').read_text());self.assertEqual(row['returncode'],0);self.assertEqual(row['stdout_bytes'],0);self.assertFalse(row['dynamic_header_present'])
   finally:subprocess.run=original

if __name__=='__main__':unittest.main()
