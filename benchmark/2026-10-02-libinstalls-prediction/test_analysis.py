#!/usr/bin/env python3
"""Known-answer checks of real archived attempts, not a device test."""
import json,unittest
from pathlib import Path
import analyze
H=Path(__file__).resolve().parent
class PredictionEvidence(unittest.TestCase):
 @classmethod
 def setUpClass(cls):
  cls.attempts=json.loads((H/'attempts.json').read_text());cls.selected=json.loads((H/'selected166.json').read_text());cls.results=json.loads((H/'results.json').read_text())
 def test_exact_signed166_coverage_and_alias_pins(self):
  signed=json.loads(analyze.SIGN.read_text())['keys']
  self.assertEqual(len(self.selected),166);self.assertEqual({r['key'] for r in self.selected},set(signed))
  self.assertEqual(len(self.attempts),172)
  self.assertEqual([r['key'] for r in self.attempts if r['install_verdict']=='rejected'],['toutiao'])
  self.assertTrue(all(r['install_verdict']=='accepted' for r in self.selected))
 def test_real_toutiao_bm_rc0_is_failure_and_counterfactual_is_named(self):
  old=next(r for r in self.attempts if r['key']=='toutiao' and r['libinstalls_sha256']==analyze.OLD)
  new=next(r for r in self.selected if r['key']=='toutiao')
  self.assertEqual(old['bm_return_code'],0);self.assertEqual(old['install_verdict'],'rejected')
  self.assertEqual(old['apk_sha256'],new['apk_sha256']);self.assertEqual(new['install_verdict'],'accepted')
  self.assertTrue(analyze.moves_install_wall(old,{'com.ss.android.article.news'}))
  self.assertFalse(analyze.moves_install_wall(new,{'com.ss.android.article.news'}))
 def test_real_seal_three_exceptions_and_unrelated_launch_failure(self):
  seal=next(r for r in self.selected if r['key']=='fd-seal')
  names=['libaria2c.zip.so','libffmpeg.zip.so','libpython.zip.so']
  text='\n'.join(w['text'] for w in seal['install_witnesses'])
  self.assertTrue(all('exception '+n in text for n in names));self.assertEqual(seal['signed_verdict'],'lit')
  app=next(r for r in self.selected if r['key']=='cv2-com-frequent-habits')
  self.assertEqual(app['status'],'app_failed');self.assertEqual(app['install_verdict'],'accepted');self.assertFalse(app['tuple_target'])
 def test_zero_current_wall_movement_keeps_historical_failure(self):
  self.assertEqual(self.results['current_canonical_first_fatal_keys_expected_moved_count'],0)
  self.assertEqual(self.results['historical_stage_A_install_wall_keys'],['toutiao'])
  self.assertEqual(self.results['old_board_portability_target_keys'],['fd-seal','toutiao'])
  self.assertFalse(self.results['plan_created']);self.assertFalse(self.results['device_access'])
if __name__=='__main__':unittest.main(verbosity=2)
