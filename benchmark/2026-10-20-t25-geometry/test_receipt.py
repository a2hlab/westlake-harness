import json
import os
import shutil
import tempfile
import unittest
from pathlib import Path
from check_receipt import validate
P=Path(__file__).resolve().parent
class ReceiptTests(unittest.TestCase):
 def test_actual_and_negative(self):
  source=Path(os.environ.get('T25_BUILD_OUT',str(P/'.private/production-02')))
  self.assertEqual(validate(source)['status'],'VALID_OFFLINE_BUILD')
  for case in ['missing_stderr','nonzero_rc','source_snapshot','artifact','old77','version','frozen_command']:
   with self.subTest(case=case),tempfile.TemporaryDirectory(dir=P/'.private',prefix='receipt-negative-') as t:
    q=Path(t)/'build';shutil.copytree(source,q);r=json.loads((q/'receipt.json').read_text())
    if case=='missing_stderr':(q/'raw/20-compile-geometry.stderr').unlink()
    if case=='nonzero_rc':(q/'raw/20-compile-geometry.rc').write_text('1\n')
    if case=='source_snapshot':(q/'source-snapshot/geometry.c').write_text('changed')
    if case=='artifact':(q/'candidate.so').write_bytes(b'changed')
    if case=='old77':r['abi']['old_exports']=76
    if case=='version':r['abi']['added'][0][3]='ANativeWindow_setBuffersGeometry'
    if case=='frozen_command':r['commands']=r['commands'][1:]
    (q/'receipt.json').write_text(json.dumps(r))
    with self.assertRaises((AssertionError,OSError)):validate(q)
if __name__=='__main__':unittest.main()
