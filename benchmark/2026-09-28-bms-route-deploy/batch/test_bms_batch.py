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
        self.installed=True
        self.uninstall_text='uninstall bundle successfully.'
        self.uninstall_rc=0
        self.wrong_focus=False
        self.fault_listing_count=0
        self.faults_before=['/data/log/faultlog/faultlogger/old-crash']
        self.faults_after=self.faults_before+['/data/log/faultlog/faultlogger/new-crash']
    def ready(self):pass
    def shell(self, command, required=True, timeout=60):
        self.calls.append(command)
        if self.stop_at and self.stop_at in command:raise b.BatchStop('simulated detach')
        if command.startswith('bm install'):
            self.installed=True
            return self.install_rc,self.install_text
        if command.startswith('bm uninstall'):
            self.installed=False
            return self.uninstall_rc,self.uninstall_text
        if command.startswith('bm dump'):
            return (0,json.dumps({'bundleName':PKG,'uid':20010055})) if self.installed else (0,'error: failed to get bundle information.')
        if command.startswith('find '):
            files=self.faults_before if self.fault_listing_count == 0 else self.faults_after
            self.fault_listing_count+=1
            return 0,'\n'.join(files)
        if command.startswith('sha256sum '):
            digest=self.digest if 'original.apk' in command else hashlib.sha256(self.image).hexdigest()
            return 0,digest+'  file'
        if command.startswith('stat '):return 0,f'{len(self.image)} 1800000000'
        if command.startswith('ps '):
            return 0,'PID PPID UID NAME\n10 1 0 appspawn-x\n11 1 1000 com.ohos.sceneboard\n'+('42 10 20010055 appspawn-x\n' if self.clicked else '')
        if command.startswith('hidumper '):
            row='App window with spaces 0 42 66 1 1 0 -1 0 [0 0 100 100]' if self.clicked and not self.wrong_focus else 'SCB Desktop 0 11 66 1 1 0 100'
            return 0,'WindowName DisplayId Pid WinId Type Mode Flag ZOrd\n'+row+'\nFocus window: 66\n'
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
        elif remote.endswith('.jpeg'):Path(local).write_bytes(self.image)
        else:Path(local).write_text('synthetic log: '+remote)


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

    def collect(self, board=None, **options):
        board=board or FakeBoard()
        with patch.object(b.time,'sleep'):
            rec=b.collect_app(board,self.entry,self.root/'inputs',self.root/'run','/unique',**options)
        return board,rec

    def test_reinstall_existing_and_directory_already_created(self):
        (self.root/'run').mkdir()
        board,rec=self.collect(reinstall=True)
        self.assertEqual(rec['status'],'captured')
        un=next(i for i,x in enumerate(board.calls) if x.startswith('bm uninstall '))
        install=next(i for i,x in enumerate(board.calls) if x.startswith('bm install '))
        self.assertLess(un,install)
        self.assertTrue(rec['uninstall']['success_text'])
        self.assertTrue((self.root/'run/uninstall.txt').exists())

    def test_reinstall_missing_target_skips_uninstall(self):
        board=FakeBoard();board.installed=False
        _,rec=self.collect(board,reinstall=True)
        self.assertEqual(rec['status'],'captured')
        self.assertFalse(rec['uninstall']['attempted'])
        self.assertFalse(any(x.startswith('bm uninstall') for x in board.calls))

    def test_reinstall_failure_text_blocks_install_despite_rc_zero(self):
        board=FakeBoard();board.uninstall_text='error: uninstall failed 9568386'
        _,rec=self.collect(board,reinstall=True)
        self.assertEqual(rec['status'],'app_failed')
        self.assertEqual(rec['uninstall']['return_code'],0)
        self.assertFalse(any(x.startswith('bm install') for x in board.calls))

    def test_install_text_error_cannot_be_overridden_by_old_bundle(self):
        board=FakeBoard();board.install_text='install bundle successfully. error: 9568260 internal error'
        _,rec=self.collect(board)
        self.assertFalse(rec['install']['success_text'])
        self.assertFalse(rec['clicked'])
        self.assertEqual(rec['status'],'app_failed')

    def test_unresolved_manifest_package_is_resolved_before_uninstall(self):
        self.entry.update(package=None,launch_activity=None)
        board,rec=self.collect(reinstall=True)
        self.assertEqual(rec['package'],PKG)
        self.assertIn('bm uninstall -n '+PKG,board.calls)
        self.assertTrue(rec['clicked'])

    def test_missing_app_input_refused_without_commands(self):
        (self.root/'inputs/app1/app-input.json').unlink()
        board,rec=self.collect(reinstall=True,hilog_seconds=15,shots=[5,20])
        self.assertEqual(rec['status'],'app_failed')
        self.assertEqual(board.calls,[])

    def test_stale_directory_refused_before_commands(self):
        (self.root/'run').mkdir();(self.root/'run/record.json').write_text('old evidence')
        board=FakeBoard()
        with self.assertRaisesRegex(b.BatchStop,'stale'):
            self.collect(board)
        self.assertEqual(board.calls,[])
        self.assertEqual((self.root/'run/record.json').read_text(),'old evidence')

    def test_hilog_and_shots_run_on_click_relative_schedule(self):
        board=FakeBoard();clock=[100.0];events=[]
        original=board.shell
        def shell(cmd,required=True,timeout=60):
            events.append((cmd,clock[0]))
            return original(cmd,required,timeout)
        board.shell=shell
        with patch.object(b.time,'monotonic',side_effect=lambda:clock[0]), patch.object(b.time,'sleep',side_effect=lambda delay:clock.__setitem__(0,clock[0]+delay)):
            rec=b.collect_app(board,self.entry,self.root/'inputs',self.root/'run','/unique',
                              shots=[5,20],hilog_seconds=15,focus_check=True)
        self.assertEqual(rec['status'],'captured')
        self.assertEqual([x['elapsed_seconds'] for x in rec['screenshots']],[5,20])
        self.assertTrue(all(x['foreground']['pid']==42 and x['foreground']['window_id']==66 and x['accepted'] for x in rec['screenshots']))
        self.assertEqual(rec['diagnostics']['elapsed_seconds'],15)
        reset=next(i for i,x in enumerate(board.calls) if x=='hilog -r')
        self.assertLess(reset,board.calls.index('uitest uiInput click 200 300'))
        dump=next(t for cmd,t in events if cmd.startswith('hilog -x'))
        self.assertEqual(dump,115)
        received=[x for x in board.calls if x.startswith('receive /data/log')]
        self.assertEqual(received,['receive /data/log/faultlog/faultlogger/new-crash'])
        self.assertTrue((self.root/'run/hilog.txt').exists())
        # The immediately preceding command to each snapshot is the focus dump.
        for i,cmd in enumerate(board.calls):
            if cmd.startswith('snapshot_display'):
                self.assertTrue(board.calls[i-1].startswith('hidumper '))

    def test_each_shot_refreshes_focus_and_does_not_promote_weak_match(self):
        board=FakeBoard();base=board.shell;probes=[0]
        def shell(cmd,required=True,timeout=60):
            if cmd.startswith('hidumper') and board.clicked:
                probes[0]+=1
                if probes[0]==1:
                    return 0,'Some other app 0 777 123 1 1 0 -1\nFocus window: 123\n'
            return base(cmd,required,timeout)
        board.shell=shell
        _,rec=self.collect(board,shots=[5,20])
        self.assertEqual(rec['status'],'foreground_unconfirmed')
        self.assertFalse(rec['screenshots'][0]['accepted'])
        self.assertTrue(rec['screenshots'][1]['accepted'])
        self.assertEqual(rec['screenshots'][0]['foreground']['pid'],777)
        self.assertFalse(rec['screenshots'][0]['captured'])
        self.assertEqual(sum(x.startswith('snapshot_display') for x in board.calls),1)

    def test_focus_check_applies_to_default_early_shot(self):
        board=FakeBoard();board.wrong_focus=True
        _,rec=self.collect(board,focus_check=True)
        self.assertEqual(rec['status'],'foreground_unconfirmed')
        self.assertTrue(all(not x['accepted'] for x in rec['screenshots']))

    def test_known_black_frame_keeps_bytes_but_cannot_pass(self):
        board=FakeBoard();board.image=b'\xff\xd8'+b'x'*(b.BLACK_FRAME_BYTES-4)+b'\xff\xd9'
        _,rec=self.collect(board,shots=[5,20])
        self.assertEqual(rec['status'],'capture_rejected')
        self.assertTrue(all(x['known_black_frame'] and not x['accepted'] for x in rec['screenshots']))
        self.assertTrue(all(Path(x['path']).stat().st_size==36627 for x in rec['screenshots']))
        self.assertEqual(rec['review'],'pending_review')

    def test_diagnostic_detach_stops_without_cleanup_writes(self):
        board=FakeBoard();board.stop_at='hilog -x'
        with self.assertRaises(b.BatchStop):
            self.collect(board,hilog_seconds=15)
        self.assertTrue(board.calls[-1].startswith('hilog -x'))
        rec=json.loads((self.root/'run/record.json').read_text())
        self.assertEqual(rec['status'],'batch_interrupted')

    def test_bad_faultlog_path_never_received(self):
        board=FakeBoard();board.faults_after=['/data/log/faultlog/faultlogger/../../private']
        _,rec=self.collect(board,hilog_seconds=15)
        self.assertEqual(rec['status'],'app_failed')
        self.assertFalse(any('receive /data/log' in x for x in board.calls))

    def test_focus_parser_handles_spaces_negative_zorder_and_unknown(self):
        good='App title with spaces 0 42 61 1001 1 0 -1 0 [0 0 1200 1920]\nFocus window: 61\n'
        self.assertTrue(b.foreground(good,[42])['confirmed'])
        for text in ('Focus window: 61',good.replace('0 42 61','0 -1 61'),good+'Other app 0 99 61 1001 1 0 -1\n'):
            self.assertFalse(b.foreground(text,[42])['confirmed'])

    def test_launcher_unknown_retries_but_foreign_owner_stops(self):
        board=FakeBoard();base=board.shell;seen=[0]
        def shell(cmd,required=True,timeout=60):
            if cmd.startswith('hidumper'):
                seen[0]+=1
                if seen[0]<3:return 0,'Focus window: 66'
            return base(cmd,required,timeout)
        board.shell=shell
        with patch.object(b.time,'sleep'):
            self.assertEqual(b.launcher_focused(board),11)
        self.assertEqual(seen[0],3)
        board=FakeBoard();base=board.shell
        board.shell=lambda cmd,**kw:(0,'foreign 0 777 88 1 1 0 0\nFocus window: 88') if cmd.startswith('hidumper') else base(cmd,**kw)
        with self.assertRaises(b.BatchStop):b.launcher_focused(board)

    def test_empty_lock_and_targets_retry_without_weakening_holder(self):
        board=self.guard_board();calls=[];remaining={'board-note':1,'hdc':1}
        def cmd(argv,timeout=60):
            calls.append(argv)
            if remaining[argv[0]]:
                remaining[argv[0]]-=1;return 0,''
            return (0,'cx-t0 100 now') if argv[0]=='board-note' else (0,SERIAL)
        board.command=cmd
        with patch.object(b.time,'sleep'):board.ready()
        self.assertEqual(len(calls),4)
        board=self.guard_board(lock='wrong-holder 1 now')
        with patch.object(b.time,'sleep') as sleep:
            with self.assertRaises(b.BatchStop):board.ready()
        sleep.assert_not_called()

    def test_cli_options_are_in_offline_plan_and_invalid_offsets_rejected(self):
        with patch.object(subprocess,'run',side_effect=AssertionError('device command')):
            with contextlib.redirect_stdout(io.StringIO()) as output:
                self.assertEqual(b.main(['--keys','x,noice','--reinstall','--hilog','12','--shots','5,20','--focus-check']),0)
            options=json.loads(output.getvalue())['options']
            self.assertEqual(options,dict(reinstall=True,hilog_seconds=12,shots=[5,20],focus_check=True))
            for args in (['--shots','20,5'],['--shots','5,5'],['--shots','nan'],['--shots','0,20'],['--hilog','nan'],['--hilog','-1'],['--wait','inf']):
                with self.subTest(args=args),contextlib.redirect_stderr(io.StringIO()):
                    with self.assertRaises(SystemExit):b.main(args)

    def test_bare_hilog_defaults_to_wait_and_one_second_is_explicit(self):
        for args,expected in ((['--hilog','--wait','22'],22),(['--hilog','1'],1)):
            with contextlib.redirect_stdout(io.StringIO()) as stream:
                self.assertEqual(b.main(['--keys','aegis']+args),0)
            self.assertEqual(json.loads(stream.getvalue())['options']['hilog_seconds'],expected)

    def test_nearby_shot_offsets_have_distinct_filenames(self):
        _,rec=self.collect(shots=[5.0000001,5.0000002])
        self.assertEqual(rec['status'],'captured')
        self.assertEqual(len({x['path'] for x in rec['screenshots']}),2)

    def test_empty_guard_response_still_stops_after_bounded_retry(self):
        board=self.guard_board(lock='')
        with patch.object(b.time,'sleep') as sleep:
            with self.assertRaisesRegex(b.BatchStop,'hold board lock'):board.ready()
        sleep.assert_called_once_with(2)
        board=self.guard_board(targets='')
        with patch.object(b.time,'sleep') as sleep:
            with self.assertRaisesRegex(b.BatchStop,'detached'):board.ready()
        sleep.assert_called_once_with(2)

    def test_install_receipt_survives_transport_loss_on_stage_cleanup(self):
        board=FakeBoard();board.stop_at='rm -f /unique/original.apk'
        with self.assertRaises(b.BatchStop):self.collect(board)
        rec=json.loads((self.root/'run/record.json').read_text())
        self.assertTrue(rec['install']['success_text'])
        self.assertEqual(rec['status'],'batch_interrupted')

    def test_stale_record_never_becomes_current_batch_result(self):
        directory=self.root/'app1';directory.mkdir()
        (directory/'record.json').write_text(json.dumps({'key':'app1','status':'captured','old':True}))
        with self.assertRaises(b.StaleEvidence):
            b.run_batch(FakeBoard(),[self.entry],self.root/'inputs',self.root,'unit',3)
        summary=json.loads((self.root/'summary.json').read_text())
        self.assertEqual(summary['records'],[])
        self.assertEqual(summary['not_run'],['app1'])


if __name__=='__main__':unittest.main()
