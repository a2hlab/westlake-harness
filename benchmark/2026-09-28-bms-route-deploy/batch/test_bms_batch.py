"""Offline tests only: transport and fixture APK/JPEG bytes are synthetic."""
import contextlib
import hashlib
import io
import json
from pathlib import Path
import subprocess
import tempfile
import unittest
from unittest.mock import patch

import bms_batch as b

SERIAL = sorted(b.SERIALS)[0]
PKG = 'org.example.test'
ABILITY = PKG + '.MainActivity'
JPEG = b'\xff\xd8synthetic-not-real-device-image\xff\xd9'
BOOT = '11111111-2222-3333-4444-555555555555'


def icon_tree(duplicate=False, visible='true', bundle=b.LAUNCHER):
    attrs = {'id': b.ICON_PREFIX+PKG+'.'+ABILITY,
             'bounds':'[100,200][300,400]', 'visible':visible,
             'enabled':'true','clickable':'true'}
    nodes = [{'attributes':attrs, 'children':[]}]
    if duplicate:nodes.append({'attributes':dict(attrs),'children':[]})
    return {'attributes':{'bundleName':bundle,'bounds':'[0,0][1200,1920]'},'children':nodes}


class FakeBoard:
    """Device model exercising production collection/UI/capture, not a mock verdict."""
    serial = SERIAL
    boot = BOOT
    def __init__(self):
        self.calls=[]
        self.digest=None
        self.clicked=False
        self.image=JPEG
        self.install_rc=0
        self.install_text='install bundle successfully.'
        self.stop_at=None
        self.last_remote=None
    def ready(self):pass
    def shell(self, command, required=True, timeout=60):
        self.calls.append(command)
        if self.stop_at and self.stop_at in command:raise b.BatchStop('simulated detach')
        if command.startswith('bm install'):return self.install_rc,self.install_text
        if command.startswith('bm dump'):return 0,json.dumps({'bundleName':PKG,'uid':20010055})
        if command.startswith('sha256sum '):
            digest=self.digest if 'original.apk' in command else hashlib.sha256(JPEG).hexdigest()
            return 0,digest+'  file'
        if command.startswith('stat '):return 0,f'{len(JPEG)} 1800000000'
        if command.startswith('ps '):
            return 0,'PID PPID UID NAME\n10 1 0 appspawn-x\n1997 1 1003 com.ohos.sceneboard\n'+('42 10 20010055 appspawn-x\n' if self.clicked else '')
        if command.startswith('hidumper '):
            return 0,('WindowName DisplayId Pid WinId Type Mode Flag ZOrd\n'
                'scene 0 1997 7 1 1 0 100\napp 0 42 66 1 1 0 100\nFocus window: %s\n'
                % ('66' if self.clicked else '7'))
        if command=='uitest uiInput click 200 300':self.clicked=True
        if command.startswith('aa force-stop '):self.clicked=False
        if command.startswith('param get'):return 0,'OpenHarmony-6.1.0.31'
        return 0,''
    def send(self, local, remote):
        self.calls.append('send '+remote)
        self.digest=b.sha(local)
    def receive(self, remote, local):
        self.calls.append('receive '+remote)
        if Path(local).exists():raise b.AppFailure('stale evidence')
        if remote.endswith('.json'):Path(local).write_text(json.dumps(icon_tree()))
        else:Path(local).write_bytes(self.image)


class BatchTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory()
        self.root=Path(self.tmp.name)
        appdir=self.root/'inputs'/'app1';appdir.mkdir(parents=True)
        apk=appdir/'base.apk';apk.write_bytes(b'fixture apk bytes')
        digest=b.sha(apk)
        (appdir/'app-input.json').write_text(json.dumps({'application':{'package':PKG,'launch_activity':ABILITY},'apk_sha256':digest}))
        self.entry={'key':'app1','phase':'controls','package':PKG,'apk_sha256':digest,'launch_activity':ABILITY}
    def tearDown(self):self.tmp.cleanup()
    def test_manifest_66_and_order(self):
        apps=b.load_apps(Path(b.__file__).with_name('apps.json'))
        self.assertEqual(len(apps),66)
        self.assertEqual([a['phase'] for a in apps],['controls']*13+['blocked']*43+['tail']*10)
        self.assertEqual(len({a['key'] for a in apps}),66)
    def test_plan_never_calls_subprocess(self):
        with patch.object(subprocess,'run',side_effect=AssertionError('unexpected external command')):
            with contextlib.redirect_stdout(io.StringIO()) as stream:
                self.assertEqual(b.main(['--keys','aegis']),0)
        self.assertEqual(json.loads(stream.getvalue())['execution'],'not-requested')
    def test_wrong_pin_rejected_before_device(self):
        board=FakeBoard();entry=dict(self.entry,apk_sha256='0'*64)
        rec=b.collect_app(board,entry,self.root/'inputs',self.root/'bad','/unique')
        self.assertEqual(rec['status'],'app_failed');self.assertEqual(board.calls,[])
    def test_modified_apk_rejected_before_device(self):
        (self.root/'inputs/app1/base.apk').write_bytes(b'changed')
        board=FakeBoard();rec=b.collect_app(board,self.entry,self.root/'inputs',self.root/'bad','/unique')
        self.assertEqual(rec['status'],'app_failed');self.assertEqual(board.calls,[])
    def test_exact_icon_and_bounds(self):
        self.assertEqual(b.select_icon(icon_tree(),PKG,ABILITY)['center'],[200,300])
        self.assertIsNone(b.select_icon(icon_tree(),PKG,PKG+'.Wrong'))
        self.assertIsNone(b.select_icon(icon_tree(bundle='impostor'),PKG,ABILITY))
    def test_duplicate_and_hidden_icons_rejected(self):
        for tree in [icon_tree(duplicate=True),icon_tree(visible='false')]:
            with self.assertRaises(b.AppFailure):b.select_icon(tree,PKG,ABILITY)
    def test_bad_bundle_not_queryable(self):
        for response in ['failed to get information',json.dumps({'name':'other','uid':20010055})]:
            with self.assertRaises(b.AppFailure):b.parse_bundle(response,PKG)
    def test_bms_launcher_alias_overrides_old_direct_activity(self):
        board=FakeBoard()
        old_shell=board.shell
        def shell(command, required=True, timeout=60):
            if command.startswith('bm dump'):
                return 0,json.dumps({'name':PKG,'uid':20010055,'entryModuleName':'entry',
                    'hapModuleInfos':[{'name':'entry','mainAbility':ABILITY}]})
            return old_shell(command,required,timeout)
        board.shell=shell
        meta=self.root/'inputs/app1/app-input.json'
        data=json.loads(meta.read_text());data['application']['launch_activity']=PKG+'.LegacyDirect'
        meta.write_text(json.dumps(data))
        with patch.object(b.time,'sleep'):
            rec=b.collect_app(board,self.entry,self.root/'inputs',self.root/'alias','/alias')
        self.assertTrue(rec['clicked'])
        self.assertEqual(rec['desktop_activity'],ABILITY)
        self.assertEqual(rec['launch_activity'],PKG+'.LegacyDirect')
    def test_ambiguous_bms_entry_refused(self):
        response=json.dumps({'name':PKG,'uid':20010055,'hapModuleInfos':[
            {'mainAbility':ABILITY},{'mainAbility':PKG+'.Other'}]})
        with self.assertRaisesRegex(b.AppFailure,'ambiguous'):
            b.parse_bundle(response,PKG)
    def test_bms_entry_module_excludes_feature_main(self):
        response=json.dumps({'name':PKG,'uid':20010055,'entryModuleName':'entry','hapModuleInfos':[
            {'name':'feature','mainAbility':PKG+'.Other'},
            {'name':'entry','mainAbility':ABILITY}]})
        self.assertEqual(b.parse_bundle(response,PKG)['desktop_activity'],ABILITY)
    def test_bms_nested_java_activity_is_valid(self):
        response=json.dumps({'name':PKG,'uid':20010055,'hapModuleInfos':[
            {'mainAbility':PKG+'.NfcAPI$NfcActivity'}]})
        self.assertEqual(b.parse_bundle(response,PKG)['desktop_activity'],PKG+'.NfcAPI$NfcActivity')
    def test_existing_capture_rejects_missing_prior_success(self):
        import capture_existing as c
        prior=self.root/'prior.json';prior.write_text(json.dumps({'key':'app1','install':{'return_code':0,'success_text':False}}))
        board=FakeBoard()
        with self.assertRaisesRegex(b.AppFailure,'prior successful'):
            c.capture(board,self.entry,self.root/'inputs',self.root/'capture','/capture',prior)
        self.assertEqual(board.calls,[])
    def test_existing_capture_rejects_different_installed_apk(self):
        import capture_existing as c
        prior=self.root/'prior.json';prior.write_text(json.dumps(dict(self.entry,serial=SERIAL,install={'return_code':0,'success_text':True})))
        board=FakeBoard();board.digest='0'*64
        rec=c.capture(board,self.entry,self.root/'inputs',self.root/'capture','/capture',prior)
        self.assertEqual(rec['status'],'app_failed')
        self.assertIn('installed APK',rec['error'])
        self.assertFalse(rec['clicked'])
        self.assertFalse(any(x.startswith('bm install') for x in board.calls))
    def test_foreground_requires_focus_pid(self):
        text='app 0 42 66 1 1 0 100\nFocus window: 66\n'
        self.assertTrue(b.foreground(text,[42])['confirmed'])
        self.assertFalse(b.foreground(text,[43])['confirmed'])
        self.assertFalse(b.foreground('app process alive',[42])['confirmed'])
    def test_restore_recipe_body_is_unchanged(self):
        root=Path(b.__file__).parent
        source=json.loads((root.parent/'sandbox-prep/source.json').read_text())
        original=(root.parent/'sandbox-prep/source-lines-291-294.sh.txt').read_text()
        self.assertEqual(hashlib.sha256(original.encode()).hexdigest(),source['copied_body_sha256'])
        recipe=(root/'prepare_sandbox.sh').read_text()
        self.assertEqual(recipe.split('    local PACKAGE="$1" APP_UID="$2"\n',1)[1],original+'}\n')
    def test_sandbox_parameters_rejected_before_writes(self):
        for pkg,uid in [('org.x;id',20010055),(PKG,0),(PKG,'20010055'),('../org.x',20010055)]:
            board=FakeBoard()
            with self.assertRaises(b.AppFailure):b.prepare_sandbox(board,pkg,uid,self.root)
            self.assertEqual(board.calls,[])
    def test_sandbox_failure_prevents_launch(self):
        board=FakeBoard();original=board.shell
        def shell(cmd,required=True,timeout=60):
            if cmd.startswith('set -e\nD()'):return 1,'chcon failed'
            return original(cmd,required,timeout)
        board.shell=shell
        rec=b.collect_app(board,self.entry,self.root/'inputs',self.root/'prep-fail','/unique')
        self.assertEqual(rec['status'],'sandbox_prep_failed')
        self.assertFalse(rec['clicked'])
        self.assertIn('sandbox preparation failed',rec['error'])
        receipt=json.loads((self.root/'prep-fail/sandbox-preparation.json').read_text())
        self.assertEqual(receipt['return_code'],1)
        self.assertTrue(Path(receipt['command_path']).is_file())
    def test_simulated_full_collect(self):
        board=FakeBoard()
        with patch.object(b.time,'sleep'):
            rec=b.collect_app(board,self.entry,self.root/'inputs',self.root/'run','/unique',3)
        self.assertEqual(rec['status'],'captured')
        self.assertEqual(rec['review'],'pending_review')
        self.assertEqual(len(rec['screenshots']),2)
        self.assertTrue(rec['bms']['queryable'])
        self.assertTrue(rec['foreground']['confirmed'])
        self.assertTrue(any(c.startswith('bm install -p ') for c in board.calls))
        install=next(i for i,c in enumerate(board.calls) if c.startswith('bm install '))
        prep=next(i for i,c in enumerate(board.calls) if c.startswith('set -e\nD()'))
        click=board.calls.index('uitest uiInput click 200 300')
        self.assertLess(install,prep)
        self.assertLess(prep,click)
        self.assertFalse(any('aa start' in c for c in board.calls))
        self.assertTrue((self.root/'run/record.json').exists())
    def test_failure_keeps_install_return_and_no_launch(self):
        board=FakeBoard();board.install_rc=1;board.install_text='error: install failed'
        rec=b.collect_app(board,self.entry,self.root/'inputs',self.root/'failed','/unique')
        self.assertEqual(rec['install']['return_code'],1)
        self.assertFalse(rec['clicked']);self.assertEqual(rec['status'],'app_failed')
    def test_corrupt_or_stale_capture_rejected(self):
        board=FakeBoard();board.image=b'not jpeg'
        with self.assertRaises(b.AppFailure):b.capture(board,'/unique/image.jpeg',self.root/'bad.jpeg')
        board.image=JPEG
        target=self.root/'stale.jpeg';target.write_bytes(JPEG)
        with self.assertRaises(b.AppFailure):b.capture(board,'/unique/image.jpeg',target)
    def test_detach_stops_before_next_app(self):
        board=FakeBoard();board.stop_at='bm install'
        with self.assertRaises(b.BatchStop):
            b.run_batch(board,[self.entry,dict(self.entry,key='never')],self.root/'inputs',self.root,'unit',3)
        summary=json.loads((self.root/'summary.json').read_text())
        self.assertEqual(summary['not_run'],['never'])
        self.assertEqual(summary['records'][0]['status'],'batch_interrupted')
        self.assertFalse((self.root/'never').exists())
    def test_wrong_serial_refused_before_transport(self):
        with self.assertRaises(b.BatchStop):b.Board('5ea','hdc','board-note','cx-t0',self.root)
    def guard_board(self, lock='cx-t0 100 time', targets=SERIAL, boot=BOOT):
        board=b.Board(SERIAL,'hdc','board-note','cx-t0',self.root)
        def cmd(argv,timeout=60):
            if argv[0]=='board-note':return 0,lock
            return 0,targets
        board.command=cmd
        board.raw_shell=lambda *a,**kw:(0,boot)
        return board
    def test_lock_loss_blocks_shell(self):
        board=self.guard_board(lock='cc-t3 101 time')
        with self.assertRaises(b.BatchStop):board.shell('bm install -p /x')
    def test_detached_serial_blocks_shell(self):
        board=self.guard_board(targets='another')
        with self.assertRaises(b.BatchStop):board.shell('bm install -p /x')
    def test_boot_change_blocks_shell(self):
        board=self.guard_board();board.ready()
        board.raw_shell=lambda *a,**kw:(0,'aaaaaaaa-bbbb-cccc-dddd-eeeeeeeeeeee')
        with self.assertRaises(b.BatchStop):board.shell('bm install -p /x')
    def test_raw_hdc_missing_status_marker_is_fatal(self):
        board=b.Board(SERIAL,'hdc','board-note','cx-t0',self.root)
        board.command=lambda *a,**kw:(0,'[Fail]Device not found')
        with self.assertRaises(b.BatchStop):board.raw_shell('echo test')
    def test_preflight_stop_marks_all_unattempted(self):
        with patch.object(b.Board, 'ready', side_effect=b.BatchStop('no lock')):
            with contextlib.redirect_stderr(io.StringIO()):
                rc=b.main(['--execute','--keys','aegis','--serial',SERIAL,'--lane','cx-t0',
                           '--out',str(self.root),'--run-id','preflight'])
        self.assertEqual(rc,2)
        report=json.loads((self.root/'preflight'/SERIAL/'summary.json').read_text())
        self.assertEqual(report['not_run'],['aegis'])
        self.assertEqual(report['records'],[])

    def test_status_marker_captures_remote_rc(self):
        board=b.Board(SERIAL,'hdc','board-note','cx-t0',self.root)
        def cmd(argv,timeout=60):
            marker=b.re.search(r'(__BMS_REMOTE_RC_[0-9a-f]+__)',argv[-1]).group(1)
            return 0,'install failed\n'+marker+'7\n'
        board.command=cmd
        self.assertEqual(board.raw_shell('false'),(7,'install failed'))


if __name__=='__main__':unittest.main()
