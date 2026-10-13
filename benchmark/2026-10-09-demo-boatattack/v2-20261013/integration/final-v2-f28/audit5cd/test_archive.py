import importlib.util,json,os,shutil,subprocess,tempfile,unittest
from pathlib import Path
HERE=Path(__file__).resolve().parent
spec=importlib.util.spec_from_file_location('archive_prepare',HERE/'prepare_archive_postboot.py');m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)
WS=Path(os.environ.get('WORKSPACES',Path(__file__).resolve().parents[7]));os.environ.setdefault('WORKSPACES',str(WS))
MAIN=WS/'westlake-harness';OUTER=MAIN/'benchmark/2026-10-09-demo-boatattack/v2-20261013/outer'
class TestArchive(unittest.TestCase):
 def build(self,out,fresh=None):
  return m.build(OUTER/'r5-experiment-main-r4/run',out,OUTER/'final-v2-5cd-readonly/capture.json',fresh or OUTER/'final-v2-5cd-owned-audit-readonly')
 def test_actual_generation_and_receipt_boot(self):
  with tempfile.TemporaryDirectory() as td:
   out=Path(td)/'prepared';v=self.build(out);self.assertEqual((len(v['files']),len(v['directories'])),(5,2))
   for name in ('archive.sh','remote.sh'):
    s=(out/name).read_text();subprocess.run(['bash','-n',str(out/name)],check=True)
    receipt=[line for line in s.splitlines() if 'ARCHIVED_VERIFIED' in line];self.assertEqual(len(receipt),1);self.assertIn(v['boot_id'],receipt[0]);self.assertNotIn('8d0f7543',receipt[0])
   remote=(out/'remote.sh').read_text();self.assertNotIn('awk',remote);self.assertEqual(remote.count('mv "$ROOT" "$ARCHIVE"'),1)
   self.assertNotIn('rm ',remote)
   got=subprocess.run(['bash',str(out/'archive.sh')],capture_output=True,text=True,check=True);self.assertEqual(json.loads(got.stdout)['boot_id'],v['boot_id'])
 def bad(self,old,new):
  with tempfile.TemporaryDirectory(dir=HERE) as td:
   fresh=Path(td)/'fresh';shutil.copytree(OUTER/'final-v2-5cd-owned-audit-readonly',fresh)
   p=fresh/'stdout.txt';s=p.read_text();self.assertIn(old,s);p.write_text(s.replace(old,new,1));out=Path(td)/'out'
   with self.assertRaises(ValueError):self.build(out,fresh)
   self.assertFalse(out.exists())
 def test_foreign_inode(self):self.bad('66352:156273','66352:999999')
 def test_wrong_boot(self):self.bad('362f2212-1a42-4c1a-8487-0dddb091c74b','00000000-0000-0000-0000-000000000000')
 def test_remote_failure(self):self.bad('AUDIT_READ_RC=0','AUDIT_READ_RC=1')
 def test_extra_member(self):self.bad('IDENTITIES\n','/data/westlake-demo/u13/boat-v2-20261013-r4/foreign\nIDENTITIES\n')
if __name__=='__main__':unittest.main()
