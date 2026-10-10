"""Known answers use the 128 actual outer-selected t3 records and captures."""
import copy
import importlib.util
import json
from pathlib import Path
import shutil
import tempfile
import unittest
from unittest.mock import patch

HERE = Path(__file__).resolve().parent
spec = importlib.util.spec_from_file_location('regression', HERE / 'regress_vs_signoff.py')
r = importlib.util.module_from_spec(spec)
spec.loader.exec_module(r)
spec = importlib.util.spec_from_file_location('round_driver', HERE / 'run_post_reboot.py')
d = importlib.util.module_from_spec(spec)
spec.loader.exec_module(d)


class RealT3KnownAnswers(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        # Raw screenshots are intentionally persistent large evidence, not invented substitutes.
        try:
            cls.ref = r.references(r.read(r.BASE / 't3-outer-signoff.json'), r.BASE / 't3')
        except (OSError, ValueError) as e:
            raise unittest.SkipTest('persistent t3 raw evidence unavailable: ' + str(e))
        assert len(cls.ref) == 128

    def fixture(self, root):
        for key, ref in self.ref.items():
            src = r.expand(ref['record'])
            folder = root / d.SERIAL / key
            folder.mkdir(parents=True)
            record = r.read(src)
            (folder / 'record.json').write_text(json.dumps(record))
            tag, image, _ = r.last_capture(src)
            if image:
                (folder / image.name).symlink_to(image.resolve())
            for tag in ('t5', 't10', 't20'):
                src_ps = src.parent / ('processes-' + tag + '.txt')
                if src_ps.is_file():
                    shutil.copyfile(src_ps, folder / src_ps.name)

    def test_actual_t3_all_same_128_changed_zero(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            self.fixture(root)
            result = r.compare(r.records(root), self.ref)
            self.assertEqual(result['summary'], {'same': 128, 'changed': 0, 'missing': 0})
            print('KNOWN_ANSWER t3 all-same: same=128 changed=0 missing=0')

    def test_actual_t3_change_two_final_images_changed_two(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            self.fixture(root)
            keys = [k for k, v in self.ref.items() if v['image']][:3]
            other = r.expand(self.ref[keys[2]]['image'])
            for key in keys[:2]:
                p = root / d.SERIAL / key / 'record.json'
                record = r.read(p)
                final = max(record['screenshots'], key=lambda x: x['scheduled_seconds'])
                local = p.parent / Path(final['path']).name
                local.unlink()
                local.symlink_to(other)
                final['sha256'] = r.sha(other)
                p.write_text(json.dumps(record))
            result = r.compare(r.records(root), self.ref)
            self.assertEqual(result['summary'], {'same': 126, 'changed': 2, 'missing': 0})
            self.assertEqual({x['key'] for x in result['keys'] if x['category'] == 'changed'}, set(keys[:2]))
            with patch.object(r.subprocess, 'run') as call:
                sheet_out = root / 'sheet'
                sheet_out.mkdir()
                suspects = sum(x['semantic']['class'] == 'suspect' for x in result['keys'])
                self.assertEqual(r.changed_sheet(result, sheet_out, r.REPO / 'scripts/lab/contact_sheet.sh'), suspects)
                if suspects:
                    self.assertEqual(len(call.call_args.args[0][7:]), suspects)
                else:
                    call.assert_not_called()
            print('KNOWN_ANSWER t3 two changed: same=126 changed=2 missing=0; byte changes remain evidence; sheet uses semantic suspects')

    def test_driver_canonical_symlink_view_includes_all_128(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            source, view = root / 'source', root / 'final' / d.SERIAL
            self.fixture(source)
            view.mkdir(parents=True)
            for key in self.ref:
                (view / key).symlink_to(source / d.SERIAL / key, target_is_directory=True)
            self.assertEqual(r.compare(r.records(root / 'final'), self.ref)['summary'],
                             {'same': 128, 'changed': 0, 'missing': 0})

    def test_missing_key_is_not_same(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            self.fixture(root)
            key = next(iter(self.ref))
            (root / d.SERIAL / key / 'record.json').unlink()
            self.assertEqual(r.compare(r.records(root), self.ref)['summary']['missing'], 1)

    def test_lost_final_image_cannot_fall_back_to_t5(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            self.fixture(root)
            key = next(k for k, v in self.ref.items() if v['image'])
            p = root / d.SERIAL / key / 'record.json'
            record = r.read(p)
            max(record['screenshots'], key=lambda x: x['scheduled_seconds'])['captured'] = False
            p.write_text(json.dumps(record))
            rows = r.compare(r.records(root), self.ref)
            self.assertEqual(next(v for v in rows['keys'] if v['key'] == key)['category'], 'missing')

    def test_duplicate_observations_refuse(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            self.fixture(root)
            key = next(iter(self.ref))
            duplicate = root / 'duplicate'
            duplicate.mkdir()
            shutil.copyfile(root / d.SERIAL / key / 'record.json', duplicate / 'record.json')
            with self.assertRaisesRegex(ValueError, 'duplicate'):
                r.records(root)


class DriverPreparationTests(unittest.TestCase):
    def prepare(self, out, tiers=None):
        return d.prepare(d.BASE / 'demo-manifest.json', tiers or d.HERE / 'shot-tiers.json',
                         d.BASE / 't3/install-index-final.json', out,
                         '131b8ff9-2ead-4ee0-afe4-8700433d8bec',
                         d.MASTER / 'benchmark/2026-10-03-u13-stage-b/61b/smoke-61b.json')

    def test_prepare_disabled_all_128_reuses_t3_no_device_calls(self):
        with tempfile.TemporaryDirectory() as tmp, patch.object(d.subprocess, 'run', side_effect=AssertionError('device call forbidden')):
            out = Path(tmp) / 'round'
            cfg = self.prepare(out)
            self.assertFalse(cfg['execution_enabled'])
            self.assertEqual(len(d.SERIAL), 32)
            keys = []
            for path in cfg['windows']:
                plan = r.read(d.expand(path))
                self.assertFalse(plan['execution_enabled'])
                self.assertEqual(plan['serial'], d.SERIAL)
                self.assertEqual((plan['window_limit_minutes'], plan['stop_new_tests_by_minute']), (45, 35))
                self.assertEqual(plan['demo_mode'], 'launch')
                self.assertIsNotNone(plan['before_unlock'])
                for shard in plan['shards']:
                    keys.extend(d.expand(shard['keys_file']).read_text().split())
            self.assertEqual(len(keys), 128)
            self.assertEqual(len(set(keys)), 128)
            self.assertFalse(cfg['special_slots']['boatattack']['enabled'])
            self.assertEqual(cfg['special_slots']['toutiao']['launch'], 'foreground-desktop-click')
            self.assertFalse(cfg['special_slots']['toutiao']['enabled'])
            print('KNOWN_ANSWER driver: 128 unique keys / 8 disabled windows / no device calls')

    def test_selected_serial_propagates_to_all_plans_and_round(self):
        for serial in sorted(d.ALLOWED_SERIALS):
            with self.subTest(serial=serial), tempfile.TemporaryDirectory() as tmp:
                cfg = d.prepare(d.BASE / 'demo-manifest.json', d.HERE / 'shot-tiers.json',
                                d.BASE / 't3/install-index-final.json', Path(tmp) / 'round',
                                '131b8ff9-2ead-4ee0-afe4-8700433d8bec',
                                d.MASTER / 'benchmark/2026-10-03-u13-stage-b/61b/smoke-61b.json', serial=serial)
                self.assertEqual(cfg['serial'], serial)
                self.assertTrue(all(r.read(d.expand(p))['serial'] == serial for p in cfg['windows']))
                self.assertFalse(any(v['enabled'] for v in cfg['special_slots'].values()))

    def test_unlisted_serial_refused_before_file_or_device_access(self):
        with tempfile.TemporaryDirectory() as tmp, patch.object(d.subprocess, 'run', side_effect=AssertionError('device call forbidden')):
            with self.assertRaisesRegex(ValueError, 'whitelist'):
                d.prepare(Path('missing'), Path('missing'), Path('missing'), Path(tmp) / 'round',
                          '131b8ff9-2ead-4ee0-afe4-8700433d8bec', Path('missing'), serial='0' * 32)

    def test_identity_reader_selected_target_and_default_unchanged(self):
        identity = d.module('demo_selected_identity', d.BASE / 't3/verify_identity.py')
        self.assertEqual(identity.Reader(Path('.')).serial, d.SERIAL)
        self.assertEqual(identity.Reader(Path('.'), '5cd1e3dd00000000000000000923012c').serial,
                         '5cd1e3dd00000000000000000923012c')
        with self.assertRaisesRegex(ValueError, 'whitelist'):
            identity.Reader(Path('.'), '0' * 32)

    def test_unbound_specials_refuse_before_device_access(self):
        with tempfile.TemporaryDirectory() as tmp:
            out = Path(tmp) / 'round'
            cfg = self.prepare(out)
            cfg['special_slots']['toutiao']['enabled'] = True
            with self.assertRaisesRegex(ValueError, 'Toutiao'):
                d.validate_special_slots(cfg)
            cfg['special_slots']['toutiao']['enabled'] = False
            cfg['special_slots']['boatattack']['enabled'] = True
            with self.assertRaisesRegex(ValueError, 'BoatAttack'):
                d.validate_special_slots(cfg)

    def test_tier_sha_package_drift_refuse(self):
        with tempfile.TemporaryDirectory() as tmp:
            tmp = Path(tmp)
            tiers = r.read(d.HERE / 'shot-tiers.json')
            tiers['apps'][0]['apk_sha256'] = '0' * 64
            p = tmp / 'tiers.json'
            p.write_text(json.dumps(tiers))
            with self.assertRaisesRegex(ValueError, 'tier identity'):
                self.prepare(tmp / 'round', p)

    def test_driver_no_authorization_no_execution(self):
        with tempfile.TemporaryDirectory() as tmp, patch.object(d.subprocess, 'run', side_effect=AssertionError('device call forbidden')):
            out = Path(tmp) / 'round'
            self.prepare(out)
            with self.assertRaisesRegex(ValueError, 'authorization'):
                d.execute(out, '')

    def test_shard_failure_stops_before_next_window(self):
        with tempfile.TemporaryDirectory() as tmp:
            out = Path(tmp) / 'round'
            cfg = self.prepare(out)
            calls = []
            def run(args, **kw):
                calls.append(args)
                rc = 2 if any(str(x).endswith('demo_board_run.py') for x in args) else 0
                return type('Result', (), {'returncode': rc})()
            with patch.object(d, 'resolve_inputs'), patch.object(d, 'collect'), patch.object(d.subprocess, 'run', side_effect=run):
                with self.assertRaisesRegex(RuntimeError, 'window failed'):
                    d.execute(out, 'offline test authorization')
            self.assertEqual(sum(any(str(x).endswith('demo_board_run.py') for x in args) for args in calls), 1)
            self.assertFalse(r.read(d.expand(cfg['windows'][1]))['execution_enabled'])



class SemanticTriageKnownAnswers(unittest.TestCase):
    def test_outer_read_preview_nine_only_two_desktops(self):
        folder = r.REPO / 'benchmark/2026-10-10-5cd-demo-regression/preview-01'
        mapping = folder / 'compare/changed-sheet-mapping.json'
        if not mapping.is_file():
            self.skipTest('persistent preview evidence unavailable')
        rows = r.read(mapping)
        if not all(r.expand(x['source']).is_file() for x in rows):
            self.skipTest('persistent preview captures unavailable')
        found = {x['key'] for x in rows if r.screen_class(r.expand(x['source']))['class'] == 'suspect'}
        self.assertEqual(found, {'cv2-com-kaajjo-libresudoku', 'cv2-org-secuso-privacyfriendlyminesweeper'})
        report = {'keys': [dict(x, image=x['source'], baseline_image=x['baseline_image'],
                              semantic=r.screen_class(r.expand(x['source']))) for x in rows]}
        with tempfile.TemporaryDirectory() as tmp, patch.object(r.subprocess, 'run') as call:
            self.assertEqual(r.changed_sheet(report, Path(tmp), r.REPO / 'scripts/lab/contact_sheet.sh'), 2)
            self.assertEqual(len(call.call_args.args[0][7:]), 2)
        print('KNOWN_ANSWER preview-01: same_class=7 suspect=2; suspect sheet tiles=2')

    def test_black_white_and_nonblank_body(self):
        with tempfile.TemporaryDirectory() as tmp:
            for name, pixels, expected in (
                ('black', bytes([0,0,0])*160*256, 'suspect'),
                ('white', bytes([255,255,255])*160*256, 'suspect'),
                ('app', bytes([0,180,200])*160*256, 'same_class')):
                p = Path(tmp) / (name + '.ppm')
                p.write_bytes(b'P6\n160 256\n255\n' + pixels)
                self.assertEqual(r.screen_class(p)['class'], expected)
        print('KNOWN_ANSWER blank black/white=suspect; cyan app body=same_class')

    def test_decode_failure_is_suspect(self):
        with tempfile.TemporaryDirectory() as tmp:
            p = Path(tmp) / 'invalid.jpeg'; p.write_bytes(b'invalid')
            self.assertEqual(r.screen_class(p)['class'], 'suspect')

if __name__ == '__main__':
    unittest.main(verbosity=2)
