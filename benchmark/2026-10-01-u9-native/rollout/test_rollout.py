import hashlib,importlib.util,json,subprocess,sys,tempfile,unittest
from pathlib import Path
from unittest import mock
H=Path(__file__).resolve().parent;R=H.parents[2];sys.path.insert(0,str(R/'scripts/lab'))
import lab_paths,board_run,activation_smoke as smoke
class Tests(unittest.TestCase):
 def test_plans_and_markers(self):
  spec=json.loads((H/'smoke.json').read_text())
  ids={f['id'] for f in spec['fixes']}
  self.assertTrue({'N10b-JNI-OWNER','N10b-TYPEFACE-VM','N10b-NDK-ASSET-OFFSETS','N10b-EMBOSS','J10d-THEME','J10e-DELEGATE','J10e-COOKIE','J10f-SETTINGS','J10g-SWC','J10g-PKG'}<=ids)
  self.assertNotIn('U9-INVALID-ICON',ids)
  self.assertFalse((lab_paths.workspaces()/json.loads((H/'package.json').read_text())['bundle']/'installer').exists())
  self.assertEqual(spec['probe']['files']['/system/lib64/libapk_installer.so'],'7048c7c50a828fc744b5f06e4e9ec50ac317a2272f33789249fc63e43a655a18')
  self.assertEqual(spec['probe']['expect_copies'],{'liboh_adapter_bridge.so':2,'liboh_android_runtime.so':2})
  for name in ['5ea','5cd','61b']:
   p=json.loads((H/f'plan-{name}.json').read_text());self.assertIsNone(board_run.precheck_problem(p['offline_precheck']))
 def test_transaction_isolation(self):
  with tempfile.TemporaryDirectory() as td:
   kit=Path(td);libs={}
   for name in ['libbms.z.so','libapk_installer.so']:
    data=('offline fixture '+name).encode();(kit/name).write_bytes(data);libs[name]=hashlib.sha256(data).hexdigest()
   (kit/'manifest.json').write_text(json.dumps({'candidate':libs,'baseline':libs}))
   args=[sys.executable,str(R/'scripts/lab/swap_installer.py'),'dry-run','--serial','61b0657200000000000000000324012c','--kit',str(kit)]
   old=json.loads(subprocess.check_output(args,text=True));new=json.loads(subprocess.check_output(args+['--transaction-name','u9-33558acd'],text=True))
   self.assertEqual(old['backup'],'/data/local/tmp/installer-background-launcher/backup')
   self.assertEqual(new['backup'],'/data/local/tmp/installer-u9-33558acd/backup')
   self.assertNotEqual(old['state'],new['state']);self.assertFalse(new['device_io'])
   self.assertNotEqual(subprocess.run(args+['--transaction-name','../unsafe'],capture_output=True).returncode,0)
 def test_owner_counts_remain_strict(self):
  spec={'probe':{'expect_copies':{'liboh_adapter_bridge.so':2}}}
  ok,_=smoke.evaluate(spec,{}, {},{'copies':{'liboh_adapter_bridge.so':['a@1','a@2']},'view':{}});self.assertTrue(ok)
  ok,_=smoke.evaluate(spec,{}, {},{'copies':{'liboh_adapter_bridge.so':['a@1','a@2','a@3']},'view':{}});self.assertFalse(ok)
 def hook(self):
  spec=importlib.util.spec_from_file_location('u9_rollout_hook',H/'native_window.py')
  module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module);return module
 def test_failed_rollback_keeps_lock(self):
  module=self.hook()
  with tempfile.TemporaryDirectory() as td:
   root=Path(td);(root/'transaction').mkdir();(root/'transaction/journal.json').write_text('{}')
   with mock.patch.object(module,'vm',return_value=2) as rollback, mock.patch.object(module.subprocess,'run') as verify:
    self.assertEqual(module.finish('61b0657200000000000000000324012c',root),2)
    rollback.assert_called_once();verify.assert_not_called()
 def test_missing_baseline_child_is_rejected_with_diff(self):
  module=self.hook();child='/system/lib64/westlake/libwestlake_android_child.so'
  baseline={child:'a'*64,'/system/android/framework/oh-adapter-runtime.jar':'b'*64}
  io=mock.Mock();io.boot='unchanged';io.snapshot.return_value=({p:v for p,v in baseline.items() if p!=child},[child]);io.hashes.return_value=module.service_hashes()
  with tempfile.TemporaryDirectory() as td:
   root=Path(td)
   with mock.patch.object(module.u,'prepare',return_value={'baseline':baseline,'reference_paths':{}}), mock.patch.object(module.u,'DeviceIO',return_value=io), mock.patch.object(module.u,'fingerprints',return_value={}):
    with self.assertRaises(AssertionError):module.read_baseline('61b0657200000000000000000324012c',root)
   receipt=json.loads((root/'before.json').read_text());self.assertIn(child,receipt['diff']);self.assertIn(child,receipt['absent'])
if __name__=='__main__':unittest.main()
