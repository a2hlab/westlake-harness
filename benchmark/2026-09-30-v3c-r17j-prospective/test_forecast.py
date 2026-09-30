import hashlib,json,tempfile,unittest
from pathlib import Path
from score import HERE,verify,score
class ForecastTests(unittest.TestCase):
 def test_freeze(self):
  p=HERE/'freezes/v2';f=verify(p);rows=json.loads((p/'predictions.json').read_text());profile=json.loads((p/'profile.json').read_text())
  self.assertEqual(len(rows),66);self.assertEqual(len({r['key'] for r in rows}),66)
  self.assertEqual(f['counts'],{'不变':23,'推进':27,'亮':12,'unknown':4});self.assertFalse(f['new_full_sweep_results_read'])
  self.assertTrue(profile['package_sha256'].startswith('668e4f7c'));self.assertTrue(profile['jar_sha256'].startswith('20dcb71b'))
  for r in rows:
   self.assertEqual(len(r['apk_sha256']),64);self.assertTrue(r['prior_wall']);self.assertTrue(r['reason'])
   for ref in r['evidence'].split(';'):self.assertTrue((p/ref).is_file(),ref)
   raw=json.loads((p/'evidence/prior'/(r['key']+'.json')).read_text());self.assertEqual(r['prior_record_sha256'],raw['record_sha256'])
  self.assertEqual(next(r for r in rows if r['key']=='subwaysurfers')['forecast'],'unknown')
  for key in ['wikipedia','fd-gallery','fd-binaryeye','ooniprobe','fd-seal','toutiao']:
   self.assertEqual(next(r for r in rows if r['key']==key)['forecast'],'不变')
 def test_scoring(self):
  profile=json.loads((HERE/'freezes/v2/profile.json').read_text());board=profile['boards'][0]
  p={'key':'example','apk_sha256':'exact','forecast':'推进','prior_wall':'missing native','progress_checkpoint':'native returns','prior_exposure':'prior-sweep-only'}
  obs=dict(key='example',board=board,apk_sha256='exact',package_sha256=profile['package_sha256'],jar_sha256=profile['jar_sha256'],installer_sha256=profile['installer_sha256'],grant_verified=True,select_launcher_verified=True,batch_sidecars_enabled=True,profile_evidence='fingerprint:1',clicked_at='2026-09-30T05:00:00+08:00',lit='no',screenshot_evidence='t20.jpeg',advance='yes',progress_evidence='hilog:1',progress_checkpoint='native returns',prior_wall='missing native',same_wall='no',wall_evidence='hilog:2')
  freeze='2026-09-30T04:00:00+08:00'
  result=score([p],[obs],profile,freeze);self.assertEqual(result['metrics']['all']['exact_accuracy'],1)
  for field,value in [('apk_sha256','other'),('jar_sha256','other'),('clicked_at',freeze),('grant_verified',None),('profile_evidence',None)]:
   self.assertFalse(score([p],[dict(obs,**{field:value})],profile,freeze)['rows'][0]['eligible'])
  raised=score([p],[dict(obs,lit='yes')],profile,freeze)['rows'][0];self.assertFalse(raised['exact_correct']);self.assertTrue(raised['minimum_correct'])
  missing=score([p],[dict(obs,screenshot_evidence=None,progress_evidence=None,alive=True)],profile,freeze)['rows'][0];self.assertEqual(missing['observed'],'unknown');self.assertIsNone(missing['minimum_correct'])
  unknown=score([dict(p,forecast='unknown')],[obs],profile,freeze);self.assertIsNone(unknown['metrics']['all']['exact_accuracy']);self.assertEqual(unknown['metrics']['all']['coverage'],0)
  with self.assertRaisesRegex(ValueError,'duplicate'):score([p],[obs,obs],profile,freeze)
  with tempfile.TemporaryDirectory() as directory:
   root=Path(directory);(root/'predictions.csv').write_text('x');(root/'freeze.json').write_text(json.dumps({'hashes':{'predictions.csv':'wrong'}}))
   with self.assertRaisesRegex(ValueError,'changed'):verify(root)
if __name__=='__main__':unittest.main()
