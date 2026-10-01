import json
import importlib.util
from pathlib import Path
import struct
import tempfile
import unittest

import audit as registrations
import scan_consumers as consumers
REPORT_SPEC = importlib.util.spec_from_file_location('registration_impact_report',Path(__file__).parent/'report.py')
impact_report = importlib.util.module_from_spec(REPORT_SPEC)
REPORT_SPEC.loader.exec_module(impact_report)
import inspect_first_fatal as first_fatal_followup


class InventoryTests(unittest.TestCase):
    def test_comment_dispatch_not_active(self):
        text = 'static const HwuiReg kHwuiRegFns[] = {\n// {"Ignored", "_Z30register_android_ignoredP7_JNIEnv"},\n{"Graphics", "_Z34register_android_graphics_GraphicsP7_JNIEnv"},\n};'
        rows = registrations.dispatch(text)
        self.assertEqual(len(rows),1)
        self.assertEqual(rows[0]['function'],'register_android_graphics_Graphics')
        self.assertEqual(rows[0]['line'],3)
        self.assertEqual(rows[0]['mode'],'dlsym-whole-function-delegation')

    def test_label_is_not_the_called_entrypoint(self):
        text = 'static const RegJNIRec kRegJNI[] = { {"register_android_Label",register_android_Actual} };'
        row = registrations.dispatch(text)[0]
        self.assertEqual(row['function'],'register_android_Actual')
        self.assertEqual(row['label'],'register_android_Label')

    def test_nested_body_keeps_coordinates(self):
        text = '// ignored\nint register_android_Test(JNIEnv* env) {\n  if (env) { gTestOffsets.field = env->GetFieldID(clazz,"}","J"); }\n  return 0;\n}\n'
        result = registrations.functions(text)[0]
        self.assertEqual(result['first_line'],2)
        self.assertEqual(result['last_line'],5)
        self.assertEqual(result['direct_initializer_lines'][0]['line'],3)
        self.assertIn('return 0;',result['body'])

    def test_incomplete_body_refused(self):
        with self.assertRaisesRegex(ValueError,'Unbalanced'):
            registrations.functions('int register_android_Test(JNIEnv* env) {')

    def test_provider_owner_name_is_not_a_prefix_match(self):
        self.assertEqual(registrations.function_name('_Z39register_android_graphics_BitmapFactoryP7_JNIEnv'),'register_android_graphics_BitmapFactory')
        self.assertNotEqual(registrations.function_name('_Z39register_android_graphics_BitmapFactoryP7_JNIEnv'),'register_android_graphics_Bitmap')

    def test_cache_write_inventory_not_all_mentions(self):
        self.assertEqual(registrations.cache_writes('gAssetManagerOffsets.mObject = find(); use(gOtherOffsets); if (gOtherOffsets == 0) {}'),['gAssetManagerOffsets.mObject'])


