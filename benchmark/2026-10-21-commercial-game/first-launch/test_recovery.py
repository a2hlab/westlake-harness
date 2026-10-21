import copy
import json
from pathlib import Path
import tempfile
import unittest
import os
import recovery_hook as h


class Board:
    def __init__(self):
        self.calls=[]; self.pkg='ID: 100:\n\tcom.ohos.sceneboard\n\t'+h.PACKAGE+'\n'
        self.bundle=json.dumps({'name':h.PACKAGE,'uid':20011999})
        self.ps='PID PPID UID NAME\n1 0 0 init\n'; self.rc=0
    def shell(self, command, **kw):
        self.calls.append(command)
        if command=='bm dump -a':return self.rc,self.pkg
        if command.startswith('bm dump -n '):return 0,self.bundle
        if command.startswith('ps '):return 0,self.ps
        raise AssertionError(command)


class BMS:
    def __init__(self):self.stops=0;self.stop_result=True
    def parse_bundle(self,t,p):return {'uid':json.loads(t)['uid']}
    def cold_stop(self,*args):self.stops+=1;return self.stop_result


class Recovery(unittest.TestCase):
    def setUp(self):
        self.ctx={'serial':h.SERIAL,'holder':'cc-video 123 2026-10-21T16:00:00+0800',
                  'boot_id':'boot','start_epoch':100,'input_sha256':'metadata','packages':['com.ohos.sceneboard']}
        self.rec={'serial':h.SERIAL,'boot_id':'boot','package':h.PACKAGE,'apk_sha256':h.APK_SHA,
                  'input_sha256':'metadata','install':{'return_code':0,'success_text':True},
                  'bms':{'uid':20011999},'finished_at':150}
        self.b=Board(); self.m=BMS();self.tmp=tempfile.TemporaryDirectory();self.addCleanup(self.tmp.cleanup)
        self.out=Path(self.tmp.name);(self.out/'installed-bundle.txt').write_text(self.b.bundle)
    def run_restore(self):return h.restore_target(self.b,self.m,self.ctx,self.rec,self.out)
    def test_valid_retains_and_stops(self):
        self.assertTrue(self.run_restore()['retained']);self.assertEqual(self.m.stops,1)
        self.assertFalse(any('uninstall' in c or 'rm ' in c for c in self.b.calls))
    def test_empty_and_disconnect_rejected_before_stop(self):
        for rc,text in [(0,''),(1,''),(1,self.b.pkg),(0,'error: transport lost'),(0,'ID: 100:\n')]:
            with self.subTest(rc=rc,text=text):
                self.b.rc,self.b.pkg=rc,text
                with self.assertRaises(h.Refuse):self.run_restore()
        self.assertEqual(self.m.stops,0)
    def test_foreign_package_rejected(self):
        self.b.pkg+='\tforeign.app\n'
        with self.assertRaises(h.Refuse):self.run_restore()
    def test_missing_install_receipt_rejected(self):
        self.rec=None
        with self.assertRaises(h.Refuse):self.run_restore()
    def test_install_provenance_mutations(self):
        for key,value in [('serial','other'),('boot_id','old'),('apk_sha256','other'),('input_sha256',h.APK_SHA),('finished_at',99)]:
            with self.subTest(key=key):
                rec=copy.deepcopy(self.rec);rec[key]=value
                with self.assertRaises(h.Refuse):h.install_origin(rec,self.ctx,20011999)
        for change in [{'return_code':1,'success_text':True},{'return_code':0,'success_text':False},
                       {'return_code':0,'success_text':True,'skipped':'launch_only'}]:
            rec=copy.deepcopy(self.rec);rec['install']=change
            with self.assertRaises(h.Refuse):h.install_origin(rec,self.ctx,20011999)
    def test_uid_and_bundle_drift(self):
        self.b.bundle=json.dumps({'name':h.PACKAGE,'uid':20012000})
        with self.assertRaises(h.Refuse):self.run_restore()
        self.assertEqual(self.m.stops,0)
    def test_cold_stop_failure(self):
        self.m.stop_result=False
        with self.assertRaises(h.Refuse):self.run_restore()
    def test_live_or_malformed_ps(self):
        for ps in ['', 'PID PPID UID NAME\nbad row', 'PID PPID UID NAME\n22 1 20011999 genshin']:
            self.b.ps=ps
            with self.subTest(ps=ps), self.assertRaises(h.Refuse):self.run_restore()
    def test_absent_never_calls_stop(self):
        self.b.pkg='ID: 100:\n\tcom.ohos.sceneboard\n';self.rec=None
        self.assertFalse(self.run_restore()['retained']);self.assertEqual(self.m.stops,0)
    def test_full_holder_boot_and_budget(self):
        h.validate_guard(self.ctx,self.ctx['holder'],'boot',101)
        for holder,boot,now in [('cc-video 124 2026-10-21T16:00:00+0800','boot',101),
                                (self.ctx['holder'],'old',101),(self.ctx['holder'],'boot',1900),
                                (self.ctx['holder'],'boot',99)]:
            with self.assertRaises(h.Refuse):h.validate_guard(self.ctx,holder,boot,now)
    def test_power_and_focus_real_shape(self):
        self.assertEqual(h.power('Current State: SLEEP  Reason: 1\nScreenOffTime: Timeout=30000ms  OverrideTimeout=10000ms'),
                         {'state':'SLEEP','timeout':30000,'override':10000})
        self.assertEqual(h.focus('SCBScreenLock10 0 2283 15 2110 1 0 2000\nFocus window: 15'), 'SCBScreenLock10')
        for text in ['', 'Current State: SLEEP', 'Timeout=30000']:
            with self.assertRaises(h.Refuse):h.power(text)
    def test_buffer_decimal_uses_actual_bms_conversion(self):
        repo=Path(os.environ.get('G06_MAIN',Path(__file__).resolve().parents[3]))
        convert=h.load_bms(repo).size_bytes
        self.assertEqual(h.buffers('Log type app buffer size is 256.0K\nLog type core buffer size is 16.0M',convert),
                         {'app':262144,'core':16777216})
        self.assertEqual(h.buffers('Log type app buffer size is 262144',convert),{'app':262144})
        for token in ['256.0Kjunk','16..0M','16 M','0','NaN','-1','1e6','256.0K bytes']:
            with self.subTest(token=token),self.assertRaises(h.Refuse):
                h.buffers('Log type app buffer size is '+token,convert)
    def test_actual_5ea_logging_read(self):
        repo=Path(os.environ.get('G06_MAIN',Path(__file__).resolve().parents[3]))
        raw=(Path(__file__).parent/'evidence/logging-read.stdout.txt').read_text()
        self.assertEqual(raw.splitlines()[0],raw.splitlines()[-1])
        self.assertIn('HILOG_RC=0',raw);self.assertIn('PARAM_RC=0',raw)
        sizes='\n'.join(x for x in raw.splitlines() if x.startswith('Log type '))
        self.assertEqual(h.buffers(sizes,h.load_bms(repo).size_bytes),
                         {k:16777216 for k in ['app','init','core','only_prerelease']})
        self.assertEqual(raw.split('HILOG_RC=0')[1].split('PARAM_RC=0')[0].strip(),'true')
    def test_real_bms_missing_remote_marker_is_failure(self):
        repo=Path(os.environ.get('G06_MAIN',Path(__file__).resolve().parents[3]))
        bms=h.load_bms(repo)
        class EmptyTransport(bms.Board):
            def __init__(self):self.hdc=['hdc'];self.serial=h.SERIAL;self.calls=[]
            def command(self,argv,timeout=60):self.calls.append(argv);return 0,''
        b=EmptyTransport()
        with self.assertRaises(bms.BatchStop):b.raw_shell('bm dump -a')
        self.assertEqual(len(b.calls),1)


if __name__=='__main__':unittest.main()
