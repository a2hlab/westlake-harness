#!/usr/bin/env python3
import csv
import json
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import check_fix_observers as cfo  # noqa: E402

INC_HEADER = 'variant,layer,target,operation,baseline_sha256,candidate_sha256\n'
KEYS = {
    'boards': [
        {'shards': [
            {'name': 'movers', 'per_key': {
                'fd-api': {'source': 'u16 cluster L — u15-jar-v1 (20e748e5)'},
                'fd-musicplayer': {'source': 'u16 cluster E — u15-framework-bitmap (framework 9e55e286)'},
                'vlc': {'source': 'u16 cluster D — u14-native-abi-gecko (7605812c)'},
                'mcdonalds': {'source': 'u16 cluster C — u14-native-abi-v2 (f8619ad5)'},
                'fd-plus': {'source': 'bt-le-scancallback stubs 87cf65cc'},
            }},
            {'name': 'lottery', 'per_key': {}},
        ]},
    ]
}


class Matrix(unittest.TestCase):
    def _run(self, inc_rows, keys=KEYS):
        with tempfile.TemporaryDirectory() as tmp:
            inc = Path(tmp) / 'inc.csv'
            kj = Path(tmp) / 'keys.json'
            inc.write_text(INC_HEADER + ''.join(inc_rows))
            kj.write_text(json.dumps(keys))
            out = Path(tmp) / 'm.csv'
            rc = cfo.main([str(inc), str(kj), '--csv', str(out)])
            return rc, list(csv.DictReader(out.open()))

    def test_framework_jar_has_observer(self):
        rc, rows = self._run(['common,JAR,/system/android/framework/framework.jar,replace,a,b\n'])
        self.assertEqual(rc, 0)
        self.assertEqual(rows[0]['status'], 'OK')
        self.assertIn('u15-jar-v1', rows[0]['observers'])

    def test_unobserved_artifact_is_gap_and_exit_1(self):
        rc, rows = self._run(['common,native,/system/android/lib64/libmystery.so,replace,a,b\n'])
        self.assertEqual(rc, 1)
        self.assertEqual(rows[0]['status'], 'GAP')

    def test_v4_missing_movers_are_reported(self):
        """Known answer: with v4's movers (no Gecko/_ctype_/ScanCallback), the three no-log
        fix artifacts must come out as GAPs."""
        v4_keys = {'boards': [{'shards': [{'name': 'movers', 'per_key': {
            'localsend': {'source': 'u14-flutter-libandroid EGL interposer'},
        }}]}]}
        rows_in = [
            'common,native,/system/android/lib64/libbionic_compat.so,replace,a,b\n',  # Gecko/_ctype_
            'common,JAR,/system/android/framework/adapter-mainline-stubs.jar,replace,a,b\n',  # ScanCallback stub
        ]
        with tempfile.TemporaryDirectory() as tmp:
            inc = Path(tmp) / 'inc.csv'
            kj = Path(tmp) / 'keys.json'
            inc.write_text(INC_HEADER + ''.join(rows_in))
            kj.write_text(json.dumps(v4_keys))
            out = Path(tmp) / 'm.csv'
            rc = cfo.main([str(inc), str(kj), '--csv', str(out)])
            rows = list(csv.DictReader(out.open()))
            self.assertEqual(rc, 1)
            self.assertEqual([r['status'] for r in rows], ['GAP', 'GAP'])
        # and with the v5 sources present they are covered
        rc5, rows5 = self._run(rows_in)
        self.assertEqual(rc5, 0)
        self.assertTrue(all(r['status'] == 'OK' for r in rows5))


