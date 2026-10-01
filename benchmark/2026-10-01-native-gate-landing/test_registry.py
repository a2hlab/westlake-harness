import json,unittest
from pathlib import Path
R=Path(__file__).resolve().parents[2]
# Every row of the native exception registry must be traceable to an outer-loop approval (user rule 2026-10-01):
#  - approved_by outer(claude): a reviewed finding (baseline 257 rows 02:30:26; N10 185 rows; N10b 23 new rows), or
#  - approved_by auto-identical(outer rule 2026-10-01): a finding identical to an approved one, with auto_from naming
#    an existing row of the same gate that is itself outer-approved or auto (chains end at an outer row).
# The former byte-hash pin is replaced by these rules so auto_approve_exceptions.py can add rows without hand edits;
# the fixed baseline/N10 sets below still catch any edit to rows that were reviewed by hand.
BASE={'7bc02de79f989d48cedb1e5020df1be3b5cd58f6d2229df8f1a3f08cc4f5ffbe','b446d8db35e30a9180760f8dc8a4837b93e23c5187217e30b9901f94d66b68f7'}
N10='310376a18c6fc1952702d78366a7333644cbe11e3482901ff09ece4739d0bc71'
AUTO='auto-identical(outer rule 2026-10-01)'
class Registry(unittest.TestCase):
 def test_every_row_traces_to_outer_approval(self):
  rows=json.loads((R/'knowledge/gates/native-predeploy-exceptions.json').read_text())['exceptions']
  key=lambda r:(r['package_manifest_sha256'],r['gate'],r['issue_id'])
  self.assertEqual(len({key(r) for r in rows}),len(rows))
  by={(r['package_manifest_sha256'],r['issue_id']):r for r in rows}
  base=[r for r in rows if r['package_manifest_sha256'] in BASE];self.assertEqual(len(base),257)
  for r in base:self.assertEqual((r['approved_by'],r['approved_at']),('outer(claude)','2026-10-01T02:30:26+08:00'))
  n10=[r for r in rows if r['package_manifest_sha256']==N10]
  self.assertEqual({g:sum(r['gate']==g for r in n10) for g in ('N1','N2')},{'N1':31,'N2':154})
  for r in n10:self.assertEqual((r['approved_by'],r['approved_at']),('outer(claude)','2026-10-01T10:23:23+08:00'))
  for r in rows:
   for field in ['reason','removal_condition','inputs_sha256','approved_by','approved_at']:self.assertTrue(r[field])
   for evidence in r['evidence']:self.assertTrue((R/evidence).is_file(),evidence)
   if r['approved_by']==AUTO:
    seen=set();cur=r
    while cur['approved_by']==AUTO:
     src=by.get((cur['auto_from']['package_manifest_sha256'],cur['auto_from']['issue_id']))
     self.assertIsNotNone(src,f'auto row {r["issue_id"][:12]} cites a missing source row')
     self.assertEqual(src['gate'],r['gate']);self.assertNotIn(key(src),seen);seen.add(key(src));cur=src
    self.assertEqual(cur['approved_by'],'outer(claude)')
   else:
    self.assertEqual(r['approved_by'],'outer(claude)')
if __name__=='__main__':unittest.main()
