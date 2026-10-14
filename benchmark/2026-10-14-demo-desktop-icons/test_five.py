import unittest
import xml.etree.ElementTree as ET

import render_five


class SupplementResourceTests(unittest.TestCase):
    def test_clip_stack_and_original_path_preserved(self):
        xml = b'<vector xmlns:android="http://schemas.android.com/apk/res/android" android:viewportWidth="108" android:viewportHeight="108"><group><clip-path android:pathData="M0 0L108 0L108 108Z"/><clip-path android:pathData="M10 10L50 10L50 50Z" android:fillType="1"/><path android:pathData="M1 1L20 20" android:fillColor="#FF123456" android:strokeLineCap="1"/></group></vector>'
        svg = render_five.clipped_vector(xml).decode()
        self.assertIn('source-clip-1', svg)
        self.assertIn('source-clip-2', svg)
        self.assertIn('clip-rule="evenodd"', svg)
        self.assertIn('stroke-linecap="round"', svg)
        self.assertIn('M1 1L20 20', svg)

    def test_unsupported_clip_attributes_fail_not_invented(self):
        xml = b'<vector xmlns:android="http://schemas.android.com/apk/res/android" android:viewportWidth="108" android:viewportHeight="108"><clip-path android:pathData="M0 0Z" android:unknown="1"/></vector>'
        with self.assertRaises(ValueError):
            render_five.clipped_vector(xml)

    def test_five_exact_packages_no_original_three(self):
        self.assertEqual(len(render_five.PACKAGES), 5)
        self.assertNotIn('org.tasks', render_five.PACKAGES)
        self.assertNotIn('app.varlorg.unote', render_five.PACKAGES)
        self.assertNotIn('com.alxgnon.postwriter', render_five.PACKAGES)


if __name__ == '__main__':
    unittest.main()
