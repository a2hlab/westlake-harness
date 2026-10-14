import hashlib
import json
import tempfile
import unittest
from pathlib import Path

import audit
import render_known_icons as render


class IconEvidenceTests(unittest.TestCase):
    def test_placeholder_never_matches_xml_artwork(self):
        self.assertEqual(audit.classify(audit.PLACEHOLDER, 'XML'), 'CONFIRMED_TEMPLATE_NOT_ORIGINAL_ARTWORK')

    def test_absent_bytes_remain_unknown(self):
        self.assertTrue(audit.classify(None, 'PNG').startswith('UNKNOWN'))

    def test_other_sha_not_automatically_match(self):
        self.assertTrue(audit.classify('a' * 64, 'PNG').startswith('UNKNOWN'))

    def test_exact_tile_not_other_package(self):
        app = dict(package='one.pkg', expected_desktop_ability='Activity')
        desktop = dict(pages=[dict(tag='page', visible_tiles=[dict(id='AppIconCommonView_other.pkg.Activity', visible='true', bounds='b')])])
        self.assertEqual(audit.exact_tiles(app, desktop), [])

    def test_route_b_tile_uses_explicit_launch_package(self):
        app = dict(package='com.ss.android.article.news', launch_package='org.westlake.imehost', expected_desktop_ability='EntryAbility')
        desktop = dict(pages=[dict(tag='page', visible_tiles=[dict(id='AppIconCommonView_org.westlake.imehost.EntryAbility', visible='true', bounds='b')])])
        self.assertEqual(len(audit.exact_tiles(app, desktop)), 1)

    def test_remote_local_and_bytes_all_required(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / 'icon').write_bytes(b'icon')
            digest = hashlib.sha256(b'icon').hexdigest()
            row = dict(equal=True, remote_sha256=digest, local_sha256=digest, local='icon')
            self.assertEqual(audit.verify_received(row, root), root / 'icon')
            (root / 'icon').write_bytes(b'foreign')
            with self.assertRaises(ValueError):
                audit.verify_received(row, root)

    def test_remote_mismatch_rejected(self):
        with self.assertRaises(ValueError):
            audit.verify_received(dict(equal=False), Path('.'))

    def test_vector_aspect_ratio_and_original_path(self):
        xml = b'<vector xmlns:android="http://schemas.android.com/apk/res/android" android:viewportWidth="20" android:viewportHeight="40"><path android:fillColor="#80FF0000" android:pathData="M0,0L20,40Z"/></vector>'
        svg = render.vector_svg(xml).decode()
        self.assertIn('viewBox="0 0 20.0 40.0"', svg)
        self.assertIn('M0,0L20,40Z', svg)
        self.assertIn('0.5019607843137255', svg)

    def test_unsupported_transform_rejected(self):
        xml = b'<vector xmlns:android="http://schemas.android.com/apk/res/android" android:viewportWidth="20" android:viewportHeight="40"><group android:rotation="45"/></vector>'
        with self.assertRaises(ValueError):
            render.vector_svg(xml)

    def test_unresolved_color_rejected(self):
        with self.assertRaises(ValueError):
            render.color('@7F000001')

    def test_repair_plan_stays_disabled(self):
        path = Path(__file__).parent / 'evidence/repair-plan.disabled.json'
        if not path.is_file():
            self.skipTest('Generated evidence not yet materialized; no artifact dependency')
        plan = json.loads(path.read_text())
        self.assertFalse(plan['execution_enabled'])
        self.assertEqual(len(plan['repairs']), 3)
        for row in plan['repairs']:
            self.assertFalse(row['execution_enabled'])
            self.assertIsNone(row['cache']['provider'])
            self.assertFalse(row['rollback']['enabled'])


if __name__ == '__main__':
    unittest.main()
