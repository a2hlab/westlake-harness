import hashlib,json,tempfile,unittest,importlib.util
from pathlib import Path
H=Path(__file__).resolve().parent
read=lambda p:json.loads(p.read_text())
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
class Tests(unittest.TestCase):
 def test_inputs(self):
  p=H.parent/'2026-10-01-icon-invalid-fallback';d=read(H/'permission-preserving-build-receipt.json')
  self.assertEqual(d['tools']['patch_sha256'],sha(p/'apk_installer.cpp.patch'))
  self.assertEqual(d['baseline']['source_sha256'],'45438280ccc14d676c32e0d9596e0470aa618ce2e4ee08ed43b43f7a8ad92d5a')
  self.assertIn('MapApkNetworkPermissions', (H/'preserve-network-background.patch').read_text())
 def test_build(self):
  d=read(H/'permission-preserving-build-receipt.json');self.assertEqual(d['candidate']['sha256'],d['repeat']['sha256'])
  e=read(H/'permission-preserving-elf.json')
  for row in e['comparisons'].values():self.assertTrue(row['needed_equal']);self.assertTrue(row['soname_equal']);self.assertEqual(row['removed_exports'],[]);self.assertEqual(row['added_exports'],[])
 def test_package(self):
  d=read(H/'package.json');self.assertFalse(d['rollout_ready']);self.assertFalse(d['device_io']);self.assertEqual(d['identity_count'],312);self.assertTrue(d['runtime_host_sha256'].startswith('1d3b0881'))
  self.assertFalse(d['installer']['deployable']);self.assertTrue(d['installer']['activation']['foundation_restart_required'])
if __name__=='__main__':unittest.main()
