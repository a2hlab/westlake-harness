#!/usr/bin/env python3
import ast,hashlib,json,struct,unittest
from pathlib import Path
from rules85 import FAMILIES,inspect_method,elf_info,native_verdict
from scan85 import OUT
from scan_io import load

def elf_fixture():
    names=b'\0__errno\0optional\0ok\0';sym=bytes(24)+struct.pack('<IBBHQQ',1,0x12,0,0,0,0)+struct.pack('<IBBHQQ',9,0x22,0,0,0,0)+struct.pack('<IBBHQQ',18,0x12,0,1,0x1000,4)
    payload=bytearray(64);st=len(payload);payload.extend(names);sy=len(payload);payload.extend(sym);sh=len(payload)
    payload.extend(bytes(64));payload.extend(struct.pack('<IIQQQQIIQQ',0,3,0,0,st,len(names),0,0,1,0));payload.extend(struct.pack('<IIQQQQIIQQ',0,11,0,0,sy,len(sym),1,1,8,24))
    struct.pack_into('<16sHHIQQQIHHHHHH',payload,0,b'\x7fELF\x02\x01'+bytes(10),3,183,1,0,0,sh,0,64,56,0,64,3,0)
    return bytes(payload)

class Task85Tests(unittest.TestCase):
    def test_rules(self):
        def call(ins):return inspect_method('test/App.onCreate()V','classes.dex',[(str(i),i,t) for i,t in enumerate(ins)])
        found=call(['const/16 v1, #int 8192 // #2000','invoke-virtual {v0, v1}, Landroid/view/Window;.addFlags:(I)V'])
        self.assertEqual(found[0]['strength'],'unsupported-source-policy-constant')
        self.assertFalse(call(['const/16 v1, #int 128 // #0080','invoke-virtual {v0, v1}, Landroid/view/Window;.addFlags:(I)V']))
        self.assertIsNone(call(['const/16 v1, #int 8192 // #2000','goto 0004 // +0002','invoke-virtual {v0, v1}, Landroid/view/Window;.addFlags:(I)V'])[0]['constant'])
        own=call(['const-class v2, Ltest/OwnService; // type@0','invoke-virtual {v0, v1, v2, v3}, Landroid/content/Context;.bindService:(Landroid/content/Intent;Landroid/content/ServiceConnection;I)Z'])
        self.assertEqual(own[0]['family'],'in-app-bindservice');self.assertEqual(own[0]['intent_target'],'unknown');self.assertIn('test/OwnService',own[0]['class_constants_in_method_before_call'])
        vel=call(['invoke-static {v0}, Landroid/view/VelocityTracker;.obtain:(I)Landroid/view/VelocityTracker;']);self.assertEqual(vel[0]['family'],'velocitytracker-jni')
        pref=call(['invoke-interface {v0, v1, v2}, Landroid/content/SharedPreferences;.getBoolean:(Ljava/lang/String;Z)Z']);self.assertEqual(pref[0]['family'],'sharedpreferences-null')
        self.assertFalse(call(['invoke-static {v0}, Ltest/Other;.obtain:(I)I']))
        ctor=call(['const/4 v1, #int 2 // #2','const/16 v2, #int 8192 // #2000','invoke-direct {v0, v1, v2}, Landroid/view/WindowManager$LayoutParams;.<init>:(II)V'])
        self.assertEqual(ctor[0]['strength'],'unsupported-source-policy-constant')
        parsed=elf_info(elf_fixture());self.assertEqual(parsed['header'],'valid-ELF64-AArch64');self.assertEqual(parsed['imports'],[{'name':'__errno','weak':False},{'name':'optional','weak':True}])
        self.assertEqual(elf_info(b'PK\x03\x04')['header'],'invalid-magic')
        verdict=native_verdict(parsed,{},set());self.assertEqual(verdict['strong_unprovided'],['__errno']);self.assertTrue(verdict['hit'])
        self.assertFalse(native_verdict({**parsed,'imports':[{'name':'__errno','weak':True}]},{},set())['hit'])
        self.assertFalse(native_verdict({**parsed,'imports':[]},{},set())['hit'])
        provided=native_verdict(parsed,{'__errno':['libc.so']},set());self.assertEqual(provided['strong_unprovided'],[]);self.assertEqual(provided['bionic_imports'][0]['resolution'],'definition-present-scope-unknown')
    def test_freeze(self):
        freeze=load(OUT/'freeze.json');self.assertFalse(freeze['observations_read']);self.assertEqual(len(freeze['apks']),32)
        for item in freeze['inputs']+freeze['outputs']:
            p=Path(item['path']);self.assertEqual(hashlib.sha256(p.read_bytes()).hexdigest(),item['sha256'],str(p))
        rows=load(OUT/'hits.json');self.assertEqual(len(rows),160)
        keys={r['app'] for r in rows};self.assertEqual(len(keys),32)
        for key in keys:self.assertEqual({r['family'] for r in rows if r['app']==key},set(FAMILIES))
        source=Path(__file__).with_name('scan85.py').read_text();self.assertNotIn('r14full-triage',source);self.assertNotIn('first_fatal',source)
    def test_backtest(self):
        from backtest85 import score_rows
        base={'app':'a','partition':'held-out','identity':'exact','observed_family':'window-type-flags','predicted_families':['window-type-flags'],'first_new_family':'window-type-flags','observation_role':'fatal','classifiable':True}
        result=score_rows([base,{**base,'app':'b','partition':'seed'},{**base,'app':'c','identity':'unknown'},{**base,'app':'d','observed_family':'unknown','classifiable':False},{**base,'app':'e','observation_role':'nonfatal-or-unproven'}])
        self.assertEqual(result['held_out_family']['total'],2);self.assertEqual(result['held_out_first_fatal']['total'],1);self.assertEqual(result['held_out_first_fatal']['hits'],1)
        receipt=load(OUT/'observation-read-receipt.json');snapshot=OUT/'evidence/scorer-before-read.py'
        self.assertEqual(hashlib.sha256(snapshot.read_bytes()).hexdigest(),receipt['scorer_before_read_sha256'])
        def scorer(path):return ast.dump(next(n for n in ast.parse(path.read_text()).body if isinstance(n,ast.FunctionDef) and n.name=='score_rows'),include_attributes=False)
        self.assertEqual(scorer(snapshot),scorer(Path(__file__).with_name('backtest85.py')))
        actual=load(OUT/'backtest.json');self.assertTrue(actual['freeze_verified']);self.assertEqual(actual['prediction_file_sha256'],load(OUT/'freeze.json')['outputs'][2]['sha256'])
if __name__=='__main__':unittest.main()
