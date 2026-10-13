"""Offline exact-source deltas and default read-only capture protocol."""
import ast,hashlib,json,os,runpy,sys,tempfile,unittest,contextlib,io
from pathlib import Path
from unittest.mock import patch
H=Path(__file__).resolve().parent
UP=H.parent
NEW='f28bd1b3d44e2944f77911c2ad71376869f7f3ebc6dcd8434dfea869f4056db0'
OLD='94718e0d0b617a0f9a860e0b50b879b0d7d4639f32e8230b1f90f8e26e2c1354'
def read(p):return json.loads(p.read_text())
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
class Delta(unittest.TestCase):
 def test_only_exact_artifact_table_worker_and_reference_pin_change(self):
  for board,src in [('61b',UP/'final-v2-candidate-r2'),('5cd',UP/'final-v2-rehearsal-5cd/provider')]:
   with self.subTest(board=board):
    dst=H/('board'+board)/'provider';old=src/'r4-reference';new=dst/'r4-reference'
    for n in ['installer.py','prepare.py','boat_identity.py','boat_provider.py','provider_common.py']:
     self.assertEqual((src/n).read_bytes(),(dst/n).read_bytes(),n)
    for n in ['recover.cfg','recover-v3-boat.sh','installer.py']:
     self.assertEqual((old/n).read_bytes(),(new/n).read_bytes(),n)
    self.assertEqual((new/'binds.tsv').read_text(),(old/'binds.tsv').read_text().replace(OLD,NEW))
    want=(old/'worker.sh').read_text().replace(OLD,NEW).replace('TABLE_SHA='+sha(old/'binds.tsv'),'TABLE_SHA='+sha(new/'binds.tsv'))
    self.assertEqual((new/'worker.sh').read_text(),want)
    self.assertIn('18763dd4b3a48aefaaf80c9f9630b849e282175eea8da04f7918d6d2cfa3fbae',want)
    self.assertEqual(want.count('no_parent'),(old/'worker.sh').read_text().count('no_parent'))
    self.assertIn('INIT_MOUNT_NS_READ',want)
    a=read(old/'plan.disabled.json');b=read(new/'plan.disabled.json')
    for row in a['binds']:
     if row['sha256']==OLD:row['sha256']=NEW
    for row in a['members']:
     if row['sha256']==OLD:row.update(sha256=NEW,source='$WORKSPACES/westlake-inputs/generations/boat-v2-runtime-f28bd1b3-20261013/liboh_android_runtime.so')
     if row['source'].startswith('$PACKAGE/'):row['sha256']=sha(new/Path(row['source']).name)
    self.assertEqual(a,b);self.assertEqual((len(b['members']),len(b['binds'])),(11,7))
 def test_entry_only_sibling_executor_path_change(self):
  for board,src in [('61b',UP/'final-v2-entry/restore_entry.py'),('5cd',UP/'final-v2-rehearsal-5cd/entry/restore_entry.py')]:
   wanted=src.read_text().replace("HERE.parent/'final-v2-candidate-r2/installer.py'","HERE.parent/'provider/installer.py'")
   self.assertEqual((H/('board'+board)/'entry/restore_entry.py').read_text(),wanted)
 def test_selfcheck_only_exact_provider_freeze_pins_change(self):
  old=(UP/'final-v2-selfcheck/compile_selfcheck.py').read_text()
  for board,oldsha in [('61b','7b32b7a6d4fdaaee777365272850bedf7ca55ab3ecf3effda6f27876634e137d'),('5cd','ee198467407a36006f9a26f824ddd2a5237551e079de5545db4bd98a63322543')]:old=old.replace(oldsha,sha(H/('board'+board)/'provider-freeze.json'))
  self.assertEqual((H/'selfcheck/compile_selfcheck.py').read_text(),old)
  for n in ['selfcheck_entry.py','source-pins.json']:self.assertEqual((H/'selfcheck'/n).read_bytes(),(UP/'final-v2-selfcheck'/n).read_bytes())
 def test_readonly_capture_default_has_no_transport_or_output(self):
  with tempfile.TemporaryDirectory() as tmp:
   out=Path(tmp)/'fresh'
   with patch.object(sys,'argv',['capture','--out',str(out),'--expected-boot','362f2212-1a42-4c1a-8487-0dddb091c74b']),patch('subprocess.run',side_effect=AssertionError('device forbidden')),contextlib.redirect_stdout(io.StringIO()) as stdout,self.assertRaises(SystemExit) as ex:
    runpy.run_path(str(H/'capture5cd/capture_readonly.py'),run_name='__main__')
   self.assertEqual(ex.exception.code,0);self.assertFalse(out.exists());self.assertEqual(json.loads(stdout.getvalue())['file_targets'],497)
if __name__=='__main__':unittest.main(verbosity=2)
