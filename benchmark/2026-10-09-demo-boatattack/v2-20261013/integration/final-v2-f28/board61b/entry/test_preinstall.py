"""Known-answer state tests for missing-only composition; original install_one body executes on a recording Board."""
import json,sys,tempfile,unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch
HERE=Path(__file__).resolve().parent;sys.path.insert(0,str(HERE));import prepare_boat as p
class Failure(ValueError):pass
class Stop(Exception):pass
class Tests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.root=Path(self.temp.name);self.boot='11111111-1111-1111-1111-111111111111'
        self.files={p.LIBDIR+'/'+n:dict(exists=True,sha256=h,**p.META) for n,h in p.STOCK.items()}
        self.files[p.APK]={'exists':False};self.files[p.SIGNAL]={'exists':False};self.calls=[];self.registered=False;self.drift=False;self.bms_error=None
        self.apk=self.root/'original.apk';self.apk.write_bytes(b'synthetic APK transport test only')
        self.entry=p.module(HERE/'frozen-apk/missing_apk_entry.py','actual_missing_entry')
        self.bundle={'name':p.PACKAGE,'uid':20019001,'applicationInfo':{'name':p.PACKAGE,'uid':20019001},'userInfo':[{'bundleName':p.PACKAGE,'uid':20019001,'bundleUserInfo':{'userId':100}}],'versionCode':1,'versionName':'0.9'}
        case=self
        class Board:
            serial=p.r.SERIAL;boot=case.boot
            def ready(self):pass
            def receive(self,remote,local):local.write_bytes(b'synthetic stock backup');case.calls.append(('receive',remote))
            def send(self,local,remote):case.calls.append(('send',remote))
            def shell(self,command,**kwargs):
                case.calls.append(('shell',command))
                if command=='bm dump -n '+p.PACKAGE:
                    if case.bms_error:return case.bms_error
                    return 0,p.PACKAGE+':'+json.dumps(case.bundle) if case.registered else case.entry.ABSENT
                if command.startswith('mkdir -p '):return 0,''
                if command.startswith('sha256sum '):return 0,p.APK_SHA+'  /staged.apk'
                if command.startswith('bm install -p '):
                    case.registered=True;case.files[p.APK]=dict(exists=True,sha256=p.APK_SHA)
                    if case.drift:case.files[p.LIBDIR+'/libunity.so']['sha256']='f'*64
                    return 0,'install bundle successfully.'
                if '(set -C; : > ' in command:
                    case.files[p.SIGNAL]=dict(exists=True,sha256=p.EMPTY,**p.SIGNAL_META);return 0,''
                if command.startswith('stat -c %d:%i '):return 0,'12:34'
                raise AssertionError(command)
        self.board=Board()
        self.b=SimpleNamespace(AppFailure=Failure,BatchStop=Stop,resolve_input=lambda root,app:dict(app,apk=str(self.apk)),bm_success=lambda rc,text,op:rc==0 and text=='install bundle successfully.',parse_bundle=lambda text,pkg:{'queryable':True},save=lambda path,obj:path.write_text(json.dumps(obj)))
        self.data={'boot_id':self.boot,'input_root':str(self.root),'app':{'key':'boatattack','package':p.PACKAGE,'apk_sha256':p.APK_SHA}}
    def tearDown(self):self.temp.cleanup()
    def run_case(self):
        out=self.root/'out';out.mkdir()
        def sha(path):
            path=Path(path)
            if path==self.apk:return p.APK_SHA
            return p.STOCK[path.name.removesuffix('.preinstall')]
        with patch.object(p,'metadata',side_effect=lambda board,target:dict(self.files[target])),patch.object(p.r,'sha',side_effect=sha):return p.perform(self.data,self.root,out,self.b,self.board,self.entry,None)
    def test_missing_install_original_helper_and_placeholder(self):
        result=self.run_case();self.assertEqual(result['status'],'PREINSTALL_COMPLETE_PENDING_FRESH_CAPTURE')
        self.assertEqual(result['boat_uid'],20019001);self.assertFalse(result['provider_compiled'])
        commands=[s for op,s in self.calls if op=='shell'];self.assertEqual(sum(s.startswith('bm install ') for s in commands),1)
        self.assertTrue(any('(set -C; : > ' in s for s in commands));self.assertFalse(any('cold_stop' in s or 'uninstall' in s or ' -r ' in s or 'rm ' in s for s in commands))
    def test_unknown_or_transport_error_never_absence(self):
        self.bms_error=(0,'Connect server failed')
        with self.assertRaises(ValueError):self.run_case()
        self.assertFalse(any(op=='send' for op,_ in self.calls))
    def test_present_stock_drift_before_write(self):
        self.files[p.LIBDIR+'/libunity.so']['uid']=1
        with self.assertRaises(ValueError):self.run_case()
        self.assertFalse(any(op=='send' for op,_ in self.calls))
    def test_install_stock_drift_stops_before_placeholder(self):
        self.drift=True
        with self.assertRaises(ValueError):self.run_case()
        self.assertFalse(any('(set -C;' in s for _,s in self.calls));self.assertFalse(self.files[p.SIGNAL]['exists'])
    def test_existing_wrong_apk_no_reinstall(self):
        self.registered=True;self.files[p.APK]=dict(exists=True,sha256='f'*64)
        with self.assertRaises(ValueError):self.run_case()
        self.assertFalse(any(op=='send' for op,_ in self.calls))
    def test_foreign_signal_no_replace(self):
        self.files[p.SIGNAL]=dict(exists=True,sha256='f'*64,**p.SIGNAL_META)
        with self.assertRaises(ValueError):self.run_case()
        self.assertFalse(any('(set -C;' in s for _,s in self.calls))
if __name__=='__main__':unittest.main(verbosity=2)
