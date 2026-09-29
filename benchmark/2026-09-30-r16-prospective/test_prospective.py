import datetime,hashlib,json,unittest
from pathlib import Path
from score import score
HERE=Path(__file__).resolve().parent

class ProspectiveTests(unittest.TestCase):
 def test_freeze(self):
  receipt=json.loads((HERE/'freeze.json').read_text())
  for item in receipt['outputs']:
   self.assertEqual(hashlib.sha256((HERE/item['path']).read_bytes()).hexdigest(),item['sha256'],item['path'])
  for item in receipt['inputs']:
   self.assertEqual(hashlib.sha256(Path(item['path']).read_bytes()).hexdigest(),item['sha256'],item['path'])
  rows=json.loads((HERE/'predictions.json').read_text())
  self.assertEqual(len(rows),66);self.assertEqual(len({r['app'] for r in rows}),66)
  self.assertTrue(all(type(r['expected_lit']) is bool for r in rows))
  self.assertTrue(all(r['expected_first_wall'] for r in rows))
  self.assertEqual(sum(r['expected_lit'] for r in rows),16)
  self.assertTrue(all((r['expected_first_wall']=='none')==r['expected_lit'] for r in rows))
  self.assertEqual(receipt['outputs'][0]['sha256'],'e8ce460f6a8cdfdfa13e3d885827f9aea3552cdb0b88e5be1f760995a43aa94e')
 def test_scoring(self):
  frozen='2026-09-30T00:15:05+08:00';epoch=datetime.datetime.fromisoformat(frozen).timestamp()
  pred=[{'app':x,'apk_sha256':x,'expected_lit':x=='a','expected_first_wall':'none' if x=='a' else 'unknown' if x=='e' else 'common-event-jni'} for x in 'abcde']
  outcomes={
   'a':{'apk_sha256':'a','complete':True,'visual':'lit','first_wall':'none','clicked_at':epoch+1,'profile':'confirmed'},
   'b':{'apk_sha256':'b','complete':True,'visual':'not-lit','first_wall':'common-event-jni','clicked_at':epoch-1},
   'c':{'apk_sha256':'mismatch','complete':True,'visual':'not-lit','first_wall':'common-event-jni','clicked_at':epoch+1},
   'd':{'apk_sha256':'d','complete':True,'visual':'unknown','clicked_at':epoch+1},
   'e':{'apk_sha256':'e','complete':True,'visual':'not-lit','first_wall':'common-event-jni','clicked_at':epoch+1},
  }
  r=score(pred,outcomes,frozen)
  self.assertEqual(r['all_exact_adjudicated']['lighting']['total'],3)
  self.assertEqual(r['all_exact_adjudicated']['lighting']['hits'],3)
  self.assertEqual(r['strict_pre_click']['lighting']['total'],2)
  self.assertEqual(r['all_exact_adjudicated']['first_wall_classified_forecasts'],{'hits':1,'total':1,'rate':1.0})
  self.assertEqual(r['all_exact_adjudicated']['first_wall_including_forecast_abstentions'],{'hits':1,'total':2,'rate':0.5})
  self.assertEqual(r['all_exact_adjudicated']['wall_forecast_abstentions'],1)
  self.assertEqual(r['all_exact_adjudicated']['excluded'],2)
  outcomes['a']['complete']=False
  self.assertEqual(score(pred,outcomes,frozen)['all_exact_adjudicated']['lighting']['total'],2)

if __name__=='__main__':unittest.main()
