import importlib.util
import json
import unittest
from pathlib import Path

HERE = Path(__file__).resolve().parent
SPEC = importlib.util.spec_from_file_location('m2_collect', HERE / 'collect.py')
COLLECT = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(COLLECT)


class EvidenceTests(unittest.TestCase):
    def setUp(self):
        self.data = json.loads((HERE / 'results.json').read_text())

    def test_six_app_pid_provider_routes_and_html_failures(self):
        self.assertEqual(len(self.data['rows']), 6)
        for row in self.data['rows']:
            text = '\n'.join(item['text'] for item in row['events'])
            self.assertIn('type-zero stub', text)
            self.assertIn('enriched WebViewFactoryProvider seeded', text)
            self.assertIn('unavailable (no ASX_WEBVIEW_APK provider)', text)
            self.assertIn('WESTLAKE_HTML_COMPAT env set', text)
            self.assertIn('path is outside app domain:', text)
            self.assertFalse(row['maps'])
            self.assertTrue(all(item['pid'] in row['app_pids'] for item in row['events']))
            self.assertTrue(any('AppSpawnXJava' in item['text'] for item in row['events']))

    def test_lit_control_has_native_controls_not_a_different_renderer(self):
        row = self.data['rows'][-1]
        self.assertEqual(row['signed']['verdict'], 'lit')
        text = '\n'.join(item['text'] for item in row['events'])
        self.assertIn('1200x1539', text)
        self.assertIn("text='Load'", text)
        self.assertIn("text='WebView'", text)
        for white in self.data['rows'][:-1]:
            self.assertIn(white['signed']['verdict'], ['alive-white-window', 'alive-black-window'])
            self.assertIn('1200x1920', '\n'.join(item['text'] for item in white['events']))

    def test_no_renderer_or_html_unlock_is_claimed(self):
        verdict = self.data['verdict']
        self.assertEqual(verdict['first_fatal_moves'], 0)
        self.assertEqual(verdict['html_compat_restoration_moves'], 0)
        self.assertEqual(verdict['measured_new_lit'], 0)
        self.assertEqual(verdict['conditional_renderer_content_wall_upper_bound'], 5)
        for row in self.data['rows'][:-1]:
            self.assertEqual(row['prediction']['renderer_content_wall_moves'], 'conditional')
            self.assertGreater(row['coverage']['hilog_end_to_t20_gap_seconds'], 0)

    def test_exact_jar_identity_and_sibling_path_boundary(self):
        components = self.data['components']
        self.assertTrue(components['effective_runtime_sha256'].startswith('5ae3dd29'))
        self.assertNotEqual(components['effective_runtime_sha256'], components['stale_native_payload_runtime_sha256'])
        self.assertTrue(all('jnigraphics' in path for path in components['webview_related_package_entries']))
        sibling = COLLECT.WS / 'westlake-harness-u7-executor/benchmark/example'
        self.assertEqual(COLLECT.portable(sibling), '$WORKSPACES/westlake-harness-u7-executor/benchmark/example')
        for row in self.data['rows']:
            self.assertFalse(row['native_entries'])


if __name__ == '__main__':
    unittest.main(verbosity=2)
