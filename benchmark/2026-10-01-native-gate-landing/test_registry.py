import hashlib,json,unittest
from pathlib import Path
R=Path(__file__).resolve().parents[2]
# Baseline: 257 rows approved 2026-10-01T02:30:26 for the U5/U7 native manifests (7bc02de7, b446d8db).
# Added 2026-10-01 10:24:37 (board ACK(95)): 185 rows for the N10 manifest 310376a1 (N1 31 + N2 154, identical
# to N8), scope N10 single-variable window + U8. Any further change to the registry must update this pin.
BASE={'7bc02de79f989d48cedb1e5020df1be3b5cd58f6d2229df8f1a3f08cc4f5ffbe','b446d8db35e30a9180760f8dc8a4837b93e23c5187217e30b9901f94d66b68f7'}
N10='310376a18c6fc1952702d78366a7333644cbe11e3482901ff09ece4739d0bc71'
class Registry(unittest.TestCase):
 def test_exact_approved_bytes_and_evidence(self):
  p=R/'knowledge/gates/native-predeploy-exceptions.json'
  self.assertEqual(hashlib.sha256(p.read_bytes()).hexdigest(),'0fbf06f9134c0d0fc7f2e1f53a9d5689a908437b4b65add69aadc18bfe14a2bb')
  rows=json.loads(p.read_text())['exceptions'];self.assertEqual(len(rows),442)
  self.assertEqual({r['package_manifest_sha256'] for r in rows},BASE|{N10})
  self.assertEqual(len({(r['package_manifest_sha256'],r['gate'],r['issue_id']) for r in rows}),442)
  base=[r for r in rows if r['package_manifest_sha256'] in BASE];self.assertEqual(len(base),257)
  for row in base:self.assertEqual(row['approved_at'],'2026-10-01T02:30:26+08:00')
  n10=[r for r in rows if r['package_manifest_sha256']==N10]
  self.assertEqual({g:sum(r['gate']==g for r in n10) for g in ('N1','N2')},{'N1':31,'N2':154})
  for row in n10:self.assertEqual(row['approved_at'],'2026-10-01T10:23:23+08:00')
  for row in rows:
   for field in ['reason','removal_condition','inputs_sha256','approved_by']:self.assertTrue(row[field])
   for evidence in row['evidence']:self.assertTrue((R/evidence).is_file(),evidence)
if __name__=='__main__':unittest.main()
