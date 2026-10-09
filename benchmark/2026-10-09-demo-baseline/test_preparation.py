"""Offline known answers for pinned identity and ordering; no board/VM transport."""
import importlib.util
import unittest
from pathlib import Path
s=importlib.util.spec_from_file_location('prep',Path(__file__).with_name('prepare_t3.py'));m=importlib.util.module_from_spec(s);s.loader.exec_module(m)
class PreparationTests(unittest.TestCase):
 def app(self,key,pkg):return {'key':key,'package':pkg,'apk_sha256':'a'*64}
 def test_order_and_disabled_plans(self):
  a=[self.app('z','org.z'),self.app('a','org.a'),self.app('b','org.b')];_,_,ps=m.plans({'apps':a},'/tmp/demo','smoke.json',2)
  self.assertEqual([sh['name'] for _,p,_ in ps for sh in p['shards']],['001-z','002-a','003-b']);self.assertTrue(all(p['execution_enabled'] is False for _,p,_ in ps));self.assertTrue(all(p['window_limit_minutes']==45 and p['stop_new_tests_by_minute']==35 for _,p,_ in ps))
 def test_duplicate_package_rejected(self):
  with self.assertRaisesRegex(ValueError,'duplicate'):m.plans({'apps':[self.app('a','org.a'),self.app('b','org.a')]},'/tmp/demo','smoke.json')
 def test_bad_sha_rejected(self):
  a=self.app('a','org.a');a['apk_sha256']='bad'
  with self.assertRaisesRegex(ValueError,'SHA'):m.plans({'apps':[a]},'/tmp/demo','smoke.json')
 def test_unrecorded_first_tap_rejected(self):
  a=self.app('a','org.a');a['needs_first_tap']=True
  with self.assertRaisesRegex(ValueError,'instruction'):m.plans({'apps':[a]},'/tmp/demo','smoke.json')
 def test_first_tap_remains_pending(self):
  a=self.app('a','org.a');a.update(needs_first_tap=True,first_tap='Accept welcome dialog');_,t,_=m.plans({'apps':[a]},'/tmp/demo','smoke.json');self.assertEqual(t[0]['instruction'],'Accept welcome dialog');self.assertIn('pending',t[0]['status'])
if __name__=='__main__':unittest.main()
