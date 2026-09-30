import unittest,json,hashlib
from pathlib import Path
from update90 import OUT,HERE,LIT,target_processes,network_candidate

class Task90Tests(unittest.TestCase):
 def test_observations(self):
  rows=json.loads((OUT/'predictions.json').read_text())
  self.assertEqual(len(rows),66);self.assertEqual(len({r['app'] for r in rows}),66)
  self.assertEqual(sum(r['captured'] for r in rows),124)
  self.assertEqual(sum(r['alive_t5'] is True for r in rows),13)
  self.assertTrue(all(r['alive_t20'] is None for r in rows))
  self.assertEqual({r['app'] for r in rows if r['visual']=='own-ui'},LIT)
  vlc=next(r for r in rows if r['app']=='vlc');self.assertTrue(vlc['alive_t5']);self.assertEqual(vlc['visual'],'black')
  for r in rows:
   rec=json.loads((OUT/r['record']).read_text())
   self.assertEqual(r['captured'],sum(s.get('captured') is True for s in rec.get('screenshots',[])))
   self.assertEqual(r['apk_sha256'],rec['apk_sha256'])
   proc=OUT/'evidence/records'/r['app']/'processes-t5.txt'
   if proc.exists():self.assertEqual(r['t5_processes'],target_processes(proc.read_text(),rec.get('bms',{}).get('uid')))
  self.assertEqual(target_processes('1 0 0 appspawn-x\n2 1 123 appspawn-x\n3 1 124 ps',123)[0]['pid'],2)
 def test_network(self):
  rows=json.loads((OUT/'predictions.json').read_text())
  self.assertEqual({r['app'] for r in rows if r['network_may_directly_light']},{'noice','fd-noice'})
  self.assertFalse(network_candidate('blank',['network-permission']))
  self.assertFalse(network_candidate('own-ui',[]))
  contract=json.loads((OUT/'network-contract.json').read_text());self.assertEqual(len(contract['required_together']),2)
  for key in ['noice','fd-noice']:
   d=json.loads((OUT/f'evidence/logs/{key}.json').read_text());self.assertIn('network-permission',d['families'])
  self.assertFalse(next(r for r in rows if r['app']=='wikipedia')['network_may_directly_light'])
 def test_rankings(self):
  from backtest85 import verify_freeze
  verify_freeze()
  rows={r['app']:r for r in json.loads((OUT/'predictions.json').read_text())}
  self.assertEqual(sum(r['prior_static_identity']=='exact' for r in rows.values()),32)
  self.assertIn('jobscheduler-startup',rows['fd-fitness']['stub_ok']);self.assertNotIn('shortcutmanager',rows['fd-fitness']['stub_ok'])
  self.assertIn('shortcutmanager',rows['fd-auxio']['stub_ok'])
  self.assertIn('velocitytracker-jni',rows['fd-auxio']['needs_real'])
  rank=json.loads((OUT/'wall-ranking.json').read_text())
  for policy in ['stub_ok','needs_real']:
   rr=sorted([r for r in rank if r['policy']==policy],key=lambda r:r['rank'])
   self.assertEqual([r['startup_affected_app_keys'] for r in rr],sorted([r['startup_affected_app_keys'] for r in rr],reverse=True))
   for r in rr:
    self.assertFalse(set(r['startup_apps'])&LIT)
    self.assertEqual(r['startup_affected_app_keys'],len(set(r['startup_apps'])))
  self.assertEqual(rows['fd-notes']['next_first_wall_candidate'],'unknown')
  self.assertIsNone(json.loads((OUT/'results.json').read_text())['prospective_hit_rate'])

if __name__=='__main__':unittest.main()
