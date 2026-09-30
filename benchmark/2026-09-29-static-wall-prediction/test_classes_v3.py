#!/usr/bin/env python3
import collections,json,struct,unittest
from pathlib import Path
from scan_classes_v3 import OUT,dex_classes,status,inspect_method,R13,R13SHA,sha
from scan_io import load
from scan_reachability import compute_paths

def fixture():
    # One actual definition, two referenced types. No definition for Missing.
    data=bytearray(112);data[:8]=b'dex\n035\0';strings=[b'Landroid/test/Present;',b'Landroid/test/Missing;']
    stringoff=len(data);data.extend(bytes(8));typeoff=len(data);data.extend(struct.pack('<II',0,1));classoff=len(data);data.extend(struct.pack('<IIIIIIII',0,1,0xffffffff,0,0xffffffff,0,0,0))
    for i,s in enumerate(strings):struct.pack_into('<I',data,stringoff+4*i,len(data));data.extend(bytes([len(s)])+s+b'\0')
    for off,val in [(56,2),(60,stringoff),(64,2),(68,typeoff),(96,1),(100,classoff)]:struct.pack_into('<I',data,off,val)
    return bytes(data)

class ClassesTests(unittest.TestCase):
    def test_presence(self):
        rows=dex_classes(fixture());self.assertEqual([r['class'] for r in rows],['android/test/Present'])
        inv=load(OUT/'class-inventory.json');self.assertEqual(sha(R13),R13SHA)
        self.assertEqual(status('android/net/IConnectivityManager',inv,{},True)[0],'definition-absent')
        self.assertEqual(status('android/app/Activity',inv,{},True)[0],'definition-present')
        self.assertEqual(status('android/test/Missing',{'classes':{}},{'android/test/Missing':{}},True)[0],'definition-absent')
        self.assertEqual(status('android/test/Missing',{'classes':{}},{'android/test/Missing':{}},False)[0],'app-definition-present')
        req=load(OUT/'service-interface-matrix.json');self.assertEqual(len(req),14)
        self.assertEqual([r['service'] for r in req if r['availability']=='definition-absent'],['connectivity'])
        paths=[r['path'] for r in inv['inputs']];self.assertIn(str(R13),paths);self.assertNotIn(inv['excluded_replaced_jar'],paths)
        with self.assertRaises(ValueError):dex_classes(b'not-a-dex')
    def test_paths(self):
        methods={'App.onCreate()V':{'edges':[{'target':'Used.run()V','kind':'invoke-static'}]},'Used.run()V':{'edges':[]},'Uncalled.run()V':{'edges':[]}}
        found,_,_=compute_paths(methods,{}, {},[{'method':'App.onCreate()V'}]);self.assertIn('Used.run()V',found);self.assertNotIn('Uncalled.run()V',found)
        data=load(OUT/'wikipedia-evidence.json');rows=[r for r in data['rows'] if r['class']=='android/net/IConnectivityManager']
        self.assertTrue(any('ConnectionStateMonitor' in r['method'] and r['path'] for r in load(OUT/'wikipedia-delivery.json')['evidence']));self.assertTrue(rows);self.assertTrue(any(r['startup_reachable']=='yes-static' for r in rows))
        for r in rows:
            if r['startup_reachable']=='yes-static':self.assertTrue(r.get('path') or data.get('startup_paths',{}).get(r['method'],{}).get('path'))
        self.assertTrue(any(r['availability']=='definition-absent' and r['startup_reachable']=='unknown' for r in data['rows']))
        cohort=load(OUT/'cohort.json');self.assertEqual(cohort['source_memberships'],33);self.assertEqual(cohort['unique_keys'],32);self.assertEqual(cohort['overlap'],['ooniprobe'])
        calls=inspect_method('A.x()V','classes.dex',[('0',1,'const-string v0, "android.test.Missing" // string@1')]);self.assertFalse(calls)
if __name__=='__main__':unittest.main()
