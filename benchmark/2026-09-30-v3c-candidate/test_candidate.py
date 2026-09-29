#!/usr/bin/env python3
import copy,json,tempfile,unittest
from pathlib import Path
import assemble as a
import deploy_generation as d

class CandidateTests(unittest.TestCase):
    def test_rules(self):
        with tempfile.TemporaryDirectory() as tmp:
            f=Path(tmp)/'artifact';f.write_bytes(b'good');expected=a.sha(f)
            a.pin(f,expected);f.write_bytes(b'changed')
            with self.assertRaisesRegex(ValueError,'SHA changed'):a.pin(f,expected)
        m=json.loads((a.HERE/'candidate-package.json').read_text())
        a.audit(m)
        split=copy.deepcopy(m)
        split['live_hashes']['/system/android/lib64/libapp_native_loader.so']='0'*64
        with self.assertRaisesRegex(ValueError,'mismatch'):a.audit(split)
        split=copy.deepcopy(m)
        split['files']['payload/android/lib64/libapp_native_loader.so']='0'*64
        with self.assertRaisesRegex(ValueError,'split alias'):a.audit(split)
        inputs=json.loads((a.HERE/'inputs.json').read_text())
        old=json.loads((a.HERE/inputs['boards']['61b']['manifest_snapshot']).read_text())
        coherent=copy.deepcopy(old);n='libapp_native_loader.so';h=m['files']['payload/route/'+n]
        coherent['files']['payload/route/'+n]=h
        coherent['live_hashes']['/system/android/lib64/'+n]=h
        coherent['live_hashes']['/system/lib64/westlake/route-a/'+m['generation']+'/'+n]=h
        with self.assertRaisesRegex(ValueError,'manifest mismatch'):
            d.validate_replacement(old,coherent,'/system/android/lib64/'+n)
        # Existing full-deployment method fails at the pre-activation hash of
        # an absent addition. Run its actual control flow with an offline fake.
        class Fake:
            d=None;gen='a'*64
            m={'prerequisites':{},'mounts':[{'source':'payload/android','target':'/system/android'}],
               'files':{'payload/android/lib64/libnew.so':'b'*64}}
            writes=0
            class Batch:
                def parse_bundle(self,text,pkg):return {}
            b=Batch()
            def shell(self,cmd):
                if cmd.startswith(('bm dump','test -e')):return ''
                self.writes+=1;raise AssertionError('unexpected write: '+cmd)
            def top_mounts(self):return {}
            def hashes(self,paths):
                if not paths:return {}
                raise RuntimeError('incomplete SHA readback: absent libnew.so')
        fake=Fake()
        with self.assertRaisesRegex(RuntimeError,'incomplete SHA'):
            d.Deployment.deploy(fake)
        self.assertEqual(fake.writes,0)

    def test_inventory(self):
        result=json.loads((a.HERE/'results.json').read_text())
        inputs=json.loads((a.HERE/'inputs.json').read_text())
        package=Path(result['candidate']);m=d.load_package(package);a.audit(m)
        a.pin(package/'package.json',result['package_manifest_sha256'])
        self.assertEqual(result['board_operations'],0)
        self.assertFalse(result['external_output_written'])
        self.assertTrue(package.is_relative_to(a.HERE))
        self.assertEqual(set(result['boards']),{'5ea','5cd','61b'})
        self.assertEqual(result['boards']['61b']['fingerprint_short'],'22d3245795f9')
        for name,prefix in [('liblog.so','8c81a937'),('liboh_android_runtime.so','9e14bf20'),('libnativeloader.so','fde6f31c'),('liboh_tls_boundary.so','39c2cfe9'),('libwestlake_jni_gapfill.so','d1a1961d')]:
            self.assertTrue(m['files']['payload/android/lib64/'+name].startswith(prefix),name)
        self.assertTrue(m['files']['payload/runtime/appspawn-x'].startswith('d977bd15'))
        self.assertNotIn('payload/android/lib64/libwestlake_html_compat.so',m['files'])
        for x in inputs['artifacts']:
            self.assertEqual(len(x['sha256']),64);self.assertTrue(x['source_commits']);self.assertTrue(x['source_snapshot'])
            for c in x['source_commits']:self.assertEqual(len(c),40)
            a.pin(x['path'],x['sha256'])
        for key,b in result['boards'].items():
            self.assertTrue(b['package_dry_run_passed']);self.assertFalse(b['device_io'])
            self.assertFalse(b['recorded_live_conflicts']);self.assertIsNone(b['executable_incremental_steps'])
            self.assertEqual(b['changed_live_paths'],sum(x['action']!='keep' for x in b['changes']))
            self.assertEqual(b['board_readiness'],'unknown')
            report=json.loads((a.HERE/'evidence'/('dry-run-'+key+'.json')).read_text())
            self.assertIn('--dry-run',report['command']);self.assertFalse(report['stdout']['device_io'])
        audit=json.loads((a.HERE/'elf-audit.json').read_text())
        for x in audit['libraries']:
            if x['name'] in {'liboh_tls_boundary.so','libwestlake_jni_gapfill.so'}:
                self.assertEqual(x['needed'],['libc.so']);self.assertEqual(x['hard_cpp_undefined'],[])
                self.assertIn('JNI_OnLoad',x['exports'])
if __name__=='__main__':unittest.main()
