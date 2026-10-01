"""Unit format checks use tiny fixtures; real G1/G2 evidence is separate."""
import json,hashlib,sys,tempfile,unittest
from pathlib import Path
R=Path(__file__).resolve().parents[2];sys.path.insert(0,str(R/'scripts/lab'));import generation_bundle as b
class Bundle(unittest.TestCase):
 def setUp(self):
  self.tmp=tempfile.TemporaryDirectory();self.root=Path(self.tmp.name);self.native=self.root/'native';self.native.mkdir()
  self.rows=[]
  def member(rel,data=b'x',target=None):
   p=self.root/rel;p.parent.mkdir(parents=True,exist_ok=True);p.write_bytes(data);r=dict(source=rel,sha256=b.sha(p))
   if target:r['target']=target
   return r
  lib='payload/android/lib64/liboh_adapter_bridge.so';x=member('native/'+lib)
  m=dict(generation='a'*64,files={lib:x['sha256']},mounts=[dict(source='payload/android',target='/system/android')],live_hashes={'/system/android/lib64/liboh_adapter_bridge.so':x['sha256']},runtime_identity='deployment-only',bridge_sha256=x['sha256'])
  manifest=member('native/package.json',json.dumps(m).encode())
  for target in sorted(b.IMAGE_TARGETS|{b.FW+'adapter-mainline-stubs.jar'}):self.rows.append(member('members/'+Path(target).name,target=target))
  self.d=dict(schema='westlake-generation-bundle/v1',native=dict(directory='native',manifest=manifest),boot_group=dict(members=self.rows),runtime_jar=member('runtime.jar',target=b.FW+'oh-adapter-runtime.jar'),reference={k:member('ref-'+k,('b'*64+'  /system/'+k+'\n').encode()) for k in ['runtime','boot']})
 def tearDown(self):self.tmp.cleanup()
 def write(self): (self.root/'bundle.json').write_text(json.dumps(self.d))
 def reject(self):
  self.write()
  with self.assertRaises((ValueError,FileNotFoundError)):b.plan(self.root)
 def test_complete_group_and_rollback(self):
  self.write();p=b.plan(self.root);self.assertEqual(len(p['groups']['boot_image_and_stubs']['members']),28);self.assertFalse(p['device_writes']);self.assertFalse(p['deployable']);self.assertIn('G2',p['required_gates']);self.assertEqual(len(p['rollback']),6)
 def test_missing_image(self):self.d['boot_group']['members'].pop();self.reject()
 def test_duplicate_target(self):self.rows[1]['target']=self.rows[0]['target'];self.reject()
 def test_changed_byte(self):(self.root/self.rows[0]['source']).write_bytes(b'changed');self.reject()
 def test_escape(self):self.rows[0]['source']='../escape';self.reject()
 def test_absolute(self):self.rows[0]['source']='/tmp/escape';self.reject()
 def test_symlink(self):
  p=self.root/self.rows[0]['source'];p.unlink();p.symlink_to(self.root/self.rows[1]['source']);self.reject()
 def test_undeclared_native_payload(self):
  (self.native/'payload/extra.so').write_bytes(b'extra');self.reject()
 def test_runtime_alias_rejected(self):self.d['runtime_jar']['target']=self.rows[0]['target'];self.reject()
 def test_malformed_fingerprint(self):
  row=self.d['reference']['runtime'];p=self.root/row['source'];p.write_text('nothash /system/foo\n');row['sha256']=b.sha(p);self.reject()
 def test_missing_gates_never_readies(self):
  self.write();self.assertFalse(b.plan(self.root)['deployable'])
class ReceiptTests(unittest.TestCase):
 def test_input_output_identity_and_unknown(self):
  import u7_executor as u
  with tempfile.TemporaryDirectory() as td:
   root=Path(td);fw=root/'native/payload/android/framework';fw.mkdir(parents=True)
   for j in b.JARS:(fw/(j+'.jar')).write_bytes(j.encode())
   rows=[dict(target=p,sha256='a'*64) for p in b.IMAGE_TARGETS]
   rows.append(dict(target=b.FW+'adapter-mainline-stubs.jar',sha256='b'*64))
   d=dict(native=dict(directory='native'),boot_group=dict(members=rows))
   self.assertEqual(u.receipt_check(root,d,{})['status'],'unknown')
   r=dict(status='unknown',input_jars={j+'.jar':b.sha(fw/(j+'.jar')) for j in b.JARS},
          outputs={Path(p).name:'a'*64 for p in b.IMAGE_TARGETS})
   r['input_jars']['adapter-mainline-stubs.jar']='b'*64
   def write():
    p=root/'receipt.json';p.write_text(json.dumps(r));d['paired_build_receipt']=dict(source=p.name,sha256=b.sha(p))
   write();self.assertEqual(u.receipt_check(root,d,{})['status'],'unknown')
   r.update(status='verified',build_command='dex2oat ...',dex2oat_sha256='c'*64,
            toolchain_identity_sha256='d'*64,build_log_sha256='e'*64)
   write();self.assertEqual(u.receipt_check(root,d,{})['status'],'verified')
   r['input_jars']['core-oj.jar']='f'*64;write()
   with self.assertRaisesRegex(ValueError,'input_jars'):u.receipt_check(root,d,{})
if __name__=='__main__':unittest.main()
