#!/usr/bin/env python3
"""Offline real-consumer checks; grafted historical data is NOT fresh authorization."""
import copy, importlib.util, json, os, subprocess, sys, tempfile, unittest
from pathlib import Path
import derive_successor as ds
HERE=Path(__file__).resolve().parent
MAIN=Path(os.environ.get('T34_MAIN',str(HERE.parents[2]))).resolve()
PACKAGE=Path(os.environ.get('T34_GUARDIAN_PACKAGE',str(MAIN/ds.PACKAGE)))
sys.path.insert(0,str(HERE/'deployment'))
import prepare_data as pd

class Tests(unittest.TestCase):
    def setUp(self):
        # Real old receipt bytes plus only the newly frozen guardian package fields.
        self.f=json.loads((MAIN/ds.BASE/'bound-data-01/fresh.json').read_text())
        self.run=(MAIN/ds.BASE/'bound-data-01/run61b.before.reference.sh').read_bytes()
        self.ref=json.loads((HERE/'deployment/guardian-reference.json').read_text())
        self.f['cfg_sha256']=ds.NEW_CFG
        self.f['runtime_sha256'][ds.CFG_PATH]=ds.NEW_CFG
        self.f['controls']=self.ref['controls']

    def test_exact_derivation_and_eighteen_real_members(self):
        derived=ds.generate(MAIN,PACKAGE)
        for name,data in derived.items():self.assertEqual((HERE/name).read_bytes(),data,name)
        self.assertEqual(len(self.ref['controls']),18)
        for path,digest in self.ref['controls'].items():
            self.assertEqual(ds.sha((PACKAGE/'payload'/Path(path).name).read_bytes()),digest)

    def test_real_prepare_unsigned_positive(self):
        with tempfile.TemporaryDirectory(prefix='t34-r3-offline-') as t:
            out=Path(t)/'data';p=pd.prepare(self.f,self.run,MAIN,out)
            self.assertEqual(p['status'],'FRESH_DATA_BOUND_NOT_AUTHORIZED')
            ad=json.loads((out/'admission.template.json').read_text())
            self.assertIsNone(ad['approved_by']);self.assertIsNone(ad['boot']);self.assertIsNone(ad['holder'])
            self.assertEqual(ad['cfg_sha256'],ds.NEW_CFG)
            self.assertEqual(ad['executor_sha256'],ds.sha((HERE/'deployment/executor61b.py').read_bytes()))

    def test_old_or_partial_or_foreign_guardian_rejected(self):
        old=json.loads((MAIN/ds.REFERENCE).read_text())
        bads=[]
        f=copy.deepcopy(self.f);f['cfg_sha256']=ds.OLD_CFG;bads.append(f)
        f=copy.deepcopy(self.f);f['controls']=old['controls'];bads.append(f)
        f=copy.deepcopy(self.f);f['controls'].pop(next(iter(f['controls'])));bads.append(f)
        f=copy.deepcopy(self.f);f['controls'][ds.NEW_ROOT+'/watchdog.sh']='0'*64;bads.append(f)
        f=copy.deepcopy(self.f);f['controls']={k.replace('20261021-r3','foreign'):v for k,v in f['controls'].items()};bads.append(f)
        f=copy.deepcopy(self.f);f['runtime_sha256'][ds.CFG_PATH]=ds.OLD_CFG;bads.append(f)
        for i,f in enumerate(bads):
            with self.subTest(case=i),self.assertRaises(AssertionError):pd.validate(f,self.run,MAIN)

    def test_existing_identity_runtime_and_source_guards_preserved(self):
        for key,value in [('uid',20011300),('access_token_id',0),('hap_sha256','0'*64),('serial','5cd'),('power',{'timeout':10000,'override':10000})]:
            f=copy.deepcopy(self.f);f[key]=value
            with self.subTest(key=key),self.assertRaises(AssertionError):pd.validate(f,self.run,MAIN)
        with self.assertRaises(AssertionError):pd.validate(self.f,self.run+b'foreign\n',MAIN)
        f=copy.deepcopy(self.f);f['runtime_sha256'][pd.RT+'/liboh_adapter_bridge.so']='0'*64
        with self.assertRaises(AssertionError):pd.validate(f,self.run,MAIN)

    def test_transport_preview_and_old_executor_rejected(self):
        transport=HERE/'transport/file_transport.py'
        for executor,ok in [(HERE/'deployment/executor61b.py',True),(MAIN/ds.BASE/'deployment/executor61b.py',False)]:
            p=subprocess.run([sys.executable,str(transport),'--executor',str(executor),'--','apply'],capture_output=True)
            self.assertEqual(p.returncode==0,ok,p.stderr)
            if ok:self.assertEqual(json.loads(p.stdout)['device_calls'],0)
            else:self.assertIn(b'frozen executor drift',p.stderr)

    def test_recovery_verifier_accepts_exact_new_controls_not_missing(self):
        sys.path.insert(0,str(HERE/'window-driver'))
        import recover_driver as rd
        parent={'pid':4992};lines=[]
        for root in [pd.RT,'/proc/4992/root/data/local/tmp/asx']:
            lines += [h+'  '+root+'/'+rel for rel,h in rd.ORIGINAL.items()]
        lines += [h+'  '+p for p,h in self.f['controls'].items()]
        lines += [ds.NEW_CFG+'  '+rd.CFG,self.f['hap_sha256']+'  '+rd.HAP,'PHYSICAL_COMPAT_ABSENT','PRIVATE_COMPAT_ABSENT','ScreenOffTime: Timeout=30000ms  OverrideTimeout=86400000ms','DEBUG_PROCESS_RC=0','Get parameter "debug.ttplayer.log.enable" fail! errNum is:106!','RESTORE_IDENTITY_MATCH']
        text='\n'.join(lines)+'\n'
        self.assertEqual(rd.verify_text(text,parent,'fixture',self.f['controls'],ds.NEW_CFG,self.f['hap_sha256'],0)['guardian_sha_matches'],18)
        bad=dict(self.f['controls']);bad.pop(next(iter(bad)))
        with self.assertRaises(AssertionError):rd.verify_text(text,parent,'fixture',bad,ds.NEW_CFG,self.f['hap_sha256'],0)

if __name__=='__main__':unittest.main(verbosity=2)
