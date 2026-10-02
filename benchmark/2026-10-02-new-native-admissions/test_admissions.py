#!/usr/bin/env python3
"""Admission-branch metadata fixtures; actual pinned ELF exercised separately on Mac/VM."""
import copy,hashlib,json,sys,tempfile,unittest
from pathlib import Path
from unittest.mock import patch
H=Path(__file__).resolve().parent;R=H.parents[1]
sys.path.insert(0,str(R/'scripts/lab'))
import generation_static_checks as gate,u7_executor as executor
MEDIA='8fc0752dd561a62992268981164c5e75c87ceb802f93d6d0b958c23b54ddaa58'
TARGET='/system/android/lib64/libmediandk.so'

class Tests(unittest.TestCase):
 def setUp(self):
  self.tmp=tempfile.TemporaryDirectory();self.addCleanup(self.tmp.cleanup);self.repo=Path(self.tmp.name).resolve()
  self.root=self.repo/'candidate';self.base=self.repo/'base';self.root.mkdir();self.base.mkdir()
  self.manifest=self.root/'native/package.json';self.manifest.parent.mkdir();self.manifest.write_text('{"fixture":"native identity"}')
  self.manifest_sha=hashlib.sha256(self.manifest.read_bytes()).hexdigest()
  for root in [self.root,self.base]:(root/'bundle.json').write_text(json.dumps({'native':{'manifest':{'source':'native/package.json','sha256':self.manifest_sha}}}))
  (self.repo/'benchmark').mkdir();(self.repo/'benchmark/proof.json').write_text('{}')
  self.table=self.repo/'new-native-admissions.json';self.payload=self.root/'payload.so';self.payload.write_bytes(b'\x7fELF'+bytes(60))
  self.row={'target':TARGET,'sha256':MEDIA,'package_manifest_sha256':self.manifest_sha,'reason':'reviewed fixture','evidence':['benchmark/proof.json'],'added':'2026-10-02T20:00:00+08:00'}
 def write_table(self,rows=None):self.table.write_text(json.dumps({'schema':'westlake-new-native-admissions/v1','admissions':[self.row] if rows is None else rows}))
 def check(self,target=TARGET,sha=MEDIA,jar=False,previous=None,scan=None):
  row={'source':'payload.jar' if jar else 'payload.so','sha256':sha}
  def effective(root):return ({target:previous} if previous else {}) if root==self.base else {target:row}
  def member(root,entry):return gate.bundle.safe(root,entry['source']) if entry['source']=='native/package.json' else self.payload
  with patch.object(gate,'REPO',self.repo),patch.object(gate,'NEW_NATIVE_ADMISSIONS',self.table),patch.object(gate,'effective',side_effect=effective),patch.object(gate.bundle,'member',side_effect=member),patch.object(gate,'scan',side_effect=scan):return gate.check(self.root,self.base)
 def test_exact_and_variants(self):
  self.write_table();result=self.check();self.assertEqual(result['status'],'PASS');self.assertEqual(result['members'][0]['admission'],self.row)
  self.assertEqual(self.check(sha='0'*64)['status'],'REJECT')
  self.row['package_manifest_sha256']='1'*64;self.write_table();self.assertEqual(self.check()['status'],'REJECT')
  self.row['package_manifest_sha256']=self.manifest_sha;self.write_table();self.assertEqual(self.check(target='/system/android/lib64/libunreviewed.so')['status'],'REJECT')
 def test_missing_malformed_and_empty_fail_closed(self):
  self.assertEqual(self.check()['status'],'REJECT')
  self.table.write_text('{');self.assertEqual(self.check()['status'],'REJECT')
  self.table.write_text('[]');self.assertEqual(self.check()['status'],'REJECT')
  self.table.write_bytes(b'\xff');self.assertEqual(self.check()['status'],'REJECT')
  self.table.write_text('{"schema":"westlake-new-native-admissions/v1","admissions":[],"extra":NaN}');self.assertEqual(self.check()['status'],'REJECT')
  self.write_table([]);self.assertEqual(self.check()['status'],'REJECT')
 def test_evidence_and_schema_fail_closed(self):
  for field,value in [('evidence',['benchmark/missing.json']),('evidence',['benchmark']),('evidence',[]),('evidence',['../outside.json']),('sha256','8fc0752d'),('reason',''),('added','not-a-date')]:
   row=copy.deepcopy(self.row);row[field]=value;self.write_table([row]);result=self.check();self.assertEqual(result['status'],'REJECT',(field,value));self.assertIn('admission_error',result['members'][0])
  self.write_table([self.row,self.row]);self.assertEqual(self.check()['status'],'REJECT')
  self.table.write_text('{"schema":"westlake-new-native-admissions/v1","admissions":[],"admissions":[]}');self.assertEqual(self.check()['status'],'REJECT')
 def test_invalid_unrelated_row_invalidates_table(self):
  bad=copy.deepcopy(self.row);bad['target']='/system/android/lib64/libother.so';bad['evidence']=['benchmark/missing.json'];self.write_table([self.row,bad]);self.assertEqual(self.check()['status'],'REJECT')
 def test_jars_are_never_admitted(self):
  self.row['target']='/system/android/framework/new.jar';self.write_table();self.payload=self.root/'payload.jar';self.payload.write_bytes(b'JARfixture')
  self.assertEqual(self.check(target=self.row['target'],jar=True)['status'],'REJECT')
 def test_existing_open_delta_not_bypassed(self):
  self.write_table()
  site={'function':'f','callee':'dlopen','namespace':'default','path':'libnew.so','flags':2,'tail_call':False}
  def scan(path):return {'binaries':[{'sites':[] if scan.calls==0 else [site]}],'namespace_api_calls':{},'namespace_literals':[]}
  scan.calls=0
  def counted(path):r=scan(path);scan.calls+=1;return r
  result=self.check(previous={'source':'old.so','sha256':'0'*64},scan=counted);self.assertEqual(result['status'],'REJECT');self.assertEqual(result['members'][0]['status'],'REVIEW_REQUIRED')
 def test_policy_binding_changes_with_table(self):
  table=R/'knowledge/gates/new-native-admissions.json';seen=[]
  def sha(path):seen.append(Path(path));return 'table-state-a' if Path(path)==table else 'unchanged'
  with patch.object(executor.bundle,'sha',side_effect=sha):a=executor.policy_binding(self.root)
  self.assertIn(table,seen)
  with patch.object(executor.bundle,'sha',side_effect=lambda p:'table-state-b' if Path(p)==table else 'unchanged'):b=executor.policy_binding(self.root)
  self.assertNotEqual(a,b)
 def test_production_registry_not_written(self):
  production=R/'knowledge/gates/new-native-admissions.json';before=production.read_bytes();self.write_table();self.check();self.assertEqual(production.read_bytes(),before)
  self.assertEqual(json.loads((H/'delivered-registry.json').read_text())['admissions'],[])
  gate.read_new_native_admissions(production)
if __name__=='__main__':unittest.main()
