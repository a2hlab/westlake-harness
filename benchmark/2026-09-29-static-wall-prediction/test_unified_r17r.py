#!/usr/bin/env python3
import struct
import unittest
from extract_unified_failures import select
from rules_unified_r17r import requirement, inspect_method, FAMILY
from scan_unified_audio import dex_references
from score_unified_r17r import actual_family, lighting_metric


def miniature_dex(local_definition=False):
    """One external SoundPool.Builder.build reference; optionally APK-defined."""
    strings = [b'Landroid/media/SoundPool$Builder;', b'Landroid/media/SoundPool;', b'build', b'L']
    data = bytearray(224)
    data[:8] = b'dex\n035\0'
    struct.pack_into('<I', data, 40, 0x12345678)
    for offset, value in [(56,4),(60,112),(64,2),(68,128),(72,1),(76,136),(88,1),(92,148),
                          (96,int(local_definition)),(100,160)]:
        struct.pack_into('<I',data,offset,value)
    struct.pack_into('<II',data,128,0,1)
    struct.pack_into('<III',data,136,3,1,0)
    struct.pack_into('<HHI',data,148,0,0,2)
    for i,string in enumerate(strings):
        struct.pack_into('<I',data,112+4*i,len(data))
        data.extend(bytes([len(string)])+string+b'\0')
    return bytes(data)


def line(pid, message):
    return f'09-30 08:00:00.001 {pid} 11 I C00f00/AppSpawnXJava: {message}'


class Rules(unittest.TestCase):
    def test_two_native_mechanisms_remain_separate(self):
        self.assertEqual(requirement('android/media/SoundPool$Builder','build','()Landroid/media/SoundPool;'), 'soundpool-declared-library')
        self.assertEqual(requirement('android/media/AudioAttributes$Builder','setLegacyStreamType','(I)Landroid/media/AudioAttributes$Builder;'), 'audio-product-strategy-jni')

    def test_unrelated_audio_and_app_lookalikes_do_not_match(self):
        self.assertIsNone(requirement('app/media/SoundPool$Builder','build','()Landroid/media/SoundPool;'))
        self.assertIsNone(requirement('android/media/AudioAttributes$Builder','setUsage','(I)Landroid/media/AudioAttributes$Builder;'))
        self.assertIsNone(requirement('android/media/SoundPool$Builder','build','()V'))

    def test_external_reference_and_apk_definition_are_distinct(self):
        refs=list(dex_references(miniature_dex()))
        self.assertEqual(len(refs),1)
        self.assertEqual(refs[0]['method_id_offset'],148)
        self.assertEqual(requirement(**{k:refs[0][k] for k in ('owner','name','signature')}),'soundpool-declared-library')
        self.assertEqual(list(dex_references(miniature_dex(True))),[])
        with self.assertRaises(ValueError):list(dex_references(b'not a dex'))

    def test_instruction_scanner_preserves_witness_and_uncertainty(self):
        result=inspect_method('sample/App.onResume()V','classes2.dex',[
            ('0002',42,'invoke-virtual {v0}, Landroid/media/SoundPool$Builder;.build:()Landroid/media/SoundPool;')])
        self.assertEqual(len(result),1)
        self.assertEqual(result[0]['line'],42)
        self.assertEqual(result[0]['missing_implementation'],'unknown')
        self.assertEqual(result[0]['family'],FAMILY)

    def test_first_bind_failure_is_not_last_derived_crash(self):
        lines=[line(100,'nativeOnScheduleLaunchApplication ENTRY bundle=sample.app extra'),
               line(99,'J_invokeStaticMain_main_threw: unrelated'),
               line(100,'[EARLY-TF] reflect FAILED: benign'),
               line(100,'[B43-BIND] ensureBindApplication FAILED: wrapper'),
               line(100,'Caused by: missing library'),
               line(100,'J_invokeStaticMain_main_threw: lateinit instance')]
        self.assertEqual(select(lines,'sample.app')['anchor']['line'],4)
        self.assertEqual(select(lines,'sample.app',False)['anchor']['line'],6)
        self.assertIsNone(select(lines,'different.app')['anchor'])

    def test_lit_error_and_egl_are_not_audio_first_wall(self):
        row={'lit':False,'stage':'native-fatal','chain':[{'text':'ASSERT FAILED EGL_NO_SURFACE'}]}
        self.assertEqual(actual_family(row),'egl-window-recreation')
        row['lit']=True
        self.assertEqual(actual_family(row),'none-signed-lit')

    def test_dex_style_missing_method_is_classified(self):
        row={'lit':False,'stage':'main-threw','chain':[{'text':'No virtual method setProperty(Ljava/lang/String;Ljava/lang/Object;)V in class Lorg/ccil/cowan/tagsoup/Parser;'}]}
        self.assertEqual(actual_family(row),'tagsoup-api')

    def test_binary_metric_excludes_abstentions_from_accuracy(self):
        rows=[{'key':k,'actual_lit':lit,'r17o':pred} for k,lit,pred in
              [('a',True,'亮'),('b',True,'推进'),('c',False,'unknown'),('d',False,'不变')]]
        score=lighting_metric(rows,'r17o')
        self.assertEqual(score['lit_hits'],1)
        self.assertEqual(score['lit_not_predicted'],1)
        self.assertEqual(score['strict_bright_unchanged_samples'],2)
        self.assertEqual(score['strict_correct'],2)


if __name__ == '__main__':
    unittest.main()
