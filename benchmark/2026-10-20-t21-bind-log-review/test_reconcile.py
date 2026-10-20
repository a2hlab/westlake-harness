import unittest
import reconcile as r

def fixture():
 lines=[];regions=[]
 for base,path in [(0x10000000,'/data/local/tmp/asx/liboh_adapter_bridge.so'),(0x20000000,'/system/lib64/chipset-sdk-sp/libsurface.z.so'),(0x30000000,'/system/lib64/chipset-sdk-sp/libsurface.z.so')]:
  inode=1 if base==0x10000000 else 2
  regions.extend([f'{base:x}-{base+0x1000:x} r--p 00000000 103:20 {inode} {path}',f'{base+0x1000:x}-{base+0x200000:x} r-xp 00001000 103:20 {inode} {path}'])
 for name,offset in (r.OWNER|r.PROVIDER).items():
  base,path=(0x10000000,'/data/local/tmp/asx/liboh_adapter_bridge.so') if name in r.OWNER else (0x20000000,'/system/lib64/chipset-sdk-sp/libsurface.z.so')
  lines.append(f'[WL-R20-BIND] kind={name} fn={base+offset:#x} base={base:#x} file={path}\n')
 lines.append('[WL-R20-BIND] result=0 context=0x40000000 owner_base=0x10000000 provider_base=0x20000000\n')
 lines.append('[WL-R20-PAIR] seq=2 op=lock window=0x50000000 caller=0x60000000 rc=-5 request=1/0 handle=1/0 convert=1/0 map=1/-5 unmap=0/0 flush=0/0 abort=1/0 retained=1\n')
 return ''.join(lines).encode(),'\n'.join(regions).encode()
class Tests(unittest.TestCase):
 def test_two_same_inode_instances(self):
  log,m=fixture();o=r.reconcile(log,m,m,123);self.assertEqual(o['binding_layout'],'MATCH_OBSERVED_LAYOUT');self.assertEqual(o['events'][0]['source_offset'],123);self.assertEqual(o['first_observed_operation_failure']['stages']['map']['rc'],-5)
 def test_cross_instance_refuses(self):
  log,m=fixture();log=log.replace(b'fn=0x20064700 base=0x20000000',b'fn=0x30064700 base=0x30000000');self.assertEqual(r.reconcile(log,m,m)['binding_layout'],'UNKNOWN_OR_MISMATCH')
 def test_changed_inode_refuses(self):
  log,m=fixture();self.assertEqual(r.reconcile(log,m,m.replace(b'103:20 2',b'103:20 3'))['binding_layout'],'UNKNOWN_OR_MISMATCH')
 def test_truncation_and_missing_not_pass(self):
  log,m=fixture();self.assertEqual(r.reconcile(log[:80],m,m)['binding_layout'],'UNKNOWN_OR_MISMATCH');self.assertEqual(r.reconcile(b'',m,m)['operation_counts'],{})
 def test_no_private_config_output(self):
  log,m=fixture();prefix=b'{"secret_config":"do-not-copy"}\n';o=r.reconcile(prefix+log,m,m);self.assertNotIn('do-not-copy',str(o));self.assertEqual(o['events'][0]['source_offset'],len(prefix))
 def test_refusal_blocks_match(self):
  log,m=fixture();o=r.reconcile(log+b'[WL-R20-BIND] refuse=owner_provider_instance_unproven\n',m,m);self.assertEqual(o['binding_layout'],'UNKNOWN_OR_MISMATCH')
if __name__=='__main__':unittest.main()
