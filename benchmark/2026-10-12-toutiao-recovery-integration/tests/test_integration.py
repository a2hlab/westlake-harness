"""New integration tests only. Real source logic, explicit fixture path relocation."""
import hashlib, importlib.util, json, os, re, shlex, shutil, socket, subprocess, tempfile, unittest
from pathlib import Path

D = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location('preview', D / 'preview.py')
preview = importlib.util.module_from_spec(spec); spec.loader.exec_module(preview)

class BindingsTests(unittest.TestCase):
    def test_wrong_helper_alias_and_user_data_target_are_rejected(self):
        with tempfile.TemporaryDirectory() as td:
            p=Path(td);shutil.copytree(D/'sources',p/'sources');shutil.copytree(D/'payload',p/'payload')
            baseline=json.loads((D/'bindings.json').read_text())
            for kind in ['helper','alias','data_target']:
                b=json.loads(json.dumps(baseline))
                if kind=='helper':b['watchdog_aliases'][0]['helper_here']='/wrong/route-b-owner.sh'
                elif kind=='alias':b['watchdog_aliases'][1]=dict(b['watchdog_aliases'][0])
                else:b['member_layout'][0]['target']=b['runtime']+'/app-data/user-data'
                (p/'bindings.json').write_text(json.dumps(b));self.assertTrue(preview.validate(p)[1],kind)
    def test_real_sources_and_aliases_are_bound(self):
        b, errors = preview.validate(); self.assertEqual(errors, [])
        self.assertEqual(len(b['watchdog_aliases']), 2)
        self.assertFalse(b['execution_enabled'])
        self.assertTrue(b['pending'])  # Unknown live/format facts are not invented.
        self.assertTrue(b['old_stop']['must_not_clear'])
    def test_missing_and_drift_fail_closed(self):
        with tempfile.TemporaryDirectory() as td:
            p = Path(td); shutil.copytree(D / 'sources', p / 'sources')
            shutil.copytree(D / 'payload', p / 'payload')
            shutil.copyfile(D / 'bindings.json', p / 'bindings.json')
            self.assertEqual(preview.validate(p)[1], [])
            f = p / 'sources/real-spawn'; f.write_text('changed')
            self.assertTrue(preview.validate(p)[1])
            f.unlink(); self.assertTrue(preview.validate(p)[1])

class PreviewTests(unittest.TestCase):
    def test_preview_and_rejected_execute_have_no_commands_or_data_change(self):
        with tempfile.TemporaryDirectory() as td:
            r = Path(td); (r / 'stop').write_bytes(b''); (r / 'sentinel').write_text('user consent data')
            fake = r / 'bin'; fake.mkdir()
            for n in ['hdc', 'orb', 'ssh', 'kill', 'uinput']:
                f = fake / n; f.write_text('#!/bin/sh\necho forbidden >> "$CALL_LOG"\nexit 99\n'); f.chmod(0o755)
            env = dict(os.environ, PATH=str(fake)+':'+os.environ['PATH'], CALL_LOG=str(r/'calls'))
            for args, rc in [([], 0), (['--execute'], 2), (['--authorization', str(r/'unsigned')], 2)]:
                out = subprocess.run(['python3', str(D/'preview.py'), *args], env=env, capture_output=True, text=True)
                self.assertEqual(out.returncode, rc, out.stderr)
                self.assertEqual(json.loads(out.stdout)['device_calls'], 0)
            self.assertFalse((r/'calls').exists()); self.assertEqual((r/'stop').read_bytes(), b'')
            self.assertEqual((r/'sentinel').read_text(), 'user consent data')

