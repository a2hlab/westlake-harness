import copy
import json
from pathlib import Path
import sys
import tempfile
import unittest

import collect
import native_audit
import report
import rules

HERE=Path(__file__).resolve().parent


class IdentityTests(unittest.TestCase):
    def test_changed_apk_refused(self):
        with tempfile.TemporaryDirectory() as directory:
            path=Path(directory)/'test.apk'
            path.write_bytes(b'not-the-pinned-apk')
            with self.assertRaisesRegex(ValueError,'hash mismatch'):
                collect.inspect(dict(path=str(path),apk_sha256='0'*64,key='fixture'),{})

    def test_incomplete_cohort_refused(self):
        with self.assertRaisesRegex(ValueError,'166-key'):
            report.build(dict(apps=[]),dict(rows=[],java=dict(methods={})),{}, {})

    def test_deployed_pins_and_original_inputs(self):
        native=json.loads((HERE/'native-constructors.json').read_text())
        for name,row in native['artifacts'].items():
            target='/system/'+name.removeprefix('payload/')
            all_pins=json.loads((report.ROOT/'benchmark/2026-10-01-u7-prospective/v1/expected-run.json').read_text())
            pins={**all_pins['runtime_files'],**all_pins['boot_files']}
            self.assertEqual(row['sha256'],pins[target])
        self.assertEqual(native['artifact_identity']['exit_code'],0)
        self.assertEqual(len(native['artifact_identity']['stdout'].splitlines()),3)


class ActionbarTests(unittest.TestCase):
    def test_style_inheritance_variants_and_namespaces(self):
        text='''    resource 0x7f100001 style/Base
      () (style) size=2
        windowActionBar(0x7f040001)=true
        android:windowActionBar(0x010102cd)=true
    resource 0x7f100002 style/NoActionBar
      () (style) size=1 parent=style/Base (0x7f100001)
        windowActionBar(0x7f040001)=false
      (v21) (style) size=1 parent=style/Base (0x7f100001)
        windowActionBar(0x7f040001)=false
    resource 0x7f100003 style/Mixed
      () (style) size=1
        windowActionBar(0x7f040001)=false
      (night) (style) size=1
        windowActionBar(0x7f040001)=true
'''
        styles=rules.parse_styles(text)
        value=rules.theme('@0x7f100002',styles)
        self.assertIs(value['flags']['windowActionBar'],False)
        self.assertIs(value['flags']['android:windowActionBar'],True)
        self.assertIn('no-actionbar',value['status'])
        self.assertNotIn('windowActionBar',rules.theme('@0x7f100003',styles)['flags'])
        self.assertEqual(rules.theme('@0x01030001',styles)['flags'],{})

    def test_inherited_post_create_is_lifecycle_not_unanchored(self):
        classes={'Lapp/Main;':'Lapp/Base;','Lapp/Base;':'Landroidx/appcompat/app/AppCompatActivity;'}
        method='Lapp/Base;->onPostCreate(Landroid/os/Bundle;)V'
        methods={method:dict(owner='Lapp/Base;',name='onPostCreate',branches=0,callees=set())}
        self.assertIn(method,rules.roots('app.Main',classes,methods))
        visited,capped=rules.reach(rules.roots('app.Main',classes,methods),classes,methods)
        self.assertIn(method,visited)
        self.assertFalse(capped)
        self.assertTrue(rules.actionbar(dict(owner='Lapp/Main;',name='setSupportActionBar'),classes))
        self.assertFalse(rules.actionbar(dict(owner='Lunrelated/Main;',name='setSupportActionBar'),classes))

    def test_startup_vs_later_activity_and_library_controls(self):
        result=report.generate()
        rows={row['key']:row for row in result['rows']}
        for key in ['cv2-org-secuso-privacyfriendlymemory','cv2-org-secuso-privacyfriendlyyahtzeedicer']:
            self.assertTrue(any(site['theme_contract_candidate'] for site in rows[key]['actionbar']))
            self.assertEqual(rows[key]['calibration']['cluster'],'appcompat-actionbar-theme')
        self.assertTrue(any(site['classification']=='later-activity-lifecycle' and site['theme_contract_candidate'] for site in rows['cv2-org-secuso-privacyfriendlydame']['actionbar']))
        self.assertEqual(rows['cv2-com-page-bizzle']['actionbar'],[])


class NativeTests(unittest.TestCase):
    def test_unconditional_conditional_and_not_a_safety_claim(self):
        throw=dict(address=12,text='bl 0x13bb9c <_Z10doThrowIAEP7_JNIEnvPKc>')
        self.assertEqual(rules.throw_class([throw])['status'],'unconditional-normal-path-direct-throw')
        self.assertEqual(rules.throw_class([dict(address=8,text='cbnz x20, 0x20'),throw])['status'],'conditional-direct-throw')
        self.assertEqual(rules.throw_class([dict(address=8,text='ret')])['status'],'no-direct-throw-witness')

    def test_creator_scope_does_not_include_destructors(self):
        profile=dict(methods={
            'android/graphics/EmbossMaskFilter.nativeConstructor([FFFF)J':{},
            'android/graphics/LinearGradient.nativeCreate(JFFFF[J[FIJ)J':{},
            'android/graphics/MaskFilter.nativeDestructor(J)V':{},
            'android/graphics/Shader.nativeGetFinalizer()J':{}})
        self.assertEqual(len(native_audit.creators(profile)),2)

    def test_real_emboss_and_unknown_ownership_preserved(self):
        native=json.loads((HERE/'native-constructors.json').read_text())
        rows={row['id']:row for row in native['rows']}
        emboss=rows['android/graphics/EmbossMaskFilter.nativeConstructor([FFFF)J']
        self.assertEqual(emboss['jni_status'],'registered')
        self.assertEqual(emboss['implementations'][0]['body']['address'],'0x1434bc')
        self.assertEqual(emboss['implementations'][0]['throw']['status'],'unconditional-normal-path-direct-throw')
        bitmap=rows['android/graphics/BitmapShader.nativeCreate(JJIIZZ)J']
        self.assertEqual(bitmap['jni_status'],'unknown')
        timings=report.native_timings(native)
        self.assertEqual(timings[emboss['id']],'eager-Java-constructor')
        self.assertIn('non-constructor',timings[bitmap['id']])


class ReplayTests(unittest.TestCase):
    def test_all_rows_and_rankings_replay(self):
        result=report.generate()
        self.assertEqual(json.loads((HERE/'results.json').read_text()),result)
        self.assertEqual((HERE/'PREDICTIONS.csv').read_text(),report.csv_text(result))
        self.assertEqual(len(result['rows']),166)
        self.assertEqual(result['graphics_ranked'][0]['consumer_keys'],['cv2-anupam-acrylic'])
        self.assertEqual(result['graphics_ranked'][0]['observed_blocked_count'],1)
        self.assertTrue(all(row['unconditional_throw_callsite_upper_bound']==0 for row in result['graphics_ranked'][1:]))

    def test_source_byte_hashes_and_positive_controls(self):
        facts=report.load(HERE/'facts.json.gz.b64')
        self.assertEqual(sum(len(app['dex']) for app in facts['apps']),350)
        labels,pins=report.visual_labels()
        self.assertEqual(sum(row['status']=='lit' for row in labels.values()),99)
        native=json.loads((HERE/'native-constructors.json').read_text())
        self.assertEqual(native['runtime_profile_sha256'],collect.digest((native_audit.V1/'runtime-profile.json.gz.b64').read_bytes()))


if __name__=='__main__':
    unittest.main()
