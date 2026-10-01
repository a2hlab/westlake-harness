"""Reject baseline drift while leaving an actionable SHA receipt."""
import importlib.util,json,tempfile,unittest
from pathlib import Path

class BaselineReceiptTests(unittest.TestCase):
 def test_mismatch_is_recorded_before_assertion(self):
  spec=importlib.util.spec_from_file_location('window',Path(__file__).with_name('window-r2.py'))
  w=importlib.util.module_from_spec(spec);spec.loader.exec_module(w)
  with tempfile.TemporaryDirectory() as tmp:
   t=Path(tmp);w.H=t;w.ROOT=t/'board';(t/'window-r2').mkdir()
   baseline={'/a':'1'*64,'/b':'2'*64}
   (t/'window-r2/approved-production-dry-run.json').write_text(json.dumps({'baseline':baseline,'reference_paths':{}}))
   class IO:
    boot='test';values={'/a':'1'*64,'/b':'3'*64}
    def __init__(self,*args):pass
    def snapshot(self,paths):return self.values,[]
   old_io,old_fp=w.u.DeviceIO,w.u.fingerprints
   try:
    w.u.DeviceIO=IO;w.u.fingerprints=lambda got,paths:{}
    with self.assertRaises(AssertionError):w.read_baseline()
    row=json.loads((w.ROOT/'before.json').read_text())
    self.assertFalse(row['matches'])
    self.assertEqual(row['diff'],{'/b':{'expected':'2'*64,'actual':'3'*64}})
    IO.values=baseline;w.read_baseline()
    self.assertTrue(json.loads((w.ROOT/'before.json').read_text())['matches'])
   finally:w.u.DeviceIO,w.u.fingerprints=old_io,old_fp
if __name__=='__main__':unittest.main()
