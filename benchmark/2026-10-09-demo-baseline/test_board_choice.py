"""Recorded three-board known answers; no live board access."""
import hashlib
import json
from pathlib import Path
import unittest
H=Path(__file__).resolve().parent
class ReadonlyBoardChoiceTests(unittest.TestCase):
 def test_signed_fingerprints_and_complete_reads(self):
  actual=json.loads((H/'evidence/readonly-20261009/receipt.json').read_text())
  expected={'5ea':'821de739cf81','5cd':'821de739cf81','61b':'452447a4a0ba'}
  self.assertEqual(set(actual['boards']),set(expected))
  self.assertEqual(actual['remote_write_operations'],0);self.assertEqual(actual['lock_operations'],0)
  for tag,row in actual['boards'].items():
   self.assertTrue(row['same_boot']);self.assertEqual(row['runtime_fingerprint'],expected[tag]);self.assertEqual(row['boot_image_fingerprint'],'ee927db88a67')
   for name,n,key in [('runtime-fingerprint.txt',124,'runtime_fingerprint'),('boot-image-fingerprint.txt',36,'boot_image_fingerprint')]:
    lines=(H/'evidence/readonly-20261009'/tag/name).read_text().splitlines();self.assertEqual(len(lines),n)
    self.assertEqual(hashlib.sha256('\n'.join(lines).encode()).hexdigest()[:12],row[key])
   self.assertTrue(all(x['rc']==0 for x in row['commands']))
   self.assertTrue(all(x['command'].startswith(('cat /proc/','df -k /data','pidof appspawn-x','sha256sum ')) for x in row['commands']))
 def test_known_capacity_and_selected_installer(self):
  d=json.loads((H/'results.json').read_text());self.assertEqual(d['choice'],'61b')
  cap=json.loads((H/'evidence/apk-capacity.json').read_text());self.assertEqual(cap['distinct_packages'],128);self.assertEqual(cap['missing'],[])
  self.assertEqual(cap['apk_bytes'],1756238122);self.assertEqual(cap['apk_times_3_bytes'],5268714366)
  for tag,x in d['boards'].items():
   raw=(H/'evidence/readonly-20261009'/tag/'storage.txt').read_text().splitlines()[-1].split()
   self.assertEqual(x['data_free_bytes'],int(raw[3])*1024);self.assertGreater(x['data_free_bytes'],cap['apk_times_3_bytes'])
  self.assertEqual(d['boards']['61b']['libinstalls_sha256'],'51e1b52538b3198d2a8a3236a9479bf8512f51acc74c0d68e34acca358f39be5')
 def test_counts_are_signed_keys_not_plan_counts(self):
  history=json.loads((H/'evidence/history.json').read_text());repo=H.parents[1];sets={t:set() for t in ('5ea','5cd','61b')}
  for source in history['u13_stage_a_sources']:
   for key,row in json.loads((repo/source).read_text())['keys'].items():
    if row.get('lit_runs',0)>0 or row.get('verdict')=='lit': sets[row['board']].add(key)
  self.assertEqual({t:len(k) for t,k in sets.items()},{'5ea':47,'5cd':46,'61b':33})
  for t,keys in sets.items():self.assertEqual(history['boards'][t]['keys'],sorted(keys))
if __name__=='__main__':unittest.main()
