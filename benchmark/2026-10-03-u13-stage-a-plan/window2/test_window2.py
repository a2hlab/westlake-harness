import importlib.util,json,sys,tempfile,unittest
from pathlib import Path
from unittest.mock import patch
H=Path(__file__).resolve().parent;P=H.parent;W=H.parents[3]
sys.path.insert(0,str(P))
spec=importlib.util.spec_from_file_location('aux',P/'window2-observe.py');aux=importlib.util.module_from_spec(spec);spec.loader.exec_module(aux)
class Window2(unittest.TestCase):
 def test_board_authority_and_remaining(self):
  auth=json.loads((P/'outer-window-authorization.json').read_text());cov=json.loads((P/'window1/evidence/production/coverage.json').read_text())
  for b,d in [('5ea',H),('5cd',H),('61b',P/'window2-61b')]:
   p=json.loads((d/f'plan-{b}.json').read_text());c=json.loads((d/'composition.json').read_text());a=auth['per_board'][p['serial']]
   self.assertEqual(c['approved_unarmed_bundle_sha256'],a['bundle_sha256']);self.assertEqual(c['base_bundle_sha256'],a['effective_baseline_bundle_sha256'])
   keys=[k for s in p['shards'] for k in (d/'keys'/b/Path(s['keys_file']).name).read_text().split()]
   measured={x['key'] for x in cov[b]['measured']};self.assertFalse((set(keys)-{'fd-fitness'})&measured)
   if b=='5ea':self.assertEqual(keys.count('fd-fitness'),6)
   if b=='61b':self.assertEqual(len(keys),56);self.assertEqual(len(set(keys)),56)
   self.assertTrue(p['restore']['unconditional']);self.assertEqual(p['restore']['identity_assertions'],318)
 def test_auxiliary_once(self):
  with tempfile.TemporaryDirectory() as td:
   r=Path(td);plan=r/'plan.json';plan.write_text(json.dumps({'longwait_after_shard':'regular'}))
   args=['aux','shard','--plan',str(plan),'--root',str(r/'regular'),'--out',str(r/'selftest/regular.json'),'--name','regular','--cutoff','123']
   with patch.object(sys,'argv',args),patch.object(aux.observe,'main',return_value=0),patch.object(aux.observe,'longwait',return_value=0) as longwait:
    self.assertEqual(aux.main(),0);longwait.assert_called_once();self.assertEqual(longwait.call_args.args[1:],(r,123.0))
    (r/'longwait-result.json').write_text('[]');longwait.reset_mock();self.assertEqual(aux.main(),0);longwait.assert_not_called()
if __name__=='__main__':unittest.main()
