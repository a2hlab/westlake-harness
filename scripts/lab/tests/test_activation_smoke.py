#!/usr/bin/env python3
"""activation_smoke: the decision is PASS only when fingerprints, controls, markers, single-copy and child view hold."""
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import activation_smoke as s

FACTS = """RUNTIME fingerprint=e953c0921536 files=119 (runtime-fingerprint.txt; ...)
FROZEN checked=4 violations=0
BOOTIMAGE fingerprint=4db882a81732 files=36 (boot-image-fingerprint.txt; not part of RUNTIME)
TOOL bms_batch=3529581f head=x manifest=y (plan.json tool)
helloworld           shots 2/2  alive t5=yes t20=yes  child_hilog=6352  foreground_unconfirmed
zigzag               shots 2/2  alive t5=yes t20=no  child_hilog=13385  foreground_unconfirmed
TOTAL keys=2 screenshots_captured=4/4 alive_t5=2 alive_t20=1
"""
MAPS_ONE = """7f00-7f10 r-xp 0 fd:00 1 /system/lib64/westlake/route-a/x/libart.so
7f10-7f20 r--p 0 fd:00 1 /system/lib64/westlake/route-a/x/libart.so
7f30-7f40 r-xp 0 fd:00 2 /system/android/lib64/liboh_adapter_bridge.so
"""
MAPS_TWO = MAPS_ONE + "7f50-7f60 r-xp 0 fd:00 3 /system/lib64/libart.so\n"
SPEC = {'expect': {'runtime_fp': 'e953c0921536', 'boot_fp': '4db882a81732'},
        'groups': [{'manifest': 'm', 'keys': ['helloworld'], 'mode': 'launch-only', 'controls': True}],
        'fixes': [{'id': 'J10-NOTITLE', 'key': 'knot', 'markers': [r'\[J10-NOTITLE\] installed']}],
        'probe': {'package': 'com.example.helloworld', 'single_copy': ['libart.so', 'liboh_adapter_bridge.so'],
                  'files': {'/system/a.jar': 'aa'}}}


