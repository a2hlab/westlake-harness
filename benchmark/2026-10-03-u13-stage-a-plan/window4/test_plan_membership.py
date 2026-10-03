import unittest,json,os
from pathlib import Path
import guard_plan_keys
H=Path(__file__).resolve().parent;W=H.parents[3]
os.environ['WORKSPACES']=str(W)
class Membership(unittest.TestCase):
 def test_workspace_root_without_environment(self):
  prior=os.environ.pop('WORKSPACES',None)
  try:
   p=json.loads((H.parent/'window4-61b-r2/plan-61b.json').read_text())
   self.assertEqual(guard_plan_keys.validate(p)[0]['keys'],['fd-k9','fd-netguard','fd-seal','fd-organicmaps'])
  finally:
   if prior is not None:os.environ['WORKSPACES']=prior
 def test_original_invalid_see_rejects_before_lock(self):
  p=json.loads((H.parent/'window4-61b/plan-61b.json').read_text())
  with self.assertRaisesRegex(ValueError,"unknown=\\['see'\\]"):guard_plan_keys.validate(p)
 def test_corrected_six_six_four_exact_authority(self):
  allkeys=[]
  for b,d in [('5ea',H),('5cd',H),('61b',H.parent/'window4-61b-r2')]:
   p=json.loads((d/f'plan-{b}.json').read_text());rows=guard_plan_keys.validate(p);allkeys += [k for r in rows for k in r['keys']]
   if b=='61b':self.assertEqual(rows[-1]['keys'][-1],'fd-organicmaps')
  authority=W/'westlake-harness/benchmark/2026-10-03-u13-stage-a-plan/window3-signoff/lit-reference-unmeasured.txt'
  self.assertEqual(len(allkeys),16);self.assertCountEqual(allkeys,authority.read_text().split());self.assertEqual(len(set(allkeys)),16)
if __name__=='__main__':unittest.main()