class DerivedImage(unittest.TestCase):
    def test_boot_image_of_observed_jar_is_derived_ok(self):
        """Known answer: boot-adapter-mainline-stubs.art derives from
        adapter-mainline-stubs.jar; when the JAR itself is only reachable through its OWN
        boot- prefix token (not a direct JAR token), the image must still be OK via
        derived-from. Use an image whose JAR has a direct mover and no image token:
        apache-xml is not in TOKEN_TO_PATHS, so give the keys a mover naming it."""
        keys = {'boards': [{'shards': [{'name': 'movers', 'per_key': {
            'fd-api': {'source': 'u15-jar-v1 re-bakes apache-xml'},
        }}]}]}
        with tempfile.TemporaryDirectory() as tmp:
            inc = Path(tmp) / 'inc.csv'
            kj = Path(tmp) / 'keys.json'
            inc.write_text(INC_HEADER +
                           'common,JAR,/system/android/framework/apache-xml.jar,replace,a,b\n'
                           'common,image,/system/android/framework/arm64/boot-apache-xml.art,replace,a,b\n')
            kj.write_text(json.dumps(keys))
            out = Path(tmp) / 'm.csv'
            rc = cfo.main([str(inc), str(kj), '--csv', str(out)])
            rows = {r['target']: r for r in csv.DictReader(out.open())}
            self.assertEqual(rc, 0)
            img = rows['/system/android/framework/arm64/boot-apache-xml.art']
            self.assertEqual(img['status'], 'OK')
            self.assertIn('derived-from[apache-xml.jar]', img['observers'])

    def test_boot_image_of_unobserved_jar_still_gap(self):
        with tempfile.TemporaryDirectory() as tmp:
            inc = Path(tmp) / 'inc.csv'
            kj = Path(tmp) / 'keys.json'
            inc.write_text(INC_HEADER +
                           'common,JAR,/system/android/framework/mystery.jar,replace,a,b\n'
                           'common,image,/system/android/framework/arm64/boot-mystery.art,replace,a,b\n')
            kj.write_text(json.dumps(KEYS))
            out = Path(tmp) / 'm.csv'
            rc = cfo.main([str(inc), str(kj), '--csv', str(out)])
            rows = {r['target']: r for r in csv.DictReader(out.open())}
            self.assertEqual(rc, 1)
            self.assertEqual(rows['/system/android/framework/arm64/boot-mystery.art']['status'], 'GAP')


class ShaAndSmoke(unittest.TestCase):
    def test_sha_prefix_in_source_observes_row(self):
        """Known answer: a mover source naming f8619ad5 observes any increments row whose
        sha256 starts with f8619ad5 (the vlc/fennec Gecko ABI pattern)."""
        keys = {'boards': [{'shards': [{'name': 'movers', 'per_key': {
            'vlc': {'source': 'u16 cluster D — gecko ABI f8619ad5 moves __gnu_strerror_r'},
        }}]}]}
        with tempfile.TemporaryDirectory() as tmp:
            inc = Path(tmp) / 'inc.csv'; kj = Path(tmp) / 'keys.json'
            inc.write_text(INC_HEADER +
                'common,native,/system/android/lib64/libgecko_fix.so,replace,'
                'f8619ad5deadbeef' + 'a' * 48 + ',' + 'b' * 64 + '\n')
            kj.write_text(json.dumps(keys))
            out = Path(tmp) / 'm.csv'
            rc = cfo.main([str(inc), str(kj), '--csv', str(out)])
            rows = list(csv.DictReader(out.open()))
            self.assertEqual(rc, 0)
            self.assertEqual(rows[0]['status'], 'OK')
            self.assertIn('sha[f8619ad5', rows[0]['observers'])

    def test_smoke_proposal_observes_artifact(self):
        """Known answer: a smoke proposal whose probe.files pins liboh_adapter_bridge.so's
        sha observes the increments row carrying that sha."""
        keys = {'boards': [{'shards': [{'name': 'movers', 'per_key': {}}]}]}
        with tempfile.TemporaryDirectory() as tmp:
            inc = Path(tmp) / 'inc.csv'; kj = Path(tmp) / 'keys.json'
            smoke = Path(tmp) / 'smoke.json'
            sha = 'b8a87f6fe2902b1d' + '0' * 48
            inc.write_text(INC_HEADER +
                f'common,native,/system/android/lib64/liboh_adapter_bridge.so,replace,{sha},' + 'c' * 64 + '\n')
            kj.write_text(json.dumps(keys))
            smoke.write_text(json.dumps({'probe': {'files': {
                '/system/android/lib64/liboh_adapter_bridge.so': sha}},
                'fixes': [{'id': 'U14-BRIDGE-M5', 'key': 'k', 'markers': ['x']}]}))
            out = Path(tmp) / 'm.csv'
            rc = cfo.main([str(inc), str(kj), '--smoke', str(smoke), '--csv', str(out)])
            rows = list(csv.DictReader(out.open()))
            self.assertEqual(rc, 0)
            self.assertEqual(rows[0]['status'], 'OK')
            self.assertIn('smoke[', rows[0]['observers'])


if __name__ == '__main__':
    unittest.main()
