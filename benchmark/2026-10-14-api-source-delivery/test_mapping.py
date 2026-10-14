#!/usr/bin/env python3
"""Offline boundary tests on the emitted315-row consumer contract."""
import copy,hashlib,json,re,unittest,os
from pathlib import Path
HERE=Path(__file__).resolve().parent
FIELDS=('source_entry','source_revision','build_recipe','build_command','build_dependencies','build_outputs','build_verification')
H=re.compile(r'[0-9a-f]{64}\Z')
def validate(d,recipes,recipe_sha):
 rows=d['rows'];assert len(rows)==315 and len({r['id'] for r in rows})==315
 index={r['id']:r for r in recipes['recipes']};assert len(index)==len(recipes['recipes'])
 for r in rows:
  assert all(k in r for k in FIELDS);assert r['original_grades_unchanged']
  assert r['build_recipe']['sha256']==recipe_sha
  recipe=index[r['build_recipe']['id']]
  if recipe['entry']:assert Path(recipe['entry']['path']).suffix in ['.py','.sh']
  for field,key in [('build_command','command'),('build_dependencies','dependencies'),('build_outputs','outputs'),('build_verification','verification')]:assert r[field]==recipe[key]
  for e in r['source_entry']:
   assert H.fullmatch(e['sha256']) and re.fullmatch('[0-9a-f]{40}',e['git_blob'])
   assert e['role'] not in ['report','index']
   if e['role']=='permission_resource':assert Path(e['path']).suffix=='.json'
   else:assert Path(e['path']).suffix in ['.c','.cpp','.cc','.h','.hpp','.inc','.rs','.java','.smali','.py','.js']
   if e['master_tracked']:assert e['master_blob']==e['git_blob']
   if e['expected_sha256']:assert e['sha256']==e['expected_sha256']
  if not r['source_entry'] or r['implementation_status']=='stub' or r['record_kind']=='supporting_knowledge':assert not r['complete_delivery_claim']
  if r['complete_delivery_claim']:
   assert all(e['master_tracked'] and e['role']=='implementation' for e in r['source_entry'])
   assert r['source_revision']['exact_binding'] and r['build_command']['argv']
   assert not r['gaps'] and not r['build_dependencies']['gaps'] and not r['build_verification']['gaps']
 return True
class Mapping(unittest.TestCase):
 @classmethod
 def setUpClass(cls):
  cls.root=Path(os.environ.get('T5_MAPPING_DIR',str(HERE/'release')));cls.d=json.loads((cls.root/'source-build-mapping.json').read_text());p=cls.root/'recipes/recipes.json';cls.rec=json.loads(p.read_text());cls.sha=hashlib.sha256(p.read_bytes()).hexdigest()
 def test_complete_membership_and_recipe_links(self):self.assertTrue(validate(self.d,self.rec,self.sha))
 def test_report_is_not_implementation(self):
  d=copy.deepcopy(self.d);d['rows'][0]['source_entry'][0]['path']='benchmark/report/README.md'
  with self.assertRaises(AssertionError):validate(d,self.rec,self.sha)
 def test_missing_not_complete(self):
  d=copy.deepcopy(self.d);r=next(r for r in d['rows'] if not r['source_entry']);r['complete_delivery_claim']=True
  with self.assertRaises(AssertionError):validate(d,self.rec,self.sha)
 def test_stub_not_complete(self):
  d=copy.deepcopy(self.d);r=next(r for r in d['rows'] if r['implementation_status']=='stub');r['complete_delivery_claim']=True
  with self.assertRaises(AssertionError):validate(d,self.rec,self.sha)
 def test_actual_source_sha_drift_rejected(self):
  d=copy.deepcopy(self.d);r=next(r for r in d['rows'] if any(e['expected_sha256'] for e in r['source_entry']));e=next(e for e in r['source_entry'] if e['expected_sha256']);e['sha256']='0'*64
  with self.assertRaises(AssertionError):validate(d,self.rec,self.sha)
 def test_tagsoup_is_master_real_code_not_stub(self):
  rows={r['id']:r for r in self.d['rows']}
  for key in ['JAVA-001','REG-007']:
   r=rows[key];self.assertEqual(len(r['source_entry']),15);self.assertTrue(all(e['master_tracked'] for e in r['source_entry']));self.assertTrue(r['build_verification']['historical_dex_equal']);self.assertFalse(r['build_verification']['historical_jar_equal'])
 def test_receipt_not_direct_build_entry(self):
  rec=copy.deepcopy(self.rec);rec['recipes'][0]['entry']={'path':'some/build-receipt.json','sha256':'0'*64}
  with self.assertRaises(AssertionError):validate(self.d,rec,self.sha)
 def test_fulljar_keeps_strict_mismatch(self):
  rows={r['id']:r for r in self.d['rows']}
  for id in ['REG-004','REG-006']:
   v=rows[id]['build_verification'];self.assertEqual(v['producer_rc'],0);self.assertEqual(v['wrapper_rc'],2);self.assertFalse(v['historical_dex_equal']);self.assertFalse(v['historical_jar_equal'])
 def test_later_java_is_new_class_build_only(self):
  rows={r['id']:r for r in self.d['rows']}
  v=rows['JAVA-096']['build_verification'];self.assertEqual(v['status'],'NEW_ADAPTER_JAVA_BUILD_PASS');self.assertEqual(v['exit_code'],0);self.assertFalse(v['historical_r84_r89_output_equivalent']);self.assertFalse(v['deployable_runtime_jar'])
 def test_js_is_code_json_requires_resource_role(self):
  d=copy.deepcopy(self.d);e=d['rows'][0]['source_entry'][0];e['path']='sources/test/EntryAbility.js';validate(d,self.rec,self.sha)
  e['path']='sources/test/module.json'
  with self.assertRaises(AssertionError):validate(d,self.rec,self.sha)
  e['role']='permission_resource';validate(d,self.rec,self.sha)
 def test_native_actual_member_and_partial_limits(self):
  rows={r['id']:r for r in self.d['rows']}
  self.assertEqual(rows['JAVA-104']['source_entry'][0]['symbol'],'wl_getSpace0')
  self.assertEqual(rows['NATIVE-148']['source_entry'][0]['role'],'stub')
  self.assertEqual(rows['NATIVE-153']['source_entry'][0]['role'],'stub')
 def test_whole_source_delivery_not_fabricated(self):self.assertFalse(self.d['summary']['full315_source_delivery'])
if __name__=='__main__':unittest.main()
