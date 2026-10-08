import copy
import csv
import json
from pathlib import Path
import re
import tempfile
import unittest
from unittest.mock import patch

import build_report as build


class InventoryTests(unittest.TestCase):
    def setUp(self):
        self.report = build.read('apps.json')
        self.rows = self.report['apps']
        self.inputs = build.read('inputs/apk-metadata.json')

    def test_exact_scope129(self):
        reference = build.read('inputs/reference.json')
        gains = build.read('inputs/window1-signoff.json')['summary']['gains']
        expected = {key for key, row in reference['keys'].items() if row['verdict'] == 'lit'}
        self.assertEqual(len(expected), 126)
        self.assertEqual(set(gains), {'vlc', 'termux', 'cv2-org-andresoviedo-dddmodel2'})
        self.assertEqual({row['key'] for row in self.rows}, expected | set(gains))
        self.assertEqual(len(self.rows), 129)

    def test_csv_json_equivalent(self):
        with (build.HERE / 'apps.csv').open(encoding='utf-8-sig', newline='') as stream:
            rows = list(csv.DictReader(stream))
        self.assertEqual(rows, self.rows)

    def test_duplicate_package_not_extra_application(self):
        self.assertEqual(self.report['distinct_packages'], 128)
        self.assertEqual(self.report['duplicate_packages'], {'com.github.ashutoshgngwr.noice': ['fd-noice', 'noice']})
        versions = {row['version'] for row in self.rows if row['key'] in ['fd-noice', 'noice']}
        self.assertEqual(versions, {'2.5.7', '2.5.1'})

    def test_apk_record_identities(self):
        for row in self.inputs:
            build.validate_identity(row)
            output = next(item for item in self.rows if item['key'] == row['key'])
            for field in ['package', 'apk_sha256', 'record_sha256', 'apk_path']:
                self.assertEqual(output[field], row[field])

    def test_identity_conflicts_reject(self):
        for field in ['key', 'package', 'apk_sha256']:
            row = copy.deepcopy(self.inputs[0])
            row['record_identity'][field] = 'bad'
            with self.assertRaisesRegex(ValueError, 'Identity conflict'):
                build.validate_identity(row)

    def test_chinese_resource_priority(self):
        labels = dict(default='Calculator', variants=[dict(locale='', value='Calculator'),
            dict(locale='zh-rTW', value='計算機'), dict(locale='zh-rCN', value='计算器')])
        selected = build.choose_name(labels, dict(name={'zh-CN': 'Metadata title'}), 'zh')
        self.assertEqual(selected, ('计算器', 'APK AndroidManifest/resource label', 'zh-rCN'))

    def test_missing_locale_keeps_brand_or_metadata(self):
        labels = dict(default='Brand', variants=[dict(locale='', value='Brand')])
        self.assertEqual(build.choose_name(labels, {}, 'zh')[0], 'Brand')
        self.assertEqual(build.choose_name(labels, dict(name={'zh-CN': '品牌'}), 'zh')[0], '品牌')
        self.assertEqual(build.choose_name(labels, {}, 'en')[0], 'Brand')

    def test_actual_chinese_resource_count_and_names(self):
        rows = [row for row in self.rows if row['name_zh_source'] == 'APK AndroidManifest/resource label']
        self.assertEqual(len(rows), 20)
        self.assertEqual(next(row['display_name_zh'] for row in self.rows if row['key'] == 'wikipedia'), '维基百科')
        self.assertEqual(next(row['display_name_zh'] for row in self.rows if row['key'] == 'fd-calendar'), '日历')
        self.assertTrue(all(row['display_name_zh'] and row['display_name_en'] for row in self.rows))
        self.assertTrue(all(not row[field].startswith('@') for row in self.rows for field in ['display_name_zh', 'display_name_en']))
        self.assertTrue(all(row['version'] not in ['', 'None'] and row['version_code'].isdigit() for row in self.rows))

    def test_source_not_guessed_from_key(self):
        vlc = next(row for row in self.rows if row['key'] == 'vlc')
        self.assertEqual(vlc['source'], '第三方 APK（APKPure）')
        self.assertEqual(vlc['source_status'], 'receipt-backed')
        noice = next(row for row in self.rows if row['key'] == 'noice')
        self.assertEqual(noice['source_status'], 'receipt-backed')
        self.assertTrue(all(row['source'] == 'cv2 语料（F-Droid）' for row in self.rows if row['key'].startswith('cv2-')))

    def test_unknown_source_stays_uncertain(self):
        row = dict(corpus=None, source_index_version_matches=[], input_receipt=None)
        self.assertEqual(build.classify_source(row)[0::2], ('uncertain', 'uncertain'))

    def test_purpose_evidence_and_single_sentence(self):
        metadata = build.read('inputs/fdroid-metadata.json')
        for row in self.rows:
            self.assertEqual(len(re.findall('[。！？]', row['purpose_zh'])), 1)
            self.assertTrue(row['purpose_zh'].endswith('。'))
            self.assertTrue(row['category'])
            reference = row['purpose_evidence'].split('#', 1)[1].split('/')
            package, field, locale = reference
            self.assertEqual(metadata[package][field][locale], row['purpose_evidence_text'])
            self.assertIn('not a platform functional-test', row['purpose_status'])
            self.assertIn('不表示全部功能', row['lighting_scope'])

    def test_missing_purpose_evidence_reject(self):
        original = build.read

        def missing(name):
            if name == 'inputs/fdroid-metadata.json':
                return {}
            return original(name)

        with patch.object(build, 'read', side_effect=missing):
            with self.assertRaisesRegex(ValueError, 'Missing purpose evidence'):
                build.assemble()

    def test_build_reproducible_without_artifacts_or_external_inputs(self):
        self.assertEqual(build.assemble(), self.report)
        with tempfile.TemporaryDirectory() as temporary:
            original = build.HERE
            with patch.object(build, 'HERE', Path(temporary)):
                with self.assertRaises(FileNotFoundError):
                    build.assemble()
            self.assertEqual(build.HERE, original)

    def test_all_report_paths_portable(self):
        serialized = json.dumps(self.report, ensure_ascii=False)
        self.assertNotIn('/Users/', serialized)
        self.assertTrue(all(row['apk_path'].startswith(('$WORKSPACES/', '$HOME/')) for row in self.rows))

    def test_results_hashes_and_no_device_action(self):
        results = build.read('results.json')
        self.assertEqual(results['apps_csv_sha256'], build.sha(build.HERE / 'apps.csv'))
        self.assertEqual(results['apps_json_sha256'], build.sha(build.HERE / 'apps.json'))
        self.assertEqual((results['board_operations'], results['network_operations'], results['screenshots_selected']), (0, 0, 0))


if __name__ == '__main__':
    unittest.main(verbosity=2)
