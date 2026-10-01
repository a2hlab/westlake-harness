import hashlib,json,sys,unittest
from pathlib import Path
H=Path(__file__).resolve().parent;R=H.parents[1]
def read(p):return json.loads(p.read_text())
class IdentityTests(unittest.TestCase):
 def test_baseline_repeat_and_frozen(self):
  host=read(H/'host-build-receipt.json');self.assertTrue(host['baseline']['sha256'].startswith('1d3b0881'));self.assertEqual(host['candidate']['sha256'],host['repeat']['sha256'])
  rt=read(H/'runtime-build-receipt.json')['variants'];self.assertTrue(rt['baseline']['sha256'].startswith('216b68fb'));self.assertEqual(rt['candidate']['sha256'],rt['repeat']['sha256'])
  for n in ['android_view_VelocityTracker.o','android_util_AssetManager_aosp.o']:self.assertEqual(rt['baseline']['objects'][n],rt['candidate']['objects'][n])
  changed={n for n,v in rt['baseline']['objects'].items() if rt['candidate']['objects'][n]!=v};self.assertEqual(changed,{'AndroidRuntime.o','android_graphics_Typeface.o','android_graphics_compat_shim.o'})
  self.assertTrue(read(H/'package.json')['provider_unchanged'])
class GateTests(unittest.TestCase):
 def test_explicit_unapproved_findings(self):
  g=read(H/'native-gate.json');self.assertFalse(g['errors']);self.assertEqual(g['status'],'REJECT');self.assertFalse(g['device_access']);self.assertEqual(sum(v['rejected'] for v in g['gates'].values()),160)
  p=read(H/'exception-proposal.json');self.assertEqual(len(p['exceptions']),160);self.assertTrue(all(e['approval_status']=='proposed' and e['package_manifest_sha256']==g['package_manifest_sha256'] for e in p['exceptions']))
class DeviceTests(unittest.TestCase):
 @unittest.skipUnless((H/'board61b/final-u8.json').is_file(),'Authorized device run not yet performed; no fabricated PASS')
 def test_restored_board_and_instance_evidence(self):
  j=read(H/'board61b/final-u8.json');self.assertEqual(j['status'],'rolled_back');self.assertEqual(j['identity_count'],312)
if __name__=='__main__':unittest.main()
