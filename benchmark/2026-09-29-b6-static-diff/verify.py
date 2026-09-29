#!/usr/bin/env python3
"""Meaningful offline checks: identity, coverage, evidence completeness, lossy normalization controls."""
import collections, json, re, unittest
from pathlib import Path
import compare as c
R=c.ROOT
class EvidenceTests(unittest.TestCase):
 def test_identity_and_coverage(self):
  res=json.loads((R/'results.json').read_text())
  self.assertEqual(res['device_commands'],0)
  for k,inputs in c.INPUTS.items():
   fs=json.loads((R/'evidence'/k/'functions.json').read_text())
   self.assertEqual(dict(collections.Counter(f['state'] for f in fs)),res['artifacts'][k]['functions']['counts'])
   for v,(p,prefix) in zip(('r155','new'),inputs):
    e=c.ELF(p,prefix);inv=json.loads((R/'evidence'/k/v/'inventory.json').read_text());cov=res['artifacts'][k]['functions']['coverage'][v]
    self.assertEqual(c.sha(e.data),inv['sha256']);self.assertEqual(inv['sha256'],res['artifacts'][k][v]['sha256'])
    self.assertEqual(len(inv['function_symbols']),cov['function_symbols'])
    self.assertEqual(sum(bool(f[v]) and not f['name'].startswith('block:') for f in fs),cov['function_symbols'])
    self.assertFalse(cov['uncovered']);self.assertEqual(cov['decoded_bytes'],cov['executable_section_bytes'])
    self.assertEqual(cov['decoded_instructions'],cov['covered_instructions'])
    llvm=(R/'evidence'/k/v/'relocations.txt').read_text()
    self.assertEqual(sum(inv['relocations'].values()),len(re.findall(r'R_AARCH64_',llvm)))
 def test_negative_controls(self):
  with self.assertRaisesRegex(ValueError,'identity mismatch'):c.check_hash(b'wrong-generation','1f6cf53b')
  for a,b in [('ldr x1, [x2, #16]','ldr x1, [x2, #24]'),('mov w0, #1','mov w0, #2'),('bl 0x123 <first>','bl 0x456 <second>')]:
   self.assertNotEqual(c.normal_line(a,registers=True),c.normal_line(b,registers=True))
  self.assertEqual(c.normal_line('bl 0x123 <target>'),c.normal_line('bl 0x456 <target>'))
  self.assertEqual(c.normal_line('mov x1, x2',registers=True),c.normal_line('mov x7, x8',registers=True))
  # Register-erased equality cannot be used as semantic equality: dependency is lost.
  self.assertNotEqual(c.normal_line('mov x0, x0'),c.normal_line('mov x0, x1'))
 def test_every_delta_has_disposition_and_trace(self):
  top=json.loads((R/'top20.json').read_text());self.assertEqual(len(top),20)
  for k in c.INPUTS:
   for f in json.loads((R/'evidence'/k/'functions.json').read_text()):
    self.assertNotIn(f.get('disposition'),(None,'pending-review'));self.assertTrue(f['basis'])
    if f['state']!='normalized_equal':
     self.assertTrue((R/f['diff']).exists());self.assertTrue((R/f['register_diff']).exists())
    for v in ('r155','new'):
     if f[v]:
      lines=(R/'evidence'/k/v/'disassembly.txt').read_text().splitlines()
      self.assertRegex(lines[f[v]['line']-1],r'^\s*[0-9a-f]+:')
   for file in ('strings-diff.json','versioned-symbols-diff.json','sections-diff.json'):
    for d in json.loads((R/'evidence'/k/file).read_text()):self.assertTrue(d['disposition']);self.assertTrue(d['basis'])
 def test_provider_copy_caveat_is_bound_to_child_bytes(self):
  evidence=json.loads((R/'provider-baseline-caveat.json').read_text())
  for version,pair in zip(('r155','new'),c.INPUTS['child']):
   elf=c.ELF(*pair);sym=next(s for s in elf.symbols if s['name']=='kWlscplArtifacts')
   sec=elf.sections[sym['section']];offset=sym['value']-sec['addr'];data=elf.bytes(sec)
   embedded=data[offset+8:offset+8+64].decode()
   self.assertEqual(embedded,evidence[version]['first_record_printable'][0]['text'])
   self.assertEqual(data[offset+114:offset+242].split(b'\0')[0],b'libwestlake_android_runtime_provider.so')
   self.assertEqual(embedded,evidence[version]['assigned_provider_sha256'])
 def test_reference_mismatch_is_not_silently_reused(self):
  d=json.loads((R/'reference-identity.json').read_text())
  self.assertTrue(d['host']['old_matches']);self.assertTrue(d['child']['old_matches'])
  self.assertTrue(d['runtime-provider']['old_matches'])
  self.assertTrue(all(not v['new_matches'] for v in d.values()))
 def test_correct_provider_protocol_is_pinned(self):
  fs=json.loads((R/'evidence/runtime-provider/functions.json').read_text())
  f=next(x for x in fs if x['name']=='WLAR_HostServicesInstall')
  self.assertEqual(f['state'],'normalized_equal')
  for v in ('r155','new'):
   lines=(R/'evidence/runtime-provider'/v/'disassembly.txt').read_text().splitlines()
   body='\n'.join(lines[f[v]['line']-1:f[v]['line']+93])
   self.assertRegex(body,r'ldr\s+x8, \[x3, #112\]\n[^\n]*cbz\s+x8')
   self.assertRegex(body,r'ldr\s+x8, \[x3, #120\]\n[^\n]*str[^\n]*\n[^\n]*cbz\s+x8')
  installer=(R/'evidence/runtime-provider/functions/3e1af20b69614705.diff').read_text()
  ctor=(R/'evidence/runtime-provider/functions/fc7370b5c8fafe96.diff').read_text()
  self.assertIn('-bl <WLNL_InstallSealedOpenV1@plt>',installer)
  self.assertIn('+bl <WLNL_InstallSealedOpenV1@plt>',ctor)
 def test_host_child_evidence_unchanged(self):
  baseline=json.loads((R/'host-child-preserved.json').read_text())
  for path,digest in baseline.items():
   self.assertEqual(c.sha((R/path).read_bytes()),digest,path)
if __name__=='__main__':unittest.main(verbosity=2)
