import datetime,json,sys,tempfile,unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2];sys.path.insert(0,str(ROOT/'scripts/lab'));import deployment_native_gate as g
class Window(unittest.TestCase):
 def setUp(self):
  self.tmp=tempfile.TemporaryDirectory();self.path=Path(self.tmp.name)/'window.json';self.now=datetime.datetime.now(datetime.timezone.utc)
  self.d=dict(schema_version=1,serial='board',package_manifest_sha256='a'*64,status='active',issued_at=(self.now-datetime.timedelta(seconds=1)).isoformat(),expires_at=(self.now+datetime.timedelta(minutes=29)).isoformat(),exceptions=[dict(gate='N2',package_manifest_sha256='a'*64) for _ in range(57)])
 def runcheck(self,serial='board',package='a'*64):
  self.path.write_text(json.dumps(self.d));g.configure_experiment(self.path,serial);return g.experiment_entries(package)
 def tearDown(self):g.configure_experiment(None,None);self.tmp.cleanup()
 def test_active(self):self.assertEqual(len(self.runcheck()[0]),57)
 def test_wrong_board(self):
  with self.assertRaises(RuntimeError):self.runcheck('other')
 def test_expired(self):
  self.d['expires_at']=(self.now-datetime.timedelta(milliseconds=1)).isoformat()
  with self.assertRaises(RuntimeError):self.runcheck()
 def test_revoked(self):
  self.d['status']='revoked'
  with self.assertRaises(RuntimeError):self.runcheck()
 def test_overlong(self):
  self.d['expires_at']=(self.now+datetime.timedelta(minutes=31)).isoformat()
  with self.assertRaises(RuntimeError):self.runcheck()
 def test_baseline_rollback_independent(self):
  self.d['status']='revoked';self.assertEqual(self.runcheck(package='b'*64),([],None))
if __name__=='__main__':unittest.main()
