"""Offline invariants and fail-closed data controls; no device subprocesses."""
import copy,unittest
import inventory

class InventoryChecks(unittest.TestCase):
 def test_list_rejects_error_wrong_user_empty_duplicates_and_bad_names(self):
  self.assertEqual(inventory.parse_bundles('ID: 100:\n\ta.b\n'),{'a.b'})
  for text in ['','error: failed\n','ID: 0:\n\ta.b\n','ID: 100:\n','ID: 100:\n\ta.b\n\ta.b\n','ID: 100:\na.b\n','ID: 100:\n\ta;b\n']:
   with self.subTest(text=text),self.assertRaises(ValueError):inventory.parse_bundles(text)
 def test_protected_unknown_and_demo_cannot_be_removed(self):
  m=inventory.read(inventory.HERE/'manifest.json');a=inventory.read(inventory.HERE/'actions.disabled.json');self.assertTrue(inventory.validate(m,a))
  for package in ['org.westlake.imehost','com.ss.android.article.news','com.ohos.sceneboard','com.example.helloworld','not.identified.package',m['apps'][0]['package']]:
   bad=copy.deepcopy(a)
   for category in ('install','keep','remove','protect'):bad[category]=[r for r in bad[category] if r['package']!=package]
   bad['remove'].append({'package':package})
   with self.subTest(package=package),self.assertRaises(ValueError):inventory.validate(m,bad)
 def test_disabled_unique_categories_and_complete_signed_membership(self):
  m=inventory.read(inventory.HERE/'manifest.json');a=inventory.read(inventory.HERE/'actions.disabled.json')
  for case in ['enabled','duplicate','missing']:
   bad=copy.deepcopy(a)
   if case=='enabled':bad['execution_enabled']=True
   elif case=='duplicate':bad['protect'].append(copy.deepcopy(bad['keep'][0]))
   else:bad['keep'].pop()
   with self.subTest(case=case),self.assertRaises(ValueError):inventory.validate(m,bad)
 def test_historical_click_not_new_device_or_hand_tap_pass(self):
  m=inventory.read(inventory.HERE/'manifest.json');ordinary=m['apps'][:128]
  clicked=[r for r in ordinary if r['desktop_click']['kind']=='ACTUAL_AUTOMATED_DESKTOP_ICON_CLICK_RAW_RC_VERIFIED']
  fallback=[r for r in ordinary if r['desktop_click']['kind']=='NO_DESKTOP_CLICK_PROVEN']
  self.assertEqual(len(clicked),125);self.assertEqual(len(fallback),3)
  self.assertTrue(all(not r['desktop_click']['human_hand_tap_proven'] and not r['desktop_click']['current_icon_reverified'] for r in ordinary))
  self.assertTrue(all(r['current_apk_sha256'] is None for r in m['apps']))

if __name__=='__main__':unittest.main()
