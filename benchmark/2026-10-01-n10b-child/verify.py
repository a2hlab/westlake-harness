import hashlib,json,subprocess,sys,unittest
from pathlib import Path
H=Path(__file__).resolve().parent;R=H.parents[1];sys.path.insert(0,str(R/'scripts/lab'));import u7_executor as u
read=lambda n:json.loads((H/n).read_text())
class OwnerTests(unittest.TestCase):
 def test_real_function_order_failure_and_handle_retention(self):subprocess.run([sys.executable,str(H/'test_owner_order.py')],check=True)
class IdentityTests(unittest.TestCase):
 def test_rebuilt_baseline_and_child_only_package(self):
  receipt=read('child-build-receipt.json');self.assertEqual(receipt['baseline']['sha256'],'d240f8d21693057af7c0e0dfd15d97f1f54a9ed0bf0aef246761d252d4b304c9');self.assertEqual(receipt['candidate']['sha256'],receipt['repeat']['sha256'])
  self.assertEqual({k for k,v in receipt['baseline']['objects'].items() if receipt['candidate']['objects'][k]!=v},{'sealed_child_provider_loader.o'})
  plan=u.prepare(R.parent/read('u8-package.json')['child']['bundle'],R.parent/'westlake-generation-u8-j9-t7e/native')
  self.assertEqual(len(plan['expected']),312);self.assertEqual({p for p,v in plan['baseline'].items() if plan['expected'][p]!=v},{'/system/lib64/appspawn/libwestlake_android_child.z.so'});self.assertEqual(plan['additions'],[]);self.assertFalse(plan['rollout_ready']);self.assertEqual(plan['expected']['/system/lib64/appspawn/libwestlake_android_child.z.so'],receipt['candidate']['sha256'])
class GateTests(unittest.TestCase):
 def test_no_borrowed_approval_or_weakened_gate(self):
  d=read('child-u8-native-gate.json');self.assertFalse(d['errors']);self.assertFalse(d['device_access']);self.assertEqual(d['status'],'REJECT');self.assertEqual({g:r['rejected'] for g,r in d['gates'].items()},{'N1':29,'N2':103});self.assertEqual(sum(r['excepted'] for r in d['gates'].values()),0)
  proposal=read('child-u8-exception-proposal.json');self.assertEqual(len(proposal['exceptions']),132)
  self.assertTrue(all(x['package_manifest_sha256']==d['package_manifest_sha256'] and x['inputs_sha256']==d['inputs_sha256'] and 'approved_by' not in x for x in proposal['exceptions']))
  self.assertIn('0 violation', (H/'child-u8-frozen.txt').read_text())
if __name__=='__main__':unittest.main()
