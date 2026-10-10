"""Continuation safety: only finished keys from a clean prior window are excluded."""
import importlib.util
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
HERE=Path(__file__).resolve().parent
s=importlib.util.spec_from_file_location('remaining',HERE/'prepare_remaining.py');m=importlib.util.module_from_spec(s);s.loader.exec_module(m)
class ContinuationTests(unittest.TestCase):
 def fixture(self,root,finish=0):
  def put(p,v):p.parent.mkdir(parents=True,exist_ok=True);p.write_text(json.dumps(v));return p
  serial='5cd1e3dd00000000000000000923012c'
  run=root/'runner'
  put(run/'board-run-result.json',{'before_unlock':finish})
  put(run/'old'/'runid'/serial/'a'/'record.json',{'key':'a','finished_at':'2026-10-10','install_only':False})
  plan=put(root/'prior.json',{'serial':serial,'out':str(run),'shards':[{'name':'old'}],'after_lock':['hook','old-before'],'before_unlock':['hook','old-after'],'offline_precheck':{'evidence':[]},'demo_ability_pins':{'c':{'ability':'Entry'}}})
  r=root/'round';put(r/'round.json',{'serial':serial,'windows':[str(plan)]})
  put(r/'batch-apps.json',{'apps':[{'key':k,'input_root':'root'} for k in ('a','b','c')]})
  put(r/'shot-tiers.json',{'apps':[{'key':k,'screenshot_seconds':10 if k!='c' else 20} for k in ('a','b','c')]})
  return r,plan
 def test_only_unfinished_exact_tier_groups_disabled(self):
  with tempfile.TemporaryDirectory() as t:
   root=Path(t);r,p=self.fixture(root);out=root/'next'
   with patch('sys.argv',['prepare_remaining','--round',str(r),'--previous-plan',str(p),'--out',str(out)]):m.main()
   result=m.read(out/'continuation.json');self.assertEqual(result['pending'],['b','c']);self.assertEqual(set(result['finished']),{'a'})
   plan=m.read(m.expand(result['plans'][0]));self.assertFalse(plan['execution_enabled']);self.assertEqual(len(plan['shards']),2);self.assertEqual(set(plan['demo_ability_pins']),{'c'})
 def test_failed_finish_refuses_continuation(self):
  with tempfile.TemporaryDirectory() as t:
   root=Path(t);r,p=self.fixture(root,1);out=root/'next'
   with patch('sys.argv',['prepare_remaining','--round',str(r),'--previous-plan',str(p),'--out',str(out)]),self.assertRaisesRegex(ValueError,'did not release'):m.main()
   self.assertFalse(out.exists())
if __name__=='__main__':unittest.main()

class CutoffTests(unittest.TestCase):
 def test_only_recorded_deadline_with_wrapped_records_is_resumable(self):
  spec=importlib.util.spec_from_file_location('controller',HERE/'run_remaining.py');c=importlib.util.module_from_spec(spec);spec.loader.exec_module(c)
  with tempfile.TemporaryDirectory() as t:
   root=Path(t);folder=root/'group'/'runid'/'serial';folder.mkdir(parents=True)
   record=folder/'key'/'record.json';record.parent.mkdir();record.write_text(json.dumps({'finished_at':100,'status':'foreground_unconfirmed'}))
   summary=folder/'summary.json';summary.write_text(json.dumps({'stopped_at_new_key_deadline':True,'not_run':['next']}))
   result={'stopped_after_shard':'group','stop_new_keys_at':99,'shards':[{'name':'group','rc':1}]}
   with patch.object(c.time,'time',return_value=100):
    self.assertTrue(c.clean_cutoff({'out':str(root)},result))
    record.write_text(json.dumps({'status':'started'}));self.assertFalse(c.clean_cutoff({'out':str(root)},result))
    record.write_text(json.dumps({'finished_at':100,'status':'foreground_unconfirmed'}))
    summary.write_text(json.dumps({'batch_error':'cleanup refused'}));self.assertFalse(c.clean_cutoff({'out':str(root)},result))
