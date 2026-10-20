import copy,json,tempfile,unittest,shutil,os
from pathlib import Path
from check_receipt import check
HERE=Path(__file__).resolve().parent
class ReceiptNegatives(unittest.TestCase):
 def setUp(self):
  self.temp=tempfile.TemporaryDirectory(dir=HERE/'.private');self.root=Path(self.temp.name);self.out=self.root/'out';self.source=self.root/'source';self.out.mkdir();self.source.mkdir()
  original=Path(os.environ['T26_HOST_OUT']);self.receipt=json.loads((original/'receipt.json').read_text())
  for p in original.iterdir():
   if p.is_file():shutil.copyfile(p,self.out/p.name)
  for row in self.receipt['sources']:
   p=self.source/row['path'];p.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(HERE/row['path'],p)
 def tearDown(self):self.temp.cleanup()
 def write(self): (self.out/'receipt.json').write_text(json.dumps(self.receipt))
 def test_good(self):self.assertEqual(check(self.out,self.source)['core_cases'],34)
 def test_missing_raw(self):
  (self.out/'21-route-valid.stderr').unlink()
  with self.assertRaises(ValueError):check(self.out,self.source)
 def test_failed_rc(self):
  (self.out/'21-route-valid.rc').write_text('1')
  with self.assertRaises(ValueError):check(self.out,self.source)
 def test_wrong_source(self):
  (self.source/'yv12.c').write_text('foreign')
  with self.assertRaises(ValueError):check(self.out,self.source)
 def test_wrong_binary(self):
  (self.out/'test_route').write_bytes(b'foreign')
  with self.assertRaises(ValueError):check(self.out,self.source)
 def test_missing_case(self):
  self.receipt['steps'].pop();self.write()
  with self.assertRaises(ValueError):check(self.out,self.source)
 def test_fake_success(self):
  (self.out/'11-core-test.stdout').write_text('PASS')
  with self.assertRaises(ValueError):check(self.out,self.source)
 def test_drift_before(self):
  (self.out/'sources-before.json').write_text('[]')
  with self.assertRaises(ValueError):check(self.out,self.source)
if __name__=='__main__':unittest.main()
