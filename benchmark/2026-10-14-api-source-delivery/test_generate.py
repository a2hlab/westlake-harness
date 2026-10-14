"""Independent renderer gates. No mutable T4 review is consumed by these controls."""
import copy,csv,shutil,tempfile,unittest
from pathlib import Path
from unittest.mock import patch
import generate as g

class DeliveryTests(unittest.TestCase):
 @classmethod
 def setUpClass(cls):
  cls.master,cls.tree=g.master_tree()
  cls.script='sources/api-implementations/FZ-007-tagsoup/build.py'
  cls.entry={'path':cls.script,'sha256':g.sha(g.MAIN/cls.script)}
  cls.audit=g.audit_entry(cls.entry,cls.master,cls.tree)
  # Predicate-only fixture: never an actual API/source/build acceptance receipt.
  cls.row={'source_entry':[{'role':'implementation','exact_expected_match':True}],
    'source_revision':{'exact_binding':True},'build_command':{'argv':['python3',cls.script]},
    'build_outputs':{'entries':[{'unit_fixture':True}]},'build_dependencies':{'gaps':[]},
    'build_verification':{'evidence':[{'unit_fixture':True}],'gaps':[]},'gaps':[],
    'record_kind':'api_capability','implementation_status':'partial'}
  cls.base=g.read(g.resolve(g.read(g.HERE/'base-pin.json')['path']))['rows']
  cls.mapping=g.read(g.HERE/'inputs/mapping.json')
 def test_exact_main_master_entry_positive_control(self):
  self.assertTrue(self.audit['master_tracked_exact'])
  self.assertTrue(g.complete(self.row,{'entry':self.entry},[self.audit],self.audit))
 def test_publisher_is_task_repository_and_default_master(self):
  # Explicit release authority; intentionally independent of the stale local origin.
  self.assertEqual(g.PUBLISH_REPOSITORY,'a2hlab/westlake-harness')
  self.assertEqual(g.PUBLISH_BRANCH,'master')
  self.assertEqual(self.audit['master_url'],'https://github.com/a2hlab/westlake-harness/blob/master/'+self.script)
  g.validate_publisher_url(self.audit)
 def test_local_sha_and_blob_do_not_authorize_wrong_remote_repository(self):
  for prefix in ('https://github.com/A2OH/westlake-harness/blob/master/','https://github.com/a2hlab/westlake-harness/blob/main/'):
   bad=copy.deepcopy(self.audit);bad['master_url']=prefix+self.script
   self.assertEqual(bad['sha256'],self.audit['sha256'])
   self.assertEqual(bad['git_blob'],self.audit['git_blob'])
   self.assertTrue(bad['master_tracked_exact'])
   with self.assertRaisesRegex(ValueError,'publisher repository/branch/path ownership mismatch'):g.validate_publisher_url(bad)
 def test_physical_publication_rejects_wrong_owner_before_local_sha_checks(self):
  import publication_check
  with tempfile.TemporaryDirectory(prefix='publisher-negative-',dir=g.HERE) as tmp:
   view=Path(tmp)/'views';shutil.copytree(g.HERE/'views',view)
   data=g.read(view/'api-progress.json');audit=next(r for r in data['rows'] if r['source_master_audit'])['source_master_audit'][0]
   audit['master_url']='https://github.com/A2OH/westlake-harness/blob/master/'+audit['master_relative_path']
   g.write(view/'api-progress.json',data)
   with self.assertRaisesRegex(ValueError,'publisher repository/branch/path ownership mismatch'):publication_check.validate(view)
 def test_external_real_script_same_sha_is_rejected(self):
  with tempfile.TemporaryDirectory(prefix='external-build-',dir=g.HERE) as tmp:
   copied=Path(tmp)/'build.py';shutil.copy2(g.MAIN/self.script,copied)
   for name in (str(copied),'$WORKSPACES/'+copied.relative_to(g.WS).as_posix()):
    with self.subTest(path=name):
     entry={'path':name,'sha256':self.entry['sha256']};audit=g.audit_entry(entry,self.master,self.tree)
     self.assertEqual(audit['sha256'],self.audit['sha256'])
     self.assertTrue(audit['available']);self.assertFalse(audit['master_tracked_exact'])
     self.assertFalse(g.complete(self.row,{'entry':entry},[self.audit],audit))
 def test_absolute_main_script_is_not_repository_entry(self):
  entry={'path':str(g.MAIN/self.script),'sha256':self.entry['sha256']}
  audit=g.audit_entry(entry,self.master,self.tree)
  self.assertFalse(audit['master_tracked_exact'])
  self.assertFalse(g.complete(self.row,{'entry':entry},[self.audit],audit))
 def test_untracked_or_wrong_master_blob_is_rejected(self):
  audit=g.audit_entry(self.entry,self.master,{})
  self.assertFalse(g.complete(self.row,{'entry':self.entry},[self.audit],audit))
 def test_wrong_build_entry_sha_is_rejected(self):
  with self.assertRaisesRegex(ValueError,'entry SHA drift'):
   g.audit_entry({'path':self.script,'sha256':'0'*64},self.master,self.tree)
 def test_missing_build_entry_is_rejected(self):
  self.assertFalse(g.complete(self.row,{'entry':None},[self.audit],None))
  with self.assertRaisesRegex(ValueError,'unavailable'):
   g.audit_entry({'path':'sources/api-implementations/never-delivered.py','sha256':'0'*64},self.master,self.tree)
 def test_stub_and_unknown_source_cannot_be_complete(self):
  for mutation in ({'source_entry':[]},{'source_entry':[{'role':'stub','exact_expected_match':True}]},{'implementation_status':'stub'},{'gaps':['historical binding unknown']}):
   row=copy.deepcopy(self.row);row.update(mutation)
   self.assertFalse(g.complete(row,{'entry':self.entry},[self.audit],self.audit))
 def test_315_mapping_membership_and_grade(self):
  g.mapping_rows(self.base,self.mapping)
  for kind in ('missing','duplicate','grade'):
   with self.subTest(kind=kind):
    m=copy.deepcopy(self.mapping)
    if kind=='missing':m['rows'].pop()
    elif kind=='duplicate':m['rows'].append(copy.deepcopy(m['rows'][0]))
    else:m['rows'][0]['implementation_status']='invented-functional'
    with self.assertRaises(ValueError):g.mapping_rows(self.base,m)
 def test_incomplete_gate_creates_no_views(self):
  with tempfile.TemporaryDirectory(prefix='gate-',dir=g.HERE) as tmp:
   out=Path(tmp)/'views'
   with patch.object(g,'consume',return_value=([],{}, {'all315_complete':False})):
    with self.assertRaisesRegex(ValueError,'remains incomplete'):
     g.build(Path('predicate-fixture.json'),'0'*64,out,True)
   self.assertFalse(out.exists())
 def test_csv_null_preserved_and_tamper_rejected(self):
  row={'id':'unit-null-only','build_entry':None,'build_command':{'argv':None}}
  with tempfile.TemporaryDirectory(prefix='csv-',dir=g.HERE) as tmp:
   p=Path(tmp)/'table.csv'
   def emit(entry):
    with p.open('w',encoding='utf-8-sig',newline='') as stream:
     writer=csv.DictWriter(stream,fieldnames=row.keys());writer.writeheader()
     writer.writerow({'id':row['id'],'build_entry':entry,'build_command':'{"argv": null}'})
   emit('');g.check_csv(p,[row],tuple(row))
   emit('fabricated.py')
   with self.assertRaisesRegex(ValueError,'CSV field drift build_entry'):g.check_csv(p,[row],tuple(row))

if __name__=='__main__':unittest.main()