class IdentityTests(unittest.TestCase):
    def test_source_hash_drift_refused(self):
        with self.assertRaisesRegex(ValueError,'identity drift'):
            registrations.verify(b'changed','0'*64)

    def test_AOSP16_not_AOSP14(self):
        with self.assertRaisesRegex(ValueError,'Unverified'):
            registrations.reference(Path('/unused'),dict(revision='refs/tags/android-16.0.0_r4'))

    def test_exact_reference_file_hash_checked(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            source = root/'Test.cpp'
            source.write_text('int register_android_Test(JNIEnv* env) { return 0; }')
            provenance = dict(revision='refs/tags/android-14.0.0_r1',frameworks_base_commit='a'*40,files={'Test.cpp':registrations.sha(source.read_bytes())})
            originals,contexts = registrations.reference(root,provenance)
            self.assertEqual(list(originals),['register_android_Test'])
            source.write_text('changed')
            with self.assertRaisesRegex(ValueError,'identity drift'):
                registrations.reference(root,provenance)


class ConsumerTests(unittest.TestCase):
    def test_strong_weak_literal_and_substring_separate(self):
        parsed = dict(imports=[dict(name='AAssetManager_fromJava',weak=False),dict(name='ANativeWindow_fromSurface',weak=True),dict(name='dlsym',weak=False)])
        data = b'\x00AAssetManager_fromJava\x00AndroidBitmap_getInfo\x00AHardwareBuffer_lock\x00prefixAndroidBitmap_unlockPixels\x00'
        rows = consumers.exposure(data,parsed)
        self.assertEqual({row['symbol']:row['kind'] for row in rows},{'AAssetManager_fromJava':'strong-import','ANativeWindow_fromSurface':'weak-import','AndroidBitmap_getInfo':'literal-lookup-candidate','AHardwareBuffer_lock':'literal-lookup-candidate'})
        self.assertEqual(len([row for row in rows if 'file_offset' in row]),2)

    def test_literal_without_loader_is_unknown(self):
        rows = consumers.exposure(b'ANativeWindow_fromSurface\0',dict(imports=[]))
        self.assertEqual(rows[0]['kind'],'literal-only-unknown-use')


class InputTests(unittest.TestCase):
    def test_first_fatal_artifact_drift_refused(self):
        with self.assertRaisesRegex(ValueError,'artifact SHA drift'):
            first_fatal_followup.require(b'changed','0'*64)

    def test_nonzero_invalid_vtable_not_null_context(self):
        values=dict(x0=0x7f17252b4f,x8=0x7f0e749d1800,x19=1,x20=2,x21=3,x22=1)
        result=first_fatal_followup.crash_operand(values,values['x8'])
        self.assertFalse(result['null_pointer'])
        self.assertFalse(result['resource_pointer_eight_byte_aligned'])
        self.assertEqual(result['resource_index'],1)
        with self.assertRaisesRegex(ValueError,'Fault address'):
            first_fatal_followup.crash_operand(values,0)

    def test_disassembly_evidence_and_semantic_boundary(self):
        root=Path(__file__).parent
        result=json.loads((root/'NATIVE-FIRST-FATAL.json').read_text())
        self.assertEqual(result['glmark']['field'],'mObject')
        self.assertFalse(result['glmark']['direct_GetFieldID_table_load_in_scene_function'])
        self.assertFalse(result['ath0']['null_pointer'])
        for name,digest in result['evidence_sha256'].items():
            self.assertEqual(first_fatal_followup.sha((root/'evidence'/name).read_bytes()),digest)

    def test_absent_custom_name_not_missing_reference(self):
        row = dict(function='register_android_media_AudioProductStrategy', AOSP14r1=[])
        reference = dict(outer_full_tree_absence_attestation={row['function']:'full-tree absence'})
        self.assertEqual(impact_report.classify(row,reference),'Westlake-custom-name-absent-in-AOSP14r1')
        self.assertEqual(impact_report.classify(row,{}),'unknown-reference-entrypoint')

    def test_signoff_mismatch_refused(self):
        with self.assertRaisesRegex(ValueError,'cohort mismatch'):
            impact_report.join({},dict(apps=[]),{},dict(keys={}))

    def test_asset_reference_does_not_predict_unlocks(self):
        context,status = impact_report.relationship('AAssetManager_fromJava')
        self.assertIn('distinct',context)
        self.assertIn('unresolved',status)

    def test_machine_bundle_keeps_all_entries_and_unknowns(self):
        root = Path(__file__).parent
        evidence = json.loads((root/'REGISTRATIONS.json').read_text())
        reference = json.loads((root/'reference.json').read_text())
        summary = json.loads((root/'results.json').read_text())
        self.assertEqual(len(evidence['rows']),95)
        self.assertEqual(len(reference['files']),481)
        self.assertEqual(summary['proven_registration_side_effect_deaths'],0)
        self.assertIsNone(summary['predicted_unlock_count'])
        self.assertEqual(sum(row['reference_comparison']=='Westlake-custom-name-absent-in-AOSP14r1' for row in evidence['rows']),2)

    def test_sidecar_drift_refused(self):
        with self.assertRaisesRegex(ValueError,'SHA drift'):
            consumers.member('sidecar/test.so',b'changed','0'*64)

    def test_unsupported_ABI_is_not_AArch64_provider(self):
        data = b'\x7fELF\x02\x01'+b'\0'*10+struct.pack('<HHIQQQIHHHHHH',3,40,1,0,0,0,0,64,56,0,64,0,0)
        row = consumers.member('APK!/lib/armeabi-v7a/test.so',data)
        self.assertEqual(row['header'],'wrong-machine-for-arm64')
        self.assertEqual(row['scope'],'unsupported-or-invalid-not-clean')
        self.assertEqual(row['API_evidence'],[])

    def test_duplicate_or_incomplete_cohort_refused(self):
        with self.assertRaisesRegex(ValueError,'Incomplete'):
            consumers.summarize([])


if __name__=='__main__':
    unittest.main()
