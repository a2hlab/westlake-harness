import datetime,json,sys,tempfile,unittest
from pathlib import Path
R=Path(__file__).resolve().parents[2];sys.path.insert(0,str(R/'scripts/lab'));import deployment_native_gate as g
SHA='3dd48299b599c2adebe8cc574649a31d84fabae53b77d5a7df704f4f380b993e'
class Grant(unittest.TestCase):
 def setUp(self):
  self.t=tempfile.TemporaryDirectory();self.p=Path(self.t.name)/'grant.json';now=datetime.datetime.now(datetime.timezone.utc)
  self.d=dict(schema_version=1,serial='board',package_manifest_sha256=SHA,status='active',issued_at=(now-datetime.timedelta(seconds=1)).isoformat(),expires_at=(now+datetime.timedelta(minutes=29)).isoformat(),exceptions=[dict(gate='N1' if i<31 else 'N2',package_manifest_sha256=SHA) for i in range(185)])
 def check(self,serial='board',sha=SHA):
  self.p.write_text(json.dumps(self.d));g.configure_experiment(self.p,serial);return g.experiment_entries(sha)
 def tearDown(self):g.configure_experiment(None,None);self.t.cleanup()
 def test_exact(self):self.assertEqual(len(self.check()[0]),185)
 def test_wrong_gate_count(self):
  self.d['exceptions'][0]['gate']='N2'
  with self.assertRaises(RuntimeError):self.check()
 def test_missing_row(self):
  self.d['exceptions'].pop()
  with self.assertRaises(RuntimeError):self.check()
 def test_expired(self):
  self.d["expires_at"]=(datetime.datetime.now(datetime.timezone.utc)-datetime.timedelta(seconds=1)).isoformat()
  with self.assertRaises(RuntimeError):self.check()
 def test_wrong_serial(self):
  with self.assertRaises(RuntimeError):self.check(serial='other')
 def test_revoked(self):
  self.d['status']='revoked'
  with self.assertRaises(RuntimeError):self.check()
 def test_rollback_after_revoke(self):
  self.d['status']='revoked';self.assertEqual(self.check(sha='7bc02de79f989d48cedb1e5020df1be3b5cd58f6d2229df8f1a3f08cc4f5ffbe'),([],None))
if __name__=='__main__':unittest.main()
