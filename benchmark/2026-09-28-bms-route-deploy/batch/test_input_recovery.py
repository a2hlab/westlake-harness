import json
from pathlib import Path
import unittest
from unittest.mock import patch
import zipfile
import bms_batch as b
from test_native_sidecars import NativeSidecarTests, NativeBoard, elf, PKG, LIB

class ExactPayloadTests(unittest.TestCase):
    def setUp(self):
        self.f=NativeSidecarTests();self.f.setUp()
        self.payloads={'liba.so':b'PK\x03\x04original-zip-data','libb.so':elf(40)}
        for name,data in self.payloads.items():(self.f.libdir/name).write_bytes(data)
        self.repack()
        self.policy=self.f.root/'exceptions.json';self.approve()
        self.patch=patch.object(b,'NATIVE_DATA_EXCEPTIONS',self.policy);self.patch.start()
    def tearDown(self):self.patch.stop();self.f.tearDown()
    def repack(self,omit=None):
        with zipfile.ZipFile(self.f.apk,'w') as z:
            z.writestr('AndroidManifest.xml',b'unchanged manifest fixture')
            for name,data in self.payloads.items():
                if name!=omit:z.writestr('lib/arm64-v8a/'+name,data)
        self.f.original=self.f.apk.read_bytes();self.f.metadata['apk_sha256']=b.sha(self.f.apk);self.f.write_metadata()
    def approve(self):
        self.rows=[dict(bundle=PKG,abi='arm64-v8a',filename=n,sha256=b.sha(self.f.libdir/n),bytes=(self.f.libdir/n).stat().st_size,apk_sha256=b.sha(self.f.apk),status='approved',reason='test fixture only') for n,d in self.payloads.items()]
        self.policy.write_text(json.dumps(self.rows))
    def rejected(self):
        board=NativeBoard(self.f.original)
        out=self.f.root/('rejected-'+str(len(list(self.f.root.glob('rejected-*')))))
        rec=b.collect_app(board,self.f.entry,self.f.inputs,out,'/stage',wait_seconds=0)
        self.assertEqual(rec['status'],'app_failed');self.assertFalse(board.calls);return rec
    def test_exact_data_roundtrip(self):
        board,rec=self.f.collect(reinstall=True,shots=[1])
        self.assertTrue(rec['clicked']);self.assertEqual(board.original_send,self.f.original)
        for name,data in self.payloads.items():self.assertEqual(board.files[LIB+name],data)
        self.assertTrue(all(x['payload_kind']=='approved-packaged-data' for x in b.resolve_input(self.f.inputs,self.f.entry)['native_sidecars']))
    def test_all_identity_dimensions_are_required(self):
        for field,value in [('bundle','wrong.pkg'),('abi','armeabi-v7a'),('filename','other.so'),('sha256','0'*64),('bytes',1),('apk_sha256','f'*64),('status','draft')]:
            with self.subTest(field=field):
                self.approve();self.rows[0][field]=value;self.policy.write_text(json.dumps(self.rows));self.rejected()
    def test_changed_payload_even_with_updated_metadata_is_rejected(self):
        (self.f.libdir/'liba.so').write_bytes(b'PKchanged');self.f.write_metadata();self.rejected()
    def test_approved_payload_must_exist_in_original_apk(self):
        self.repack(omit='liba.so');self.approve();self.assertIn('not embedded',self.rejected()['error'])
    def test_archive_content_mismatch_is_rejected(self):
        self.payloads['liba.so']=b'PKdifferent-in-apk';self.repack();self.approve();self.assertIn('conflicts with embedded',self.rejected()['error'])
    def test_staged_data_corruption_still_rejected(self):
        board=NativeBoard(self.f.original);board.corrupt_stage=True
        board,rec=self.f.collect(board,reinstall=True,shots=[1]);self.assertFalse(rec['clicked']);self.assertIn('staged native sidecar hash',rec['error'])
    def test_missing_and_malformed_policy_rejected(self):
        for data in ['{}','[null]','not json']:
            self.policy.write_text(data);self.rejected()
        self.policy.unlink();self.rejected()

if __name__=='__main__':unittest.main()
