import hashlib,json,unittest
from pathlib import Path
R=Path(__file__).resolve().parents[2]
class Registry(unittest.TestCase):
 def test_exact_approved_bytes_and_evidence(self):
  p=R/'knowledge/gates/native-predeploy-exceptions.json'
  self.assertEqual(hashlib.sha256(p.read_bytes()).hexdigest(),'d40f3b9d44d248fd6b7b665aa90b78bd35464db60e42ea90c275b1ce85d7a9da')
  rows=json.loads(p.read_text())['exceptions'];self.assertEqual(len(rows),257)
  self.assertEqual({r['package_manifest_sha256'] for r in rows},{'7bc02de79f989d48cedb1e5020df1be3b5cd58f6d2229df8f1a3f08cc4f5ffbe','b446d8db35e30a9180760f8dc8a4837b93e23c5187217e30b9901f94d66b68f7'})
  self.assertEqual(len({(r['package_manifest_sha256'],r['gate'],r['issue_id']) for r in rows}),257)
  for row in rows:
   self.assertEqual(row['approved_at'],'2026-10-01T02:30:26+08:00')
   for field in ['reason','removal_condition','inputs_sha256','approved_by']:self.assertTrue(row[field])
   for evidence in row['evidence']:self.assertTrue((R/evidence).is_file(),evidence)
if __name__=='__main__':unittest.main()