class LaunchTests(unittest.TestCase):
    def case(self, mode='normal'):
        with tempfile.TemporaryDirectory(prefix='tt-integration-') as td:
            r = Path(td); state=r/'state'; rt=r/'runtime'; stage=r/'stage'; bindir=r/'bin'
            for x in [state, rt, stage, bindir, r/'proc/1', r/'proc/sys/kernel/random', r/'device-data/local/tmp/asx']:
                x.mkdir(parents=True, exist_ok=True)
            (r/'proc/sys/kernel/random/boot_id').write_text('fixture-boot\n'); (r/'proc/uptime').write_text('254.0 0\n')
            for n in ['app-data','data','webview-t-data']:
                (rt/n).mkdir(); (rt/n/'sentinel').write_text('user-'+n)
            oldstop=r/'device-data/local/tmp/operator45/selfheal48/stop';oldstop.parent.mkdir(parents=True);oldstop.write_bytes(b'')
            record=Path(__file__).with_name('record_command.py')
            for n in ['sha256sum','readlink','stat','hidumper','sed','nohup','nsenter','timeout','snapshot_display','screen-gate','sleep','chown','chmod','ls','kill','hdc','orb','ssh','uinput']:
                x=bindir/n; shutil.copyfile(record,x);x.chmod(0o755)
            # Explicit path-only relocation: original SHA and relocated SHA are both recorded.
            # Native helpers are external recording substitutes, never executed ARM binaries.
            mapping=[('/dev/unix/socket/A2HSourcec91d26bfb4db4fd5a002',str(r/'socket')),('/data/local/tmp/a2hlab-app-c91d26bfb4db4fd5a002287011c4916d',str(stage)),('/data/app/el2/100/base/org.westlake.imehost/files/a2hlab-source-c91d26bfb4db4fd5a002287011c4916d',str(rt)),('/system/bin/sh','/bin/bash'),('/bin/nsenter',str(bindir/'nsenter')),('/proc',str(r/'proc')),('/data',str(r/'device-data'))]
            provenance=[]
            for x in (D/'payload').glob('*.sh'):
                text=x.read_text()
                # One lexical pass at absolute-path starts; never recursively
                # rewrite a replacement or the second /data in /data/data.
                replacements=dict(mapping)
                pattern=r'(?<![A-Za-z0-9_./])('+ '|'.join(re.escape(a) for a,b in mapping)+r')'
                rendered=re.sub(pattern,lambda m:replacements[m.group(1)],text)
                target=state/{'spawn-prepared.sh':'spawn.sh','start-parent-prepared.sh':'start-parent.sh'}.get(x.name,x.name)
                target.write_text(rendered)
                provenance.append({'source':str(x.relative_to(D)),'original_sha256':hashlib.sha256(text.encode()).hexdigest(),'relocated_sha256':hashlib.sha256(rendered.encode()).hexdigest()})
            # Existing-parent positive path; new-parent source is separately exercised below.
            p=r/'proc/100';p.mkdir();(p/'stat').write_text('100 (fixture) S 1 '+' '.join(['0']*17)+' 123 0\n');(p/'status').write_text('Uid:\t0\t0\t0\t0\n')
            (p/'environ').write_bytes(b'WL_PARENT_ID=1443\x00' if mode=='stale_window' else b'WL_PARENT_ID=777\x00')
            (rt/'run.sh').write_text('export WL_PARENT_ID=1443\n')
            for n in ['host_spawn','source_app_namespace']:
                x=stage/n;shutil.copyfile(record,x);x.chmod(0o755)
            (stage/'request.bin').write_bytes((D/'payload/request-uid20011206.bin').read_bytes())
            (rt/'prepare_jit50.sh').write_text((state/'prepare_jit50-uid20011206.sh').read_text())
            view=p/'root/data/local/tmp/asx';view.mkdir(parents=True)
            if mode=='jit_parent_mismatch': (view/'prepare_jit50.sh').write_text('wrong private namespace JIT')
            else:(view/'prepare_jit50.sh').symlink_to(rt/'prepare_jit50.sh')
            (r/'device-data/local/tmp/asx/prepare_jit50.sh').symlink_to(rt/'prepare_jit50.sh')
            (state/'screen-gate').symlink_to(bindir/'screen-gate')
            (r/'model.json').write_text(json.dumps({'jit_fail':mode=='jit_fail','window_missing':mode=='window_missing'}))
            sock=socket.socket(socket.AF_UNIX); sock.bind(str(r/'socket'))
            sha=lambda x:hashlib.sha256(x.read_bytes()).hexdigest()
            auth={'AUTH_APPROVED_BY':'outer(codex)','AUTH_NEW_ATTEMPT':'yes','AUTH_RETAIN_OLD_STOP':'yes','AUTH_SERIAL':'61b0657200000000000000000324012c','AUTH_EXPIRES_EPOCH':'9999999999','AUTH_BOOT':'fixture-boot','AUTH_UID':'20011206','AUTH_STATE_ROOT':str(state),'AUTH_OLD_STOP_SHA':sha(oldstop),'AUTH_CAPTURE_FORMAT_VERIFIED':'yes','AUTH_RUNTIME_BINDINGS_VERIFIED':'yes','AUTH_CANDIDATE_SHA':'9763171a0b6dab1b23b72e454cb2c6256181298bc282e81b6ae8e38fa9577072','AUTH_PARENT_MODE':'existing','AUTH_PARENT_PID':'100','AUTH_PARENT_BIRTH':'123','AUTH_RUNTIME':str(rt),'AUTH_STAGE':str(stage),'AUTH_SOCKET':str(r/'socket'),'AUTH_JIT_SHA':sha(rt/'prepare_jit50.sh'),'AUTH_HOST_SPAWN_SHA':sha(stage/'host_spawn'),'AUTH_REQUEST_SHA':sha(stage/'request.bin')}
            auth.update(AUTH_HELPER_SHA=sha(state/'route-b-owner.sh'),AUTH_WATCHDOG_FILE_SHA=sha(state/'watchdog.sh'))
            auth['AUTH_WAIT_FOR_TAP_SECONDS']='1'
            auth.update(AUTH_NAMESPACE_SHA=sha(stage/'source_app_namespace'),AUTH_START_PARENT_SHA=sha(state/'real-start-parent.sh'))
            # Fixture-only alteration of the exact new-state guard to the temp dir,
            # not a production capability or authorization.
            f=state/'entry.sh';f.write_text(f.read_text().replace(str(r/'device-data/westlake-demo/toutiao/recovery-attempts')+'/*',str(state)))
            if mode=='wrong_boot': auth['AUTH_BOOT']='wrong-boot'
            if mode=='expired': auth['AUTH_EXPIRES_EPOCH']='1'
            if mode=='wrong_candidate': auth['AUTH_CANDIDATE_SHA']='4d3a8e53'
            if mode=='format': auth['AUTH_CAPTURE_FORMAT_VERIFIED']='no'
            if mode=='missing_jit': (rt/'prepare_jit50.sh').unlink()
            if mode=='helper': (state/'route-b-owner.sh').unlink()
            if mode=='socket': sock.close();(r/'socket').unlink()
            if mode=='new_parent':
                sock.close();(r/'socket').unlink();auth['AUTH_PARENT_MODE']='new'
                shutil.rmtree(r/'proc/100')
            af=r/'auth.env';af.write_text('# SYNTHETIC fixture ticket, NOT an outer authorization\n'+'\n'.join(k+'='+shlex.quote(v) for k,v in auth.items())+'\n')
            (state/'authorization.expected.sha256').write_text('NONE\n' if mode=='unsigned' else ('0'*64+'\n' if mode=='wrong_auth_sha' else sha(af)+'\n'))
            init=r/'bash-env';init.write_text('/bin/mkdir -p "$CASE_ROOT/proc/$$"\nprintf "%s (supervisor) S 1 " "$$" > "$CASE_ROOT/proc/$$/stat"\nprintf "0 %.0s" {1..17} >> "$CASE_ROOT/proc/$$/stat"\nprintf " 123 0\\n" >> "$CASE_ROOT/proc/$$/stat"\nkill(){ "$CASE_ROOT/bin/kill" "$@"; }\n')
            env=dict(os.environ, CASE_ROOT=str(r),BASH_ENV=str(init),PATH=str(bindir)+':'+os.environ['PATH'],TT_MAX_POLLS='2',TT_SOCKET=str(r/'socket'))
            before={n:sha(rt/n/'sentinel') for n in ['app-data','data','webview-t-data']}
            out=subprocess.run(['/bin/bash',str(state/'entry.sh'),str(af)],env=env,capture_output=True,text=True,timeout=20)
            calls=[json.loads(x) for x in (r/'commands.jsonl').read_text().splitlines()] if (r/'commands.jsonl').exists() else []
            after={n:sha(rt/n/'sentinel') for n in before};self.assertEqual(before,after);self.assertEqual(oldstop.read_bytes(),b'')
            self.assertFalse(set(x['command'] for x in calls)&{'kill','hdc','orb','ssh','uinput'})
            evidence=D/'evidence/launch-cases';evidence.mkdir(exist_ok=True);c=Path(tempfile.mkdtemp(prefix=mode+'-',dir=evidence))
            (c/'commands.jsonl').write_text(''.join(json.dumps(x)+'\n' for x in calls));(c/'stdout.txt').write_text(out.stdout);(c/'stderr.txt').write_text(out.stderr)
            logs={str(x.relative_to(state)):x.read_text(errors='replace') for x in state.glob('*.txt')}
            (c/'control-logs.json').write_text(json.dumps(logs,indent=2))
            out.evidence_diagnostics=out.stderr+'\n'+'\n'.join(logs.values())
            out.window_run=(rt/'run.sh').read_text()
            (c/'case.json').write_text(json.dumps({'mode':mode,'exit':out.returncode,'sources':provenance,'sentinels_before':before,'sentinels_after':after,'old_stop_preserved':True,'grading':'relocated real shell logic; synthetic native/identity/capture; not device evidence'},indent=2))
            sock.close()
            return out,calls, (state/'state').read_text() if (state/'state').is_file() else None
    def test_unsigned_wrong_boot_expiry_refuse_without_launch(self):
        for mode in ['unsigned','wrong_boot','expired','wrong_candidate','wrong_auth_sha']:
            with self.subTest(mode=mode):
                out,calls,state=self.case(mode);self.assertNotEqual(out.returncode,0,out.stderr)
                self.assertIn({'unsigned':'UNSIGNED_NEW_ATTEMPT','wrong_boot':'WRONG_BOOT','expired':'AUTH_EXPIRED','wrong_candidate':'WRONG_CANDIDATE','wrong_auth_sha':'AUTH_SHA_MISMATCH'}[mode],out.stderr)
                self.assertFalse(set(x['command'] for x in calls)&{'host_spawn','nsenter'})
    def test_normal_namespace_jit_then_real_spawn_source(self):
        out,calls,state=self.case();self.assertEqual(out.returncode,0,out.stderr)
        names=[x['command'] for x in calls];self.assertLess(names.index('nsenter'),names.index('host_spawn'))
        self.assertEqual(state.strip(),'READY') # Synthetic classifier only.
    def test_real_start_parent_updates_window_before_namespace_jit_spawn(self):
        out,calls,state=self.case('new_parent');self.assertEqual(out.returncode,0,out.stderr)
        names=[x['command'] for x in calls]
        for first,second in [('hidumper','sed'),('sed','source_app_namespace'),('source_app_namespace','nsenter'),('nsenter','host_spawn')]:
            self.assertLess(names.index(first),names.index(second))
        self.assertIn('WL_PARENT_ID=777',out.window_run)
        self.assertEqual(state.strip(),'READY')
    def test_missing_prerequisites_refuse(self):
        for mode in ['missing_jit','helper','socket','format','jit_fail','jit_parent_mismatch','window_missing','stale_window']:
            with self.subTest(mode=mode):
                out,calls,state=self.case(mode);self.assertNotEqual(out.returncode,0,out.stderr)
                self.assertIn({'missing_jit':'JIT_MISSING','helper':'MISSING_HELPER','socket':'SOCKET_NOT_READY','format':'CAPTURE_FORMAT_PENDING','jit_fail':'JIT_PREPARE_FAILED','jit_parent_mismatch':'JIT_PARENT_SHA_CHANGED','window_missing':'FOREGROUND_HOST_NOT_READY','stale_window':'PARENT_WINDOW_CHANGED'}[mode],out.evidence_diagnostics)
                self.assertFalse(any(x['command']=='host_spawn' for x in calls))

if __name__=='__main__': unittest.main(verbosity=2)
