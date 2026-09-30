#!/usr/bin/env python3
import copy,csv,json,unittest
from pathlib import Path
import engine
from audit_run import projected_hashes
from score import add_baselines
H=Path(__file__).resolve().parent

class ScoreTests(unittest.TestCase):
 def fixture(self):
  profile=json.loads((H/'profiles.json').read_text())['r17p']
  p={'key':'fixture','apk_sha256':'a'*64,'forecast':'亮','progress_checkpoint':'surface checkpoint','prior_wall':'EGL wall','prior_exposure':'unseen'}
  obs={'key':'fixture','board':profile['boards'][0],'apk_sha256':'a'*64,**{k:profile[k] for k in ['package_sha256','jar_sha256','installer_sha256','native_overrides']},
       'grant_verified':True,'select_launcher_verified':True,'batch_sidecars_enabled':True,'runtime_audit_verified':True,'clicked_at':'2026-10-01T00:00:01Z','profile_evidence':'facts.txt','lit':'yes','screenshot_evidence':'verified-shot.jpeg'}
  return profile,p,obs
 def test_rejections_and_survival(self):
  profile,p,o=self.fixture();stamp='2026-10-01T00:00:00Z'
  good=engine.score([p],[o],profile,stamp);self.assertTrue(good['rows'][0]['exact_correct'])
  for k,value in [('jar_sha256','0'*64),('native_overrides',{}),('apk_sha256','0'*64),('clicked_at',stamp),('runtime_audit_verified',False),('grant_verified',False)]:
   bad={**o,k:value};r=engine.score([p],[bad],profile,stamp)['rows'][0];self.assertFalse(r['eligible'],k)
  bad={**o,'screenshot_evidence':None,'alive_t20':True};self.assertEqual(engine.score([p],[bad],profile,stamp)['rows'][0]['observed'],'unknown')
  p['forecast']='unknown';self.assertIsNone(engine.score([p],[o],profile,stamp)['rows'][0]['exact_correct'])
 def test_override_projection_and_baseline(self):
  profile,p,o=self.fixture();package=json.loads((H/'evidence/v3c-package.json').read_text());projection,_=projected_hashes(package,profile)
  self.assertEqual(projection['/system/android/lib64/libhwui.so'],profile['native_overrides']['/system/android/lib64/libhwui.so'])
  self.assertEqual(projection['/system/android/framework/oh-adapter-runtime.jar'],profile['jar_sha256'])
  result=add_baselines(engine.score([p],[o],profile,'2026-10-01T00:00:00Z'));self.assertEqual(result['metrics']['all']['always_unchanged_accuracy'],0)
  old=json.loads((H/'profiles.json').read_text())['r17o'];self.assertFalse(engine.score([p],[o],old,'2026-10-01T00:00:00Z')['rows'][0]['eligible'])

class FreezeTests(unittest.TestCase):
 def test_pair_and_immutability(self):
  root=H/'freezes/v3';f=engine.verify(root);rows=json.loads((root/'predictions.json').read_text());self.assertEqual(len(rows),66);self.assertEqual(len({r['key'] for r in rows}),66)
  with (root/'predictions.csv').open() as fd:csvrows=list(csv.DictReader(fd))
  self.assertEqual(len(csvrows),66);self.assertEqual([(x['r17o'],x['r17p']) for x in rows],[(x['r17o'],x['r17p']) for x in csvrows])
  for v in ['r17o','r17p']:
   engine.verify(root/'variants'/v);flat=json.loads((root/'variants'/v/'predictions.json').read_text())
   self.assertEqual([x[v] for x in rows],[x['forecast'] for x in flat]);self.assertTrue(all(x['forecast'] in {'亮','推进','不变','unknown'} and x['reason'] and x['progress_checkpoint'] for x in flat))
  by={r['key']:r for r in rows};self.assertEqual(by['subwaysurfers']['r17o'],'unknown');self.assertEqual(by['fd-droidify']['r17o_exposure'],'prior-r17o-targeted-board-report');self.assertTrue(all(r['r17p_exposure']=='no-r17p-outcome-read' for r in rows))
  self.assertFalse(f['upcoming_full_sweep_results_read']);self.assertFalse(f['r17p_outcomes_read'])
  for r in rows:
   for ref in r['primary_evidence'].split(';'):self.assertTrue((root/ref).is_file(),ref)
 def test_prior_frozen_unchanged(self):
  old=H.parent/'2026-09-30-v3c-r17j-prospective/freezes/v2';engine.verify(old)
  self.assertEqual(engine.sha(old/'predictions.csv'),'be1879a15267f3c208236fce946644ea0580319b9cf8c9395218091182058bed')
  fb=H.parent/'2026-09-30-v2-scanner-feedback';self.assertEqual(engine.sha(fb/'matrix.csv'),'5b96bf4e34a50bfb0695bffcb4d40f827fc2eab38bfff894e8a306893b01d50b')
if __name__=='__main__':unittest.main()
