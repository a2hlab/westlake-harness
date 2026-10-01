import json
from pathlib import Path
import tempfile
import unittest

import predict
import scan_webview as scan

HERE = Path(__file__).resolve().parent


class IdentityTests(unittest.TestCase):
    def test_changed_apk_refused(self):
        with tempfile.TemporaryDirectory() as directory:
            path=Path(directory)/'input.apk'
            path.write_bytes(b'drift')
            with self.assertRaisesRegex(ValueError, 'hash mismatch'):
                scan.inspect(dict(path=str(path),key='fixture',apk_sha256='0'*64), {})

    def test_incomplete_cohort_refused(self):
        with self.assertRaisesRegex(ValueError, 'seven-key'):
            predict.build(dict(apps=[]), {})


class ScopeTests(unittest.TestCase):
    def test_subclass_and_resource_comments(self):
        self.assertTrue(scan.web_owner('Lapp/Custom;', {'Lapp/Custom;':scan.WEBVIEW}))
        refs=scan.layout_mentions([dict(instruction='const v0, #float 1.8e38 // #7f0b001c',line=1)], {'0x7f0b001c'})
        self.assertEqual(refs[0]['resource'],'0x7f0b001c')

    def test_fragment_is_not_automatically_later(self):
        result=predict.generate()
        self.assertTrue(all(row['webview_scope']=='startup-required' for row in result['rows']))
        rows={row['short']:row for row in result['rows']}
        self.assertTrue(any(site['fragment_callback'] for site in rows['jslab']['unanchored_or_callback_sites']))
        self.assertTrue(rows['jiten-webview']['layout_resources'])
        self.assertIn('Capacitor',rows['yam']['next_wall_candidate'])


class ReplayTests(unittest.TestCase):
    def test_predicted_artifacts_replay(self):
        result=predict.generate()
        self.assertEqual(json.loads((HERE/'results.json').read_text()), result)
        self.assertEqual((HERE/'PREDICTIONS.csv').read_text(),predict.csv_text(result))
        self.assertEqual(result['counts']['predicted_functional_lit'],0)
        self.assertEqual(result['counts']['native_chrome_fallback_candidates'],2)

    def test_settings_are_not_interface_proxy(self):
        evidence=json.loads((HERE/'provider-evidence.json').read_text())
        self.assertEqual(evidence['unchanged_framework']['artifact_identity_exit'],0)
        self.assertEqual(evidence['framework']['classes'][scan.SETTINGS],'Ljava/lang/Object;')
        kinds=json.loads((HERE/'class-kinds.json').read_text())
        self.assertNotIn('INTERFACE',kinds['class_flags'][scan.SETTINGS])
        self.assertIn('INTERFACE',kinds['class_flags']['Landroid/webkit/WebViewProvider;'])
        methods=evidence['runtime']['methods']
        zero=next(row for key,row in methods.items() if 'ZeroHandler;->invoke' in key)
        text='\n'.join(row['instruction'] for row in zero['instructions'])
        self.assertIn('Ljava/lang/Class;.isInterface',text)
        self.assertIn('return-object v6',text)
        self.assertTrue(any('WebViewProvider;.getSettings' in row['instruction']
            for row in evidence['framework']['methods']['Landroid/webkit/WebView;->getSettings()Landroid/webkit/WebSettings;']['instructions']))


if __name__ == '__main__':
    unittest.main()
