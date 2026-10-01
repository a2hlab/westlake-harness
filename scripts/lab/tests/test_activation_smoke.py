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


if __name__ == '__main__':
    unittest.main()