class Smoke(unittest.TestCase):
    def runs(self):
        return {'group-0': s.parse_facts(FACTS)}

    def test_stale_scene_session_only_for_dead_key_with_its_own_package(self):
        import json, tempfile
        line = ('10-01 22:15:26.417 13484 13484 W A04202/WMSMain: add failed. com.example.helloworld.MainActivity/'
                'com.example.helloworld/entry/0(persistentId: 29)(containerId: 1) already existed in array\n')
        with tempfile.TemporaryDirectory() as d:
            for key, package, text in (('helloworld', 'com.example.helloworld', line),
                                       ('zigzag', 'com.ketchapp.zigzaggame', line)):   # zigzag's hilog names another app
                k = Path(d) / 'run' / 'serial' / key
                k.mkdir(parents=True)
                (k / 'record.json').write_text(json.dumps({'package': package}))
                (k / 'hilog.txt').write_text(text)
            self.assertEqual(s.stale_session_keys(Path(d), ['helloworld', 'zigzag']), ['helloworld'])
            self.assertEqual(s.stale_session_keys(Path(d), []), [])               # alive keys are never retried

    def test_parse_facts(self):
        f = s.parse_facts(FACTS)
        self.assertEqual((f['runtime_fp'], f['boot_fp']), ('e953c0921536', '4db882a81732'))
        self.assertEqual(f['alive_t20'], {'helloworld': 'yes', 'zigzag': 'no'})

    def test_same_path_loaded_twice_is_two_copies(self):
        maps = ("7f0338-7f0343 r--p 00000000 103:30 98478 /system/android/lib64/liboh_adapter_bridge.so\n"
                "7f0343-7f0351 r-xp 000b7000 103:30 98478 /system/android/lib64/liboh_adapter_bridge.so\n"
                "7f0dfc-7f0e07 r--p 00000000 103:30 98478 /system/android/lib64/liboh_adapter_bridge.so\n"
                "7f0e07-7f0e15 r-xp 000b7000 103:30 98478 /system/android/lib64/liboh_adapter_bridge.so\n")
        got = s.copies(maps, ['liboh_adapter_bridge.so'])['liboh_adapter_bridge.so']
        self.assertEqual(len(got), 2)
        ok, checks = s.evaluate({'probe': {'single_copy': ['liboh_adapter_bridge.so']}}, {}, {},
                                {'copies': {'liboh_adapter_bridge.so': got}, 'view': {}})
        self.assertFalse(ok)

    def test_expect_copies_accepts_known_count(self):
        probe = {'copies': {'liboh_adapter_bridge.so': ['a@1', 'a@2']}, 'view': {}}
        ok, _ = s.evaluate({'probe': {'single_copy': ['liboh_adapter_bridge.so'],
                                      'expect_copies': {'liboh_adapter_bridge.so': 2}}}, {}, {}, probe)
        self.assertTrue(ok)
        ok, _ = s.evaluate({'probe': {'single_copy': ['liboh_adapter_bridge.so']}}, {}, {}, probe)
        self.assertFalse(ok)

    def test_copies_counts_distinct_paths(self):
        self.assertEqual(len(s.copies(MAPS_ONE, ['libart.so'])['libart.so']), 1)
        self.assertEqual(len(s.copies(MAPS_TWO, ['libart.so'])['libart.so']), 2)
        self.assertEqual(s.copies(MAPS_ONE, ['libopenjdkjvm.so'])['libopenjdkjvm.so'], [])

    def test_all_good_passes(self):
        probe = {'copies': s.copies(MAPS_ONE, SPEC['probe']['single_copy']), 'view': {'/system/a.jar': 'aa'}}
        ok, checks = s.evaluate(SPEC, self.runs(), {'knot': 'x [J10-NOTITLE] installed y'}, probe)
        self.assertTrue(ok, checks)

    def test_inactive_fix_fails(self):  # J9: the fix printed "not installed", never "installed"
        probe = {'copies': s.copies(MAPS_ONE, SPEC['probe']['single_copy']), 'view': {'/system/a.jar': 'aa'}}
        ok, checks = s.evaluate(SPEC, self.runs(), {'knot': '[J9-NOTITLE] no current Application; not installed'}, probe)
        self.assertFalse(ok)
        self.assertFalse(next(c for c in checks if c['check'] == 'marker')['ok'])

    def test_missing_hilog_fails(self):
        probe = {'copies': s.copies(MAPS_ONE, SPEC['probe']['single_copy']), 'view': {'/system/a.jar': 'aa'}}
        ok, _ = s.evaluate(SPEC, self.runs(), {}, probe)
        self.assertFalse(ok)

    def test_second_art_copy_fails(self):  # N10: system + route-a libart in the same child
        probe = {'copies': s.copies(MAPS_TWO, SPEC['probe']['single_copy']), 'view': {'/system/a.jar': 'aa'}}
        ok, checks = s.evaluate(SPEC, self.runs(), {'knot': '[J10-NOTITLE] installed'}, probe)
        self.assertFalse(ok)
        self.assertFalse(next(c for c in checks if c.get('lib') == 'libart.so')['ok'])

    def test_wrong_child_view_and_fingerprint_fail(self):
        probe = {'copies': s.copies(MAPS_ONE, SPEC['probe']['single_copy']), 'view': {'/system/a.jar': 'bb'}}
        ok, _ = s.evaluate(SPEC, self.runs(), {'knot': '[J10-NOTITLE] installed'}, probe)
        self.assertFalse(ok)
        runs = {'group-0': dict(s.parse_facts(FACTS), runtime_fp='68b7fb016253')}
        probe['view'] = {'/system/a.jar': 'aa'}
        ok, _ = s.evaluate(SPEC, runs, {'knot': '[J10-NOTITLE] installed'}, probe)
        self.assertFalse(ok)

    def test_probe_error_fails(self):
        ok, _ = s.evaluate(SPEC, self.runs(), {'knot': '[J10-NOTITLE] installed'}, {'error': 'child count 0'})
        self.assertFalse(ok)

    def test_install_window_hilog_is_searched(self):
        import tempfile
        with tempfile.TemporaryDirectory() as d:
            key = Path(d) / 'knot'
            key.mkdir()
            (key / 'install-hilog.txt').write_text('ICONLESS_APK_TEMPLATE_PLACEHOLDER: apk=x class=DECLARED_XML_ONLY\n')
            (key / 'hilog.txt').write_text('launch line\n')
            text = s.key_hilog(key)
        self.assertEqual(s.marker_hits(text, [r'ICONLESS_APK_TEMPLATE_PLACEHOLDER: apk=.* class=DECLARED_XML_ONLY',
                                              'launch line']), {r'ICONLESS_APK_TEMPLATE_PLACEHOLDER: apk=.* class=DECLARED_XML_ONLY': 1,
                                                                'launch line': 1})


