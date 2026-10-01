"""Offline evidence gates; no test infers board UI or DSO uniqueness."""
import hashlib,json,subprocess,sys,unittest
from pathlib import Path
H=Path(__file__).resolve().parent;R=H.parents[1];WS=R.parent;sys.path.insert(0,str(R/'scripts/lab'))
import u7_executor as u,generation_bundle as g
read=lambda name:json.loads((H/name).read_text());sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
class EmbossTests(unittest.TestCase):
 def test_real_source_baseline_repeat_and_frozen_objects(self):
  d=read('runtime-build-receipt.json');b=d['variants']['baseline'];c=d['variants']['candidate'];self.assertEqual(b['sha256'],'216b68fbb3a40b5ac7a90b726f6d8184fa7cdba848ccde56c809abd400a660df');self.assertEqual(c['sha256'],d['variants']['repeat']['sha256'])
  self.assertEqual({k for k,v in b['objects'].items() if c['objects'][k]!=v},{'AndroidRuntime.o','android_graphics_Typeface.o'})
  self.assertEqual(c['objects']['android_util_AssetManager_aosp.o'],b['objects']['android_util_AssetManager_aosp.o']);self.assertEqual(c['objects']['android_view_VelocityTracker.o'],b['objects']['android_view_VelocityTracker.o'])
  for name,row in read('emboss-sources.json')['files'].items():self.assertEqual(sha(H/('src/AndroidRuntime.cpp' if name=='AndroidRuntime.cpp' else 'src/emboss/'+name)),row['sha256'])
  backing=(H/'src/emboss/SkEmbossMaskFilter.cpp').read_text();self.assertIn('new SkEmbossMaskFilter',backing);self.assertIn('SkEmbossMask::Emboss(dst, light)',backing)
  receipt_commands='\n'.join((WS/d['out_directory']/v/'recipe.sh').read_text() for v in ['candidate','repeat']);self.assertIn('-Wl,-z,defs',receipt_commands);self.assertIn('libskia_canvaskit.z.so',receipt_commands)
  extra=json.loads((WS/d['out_directory']/'candidate/extra-commands.json').read_text());self.assertTrue(all('-DSKIA_OHOS' in argv for argv in extra));self.assertIn('0 violation',(H/'batch-u8-frozen.txt').read_text())
class RegistrationTests(unittest.TestCase):
 def test_actual_vm_and_cache_initialization(self):
  subprocess.run([sys.executable,str(H/'test_registration_init.py')],check=True)
  for name,digest in read('registration-sources.json')['files'].items():self.assertEqual(sha(H/'src'/name),digest)
  s=(H/'src/AndroidRuntime.cpp').read_text();self.assertLess(s.index('initialize_n10b_asset_offsets(env)'),s.index('register_n10b_Emboss(env)'))
  asset=(H/'src/asset-offsets-init.cpp').read_text();self.assertNotIn('RegisterNatives',asset.replace('without rerunning RegisterNatives',''))
class BatchTests(unittest.TestCase):
 def test_exact_u8_references_and_two_bytechanged_members(self):
  row=read('u8-package.json')['batch'];plan=u.prepare(WS/row['bundle'],WS/'westlake-generation-u8-j9-t7e/native');base=u.prepare(WS/'westlake-generation-u8-j9-t7e',WS/'westlake-generation-u8-j9-t7e/native')['expected'];self.assertEqual(plan['baseline'],base);self.assertEqual(len(plan['expected']),312)
  self.assertEqual({p for p in base if base[p]!=plan['expected'][p]},{'/system/lib64/appspawn/libwestlake_android_child.z.so','/system/android/lib64/liboh_android_runtime.so'});self.assertFalse(plan['rollout_ready']);self.assertFalse(plan['additions'])
  b=json.loads((WS/row['bundle']/'bundle.json').read_text());old=json.loads((WS/'westlake-generation-u8-j9-t7e/bundle.json').read_text());self.assertEqual(b['boot_group'],old['boot_group']);self.assertEqual(b['runtime_jar'],old['runtime_jar']);self.assertEqual(b['paired_build_receipt'],old['paired_build_receipt'])
class BatchGateTests(unittest.TestCase):
 def test_strict_refusal_exact_proposals_no_board_io(self):
  d=read('batch-u8-native-gate.json');self.assertFalse(d['errors']);self.assertFalse(d['device_access']);self.assertEqual(d['status'],'REJECT');self.assertEqual({k:v['rejected'] for k,v in d['gates'].items()},{'N1':51,'N2':103});self.assertEqual(sum(v['excepted'] for v in d['gates'].values()),0)
  p=read('batch-u8-exception-proposal.json');self.assertEqual(len(p['exceptions']),154);self.assertTrue(all(v['approval_status']=='proposed' and v['package_manifest_sha256']==d['package_manifest_sha256'] and v['inputs_sha256']==d['inputs_sha256'] for v in p['exceptions']))
  dry=read('batch-u8-production-dry-run.json');self.assertTrue(dry['image_gates']['G1']);self.assertTrue(dry['image_gates']['G2']);self.assertEqual(dry['production_preflight'],'refused');self.assertFalse(dry['deployable']);self.assertFalse(dry['device_io'])
if __name__=='__main__':unittest.main()
