#!/usr/bin/env python3
"""Portable audit-schema checks; no network, build, device or producer-tree access."""
import copy,json,re,unittest
from pathlib import Path
HERE=Path(__file__).resolve().parent
HEX=re.compile(r'[0-9a-f]{64}\Z')
def validate(doc):
 rows=doc['targets'];assert len(rows)==824 and len({r['target'] for r in rows})==824
 for r in rows:
  assert HEX.fullmatch(r['sha256'])
  assert r['source_build_status'] and r['restore_status']
  if r['restore_status']=='EXACT_LOCAL_BYTES_AND_ARCHIVE_MEMBER_VERIFIED':
   assert r['artifact_source']['sha256']==r['sha256'] and r['archive_members']
  if r['source_build_status'] in ['EXISTING_COLD_SOURCE_BUILD_VERIFIED','EXISTING_TWO_SOURCE_BUILDS_EQUAL']:
   assert all(r.get(k) for k in ['source_snapshot','toolchain','build_scripts','original_rc0_logs'])
   logs=r['original_rc0_logs'];logs=logs if isinstance(logs,list) else [logs]
   assert all(x['rc']==0 and x.get('kind')!='PATCH_REPLAY_NOT_BUILD' for x in logs)
  if isinstance(r['original_rc0_logs'],dict) and r['original_rc0_logs'].get('kind')=='PATCH_REPLAY_NOT_BUILD':
   assert r['source_build_status']=='BLOCKED_EXACT_PARENT_SOURCE_BUILD_UNKNOWN'
 return True
class Audit(unittest.TestCase):
 @classmethod
 def setUpClass(cls):cls.doc=json.loads((HERE/'release-audit/artifact-inventory.json').read_text())
 def test_signed_inventory(self):self.assertTrue(validate(self.doc))
 def test_all_restore_not_all_source(self):
  d=json.loads((HERE/'release-audit/results.json').read_text());self.assertEqual(d['restore_status_counts'],{'EXACT_LOCAL_BYTES_AND_ARCHIVE_MEMBER_VERIFIED':824});self.assertFalse(d['whole_stack_source_reproducible']);self.assertEqual(d['device_calls'],0);self.assertEqual(d['builds_executed'],0)
 def test_patch_cannot_be_build(self):
  d=copy.deepcopy(self.doc);r=next(r for r in d['targets'] if r['sha256'].startswith('adc125'));r['source_build_status']='EXISTING_COLD_SOURCE_BUILD_VERIFIED'
  with self.assertRaises(AssertionError):validate(d)
 def test_missing_archive_ref_rejected(self):
  d=copy.deepcopy(self.doc);d['targets'][0]['archive_members']=[]
  with self.assertRaises(AssertionError):validate(d)
 def test_failed_build_not_certified(self):
  d=copy.deepcopy(self.doc);r=next(r for r in d['targets'] if r['sha256'].startswith('f28bd'));r['original_rc0_logs']['rc']=1
  with self.assertRaises(AssertionError):validate(d)
 def test_remote_evidence(self):
  a=json.loads((HERE/'release-audit/archive-coverage.json').read_text());self.assertEqual(len(a['fresh_remote']['archives']),8);r=next(r for r in a['archives'] if r['id']=='final-four-object-supplement');self.assertEqual(r['verified_target_members'],4);self.assertEqual(r['remote_status'],'OUTER_REMOTE_SHA_VERIFIED')
if __name__=='__main__':unittest.main()