class ApprovedBaselineAndCrypto(unittest.TestCase):
    def test_signed_upper_bound_allows_one_or_two_but_not_three(self):
        spec={'probe':{'single_copy':['liboh_adapter_bridge.so'], 'copy_limits':{'liboh_adapter_bridge.so':{'min':1,'max':2}}}}
        for count,expected in [(0,False),(1,True),(2,True),(3,False)]:
            ok,_=s.evaluate(spec,{}, {}, {'copies':{'liboh_adapter_bridge.so':[str(i) for i in range(count)]},'view':{}})
            self.assertEqual(ok,expected)

    def test_new_optional_member_at_most_one(self):
        spec={'probe':{'single_copy':['libicu74compat.so'],'copy_limits':{'libicu74compat.so':{'min':0,'max':1}}}}
        for count,expected in [(0,True),(1,True),(2,False)]:
            ok,_=s.evaluate(spec,{}, {}, {'copies':{'libicu74compat.so':[str(i) for i in range(count)]},'view':{}})
            self.assertEqual(ok,expected)

    def test_missing_copy_table_member_rejects(self):
        spec={'probe':{'single_copy':['libart.so'],'copy_limits':{'libart.so':{'min':1,'max':1}}}}
        self.assertFalse(s.evaluate(spec,{}, {}, {'copies':{},'view':{}})[0])

    def test_crypto_report_missing_or_rejected_never_passes(self):
        spec={'control_selftest':True}
        for crypto in [None,{'schema_version':2,'passed':False},{'schema_version':1,'passed':True}]:
            self.assertFalse(s.evaluate(spec,{}, {}, {'control_crypto':crypto})[0])
        self.assertTrue(s.evaluate(spec,{}, {}, {'control_crypto':{'schema_version':2,'passed':True}})[0])

    def crypto_records(self,text):
        import json,tempfile
        root=tempfile.TemporaryDirectory();p=Path(root.name)
        for key in ['helloworld','zigzag']:
            d=p/'run'/'serial'/key;d.mkdir(parents=True)
            (d/'record.json').write_text(json.dumps({'key':key,'bms':{'uid':123},'diagnostics':{'complete':True}}))
            (d/'processes-t20.txt').write_text('456 1 123 appspawn-x\n')
            (d/'hilog.txt').write_text(text)
        return root,p

    def test_real_scanner_success(self):
        root,p=self.crypto_records('10-03 10:00:00.000 456 x [WL-KS-PROBE] validateAead round-trip=OK\n')
        with root:
            self.assertTrue(s.control_crypto({'control_selftest':True,'groups':[{'controls':True,'keys':['helloworld','zigzag']}]},p)['passed'])

    def test_real_scanner_ok_then_badtag_rejects(self):
        root,p=self.crypto_records('10-03 10:00:00.000 456 x [WL-KS-PROBE] validateAead=OK\n10-03 10:00:00.001 456 x [WL-KS-PROBE] selftest AEADBadTagException via default provider\n')
        with root:
            self.assertFalse(s.control_crypto({'control_selftest':True,'groups':[{'controls':True,'keys':['helloworld','zigzag']}]},p)['passed'])

    def test_real_scanner_silence_rejects(self):
        root,p=self.crypto_records('10-03 10:00:00.000 456 x other text\n')
        with root:
            self.assertFalse(s.control_crypto({'control_selftest':True,'groups':[{'controls':True,'keys':['helloworld','zigzag']}]},p)['passed'])


if __name__ == '__main__':
    unittest.main()
