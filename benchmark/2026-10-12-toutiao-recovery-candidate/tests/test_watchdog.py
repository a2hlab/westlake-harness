"""Run the real R1 shell with isolated proc/data and recording fake commands."""
import json, os, subprocess, tempfile, unittest, hashlib
from pathlib import Path

D = Path(__file__).resolve().parents[1]
WATCH = D / 'payload/watchdog.sh'
TOOL = Path(__file__).with_name('fixture_tool.py')

class Harness(unittest.TestCase):
    def run_case(self, model=None, polls=4, stop=False, lock=None, execute=True, env_extra=None):
        with tempfile.TemporaryDirectory(prefix='r1-case-') as td:
            root = Path(td)
            for d in ['proc/sys/kernel/random', 'proc/1/ns', 'runtime', 'state', 'stage', 'bin']:
                (root / d).mkdir(parents=True, exist_ok=True)
            (root / 'proc/sys/kernel/random/boot_id').write_text('fixture-boot\n')
            (root / 'proc/uptime').write_text('254.00 1000\n')
            (root / 'runtime/run.sh').write_text('existing runtime\n')
            sentinels = {}
            for name in ['app-data', 'data', 'webview-t-data']:
                path = root / 'runtime' / name; path.mkdir()
                (path / 'sentinel').write_text('user-' + name)
                sentinels[name] = hashlib.sha256((path / 'sentinel').read_bytes()).hexdigest()
            for name in ['cat', 'mkdir', 'rm', 'rmdir', 'cp', 'readlink', 'sha256sum', 'stat', 'timeout', 'sleep', 'snapshot_display', 'screen-gate', 'parent_tool', 'spawn_tool', 'uinput', 'kill', 'pkill', 'killall', 'reboot', 'setenforce', 'begetctl', 'chown', 'chcon', 'mount']:
                f = root / 'bin' / name
                f.write_text('#!' + os.sys.executable + '\n' + TOOL.read_text()); f.chmod(0o755)
            for name, tool in [('start-parent.sh', 'parent_tool'), ('spawn.sh', 'spawn_tool')]:
                (root / 'state' / name).write_text(tool + '\n')
            (root / 'state/screen-gate').symlink_to(root / 'bin/screen-gate')
            if stop: (root / 'state/stop').write_text('original operator stop')
            if model and model.get('state_alias'):
                (root / 'alias').symlink_to(root / 'runtime/app-data')
            if model and model.get('stale_frame'):
                (root / 'state/current.jpeg').write_text('old feed frame')
            if lock is not None:
                (root / 'state/lock').mkdir()
                if lock != 'ownerless': (root / 'state/lock/owner').write_text(lock)
            (root / 'model.json').write_text(json.dumps(model or {}))
            # bash loads this only for the test, creating a readable synthetic self identity.
            init = root / 'bash-env'
            init.write_text('/bin/mkdir -p "$TT_PROC/$$"\nprintf "%s (watchdog) S " "$$" > "$TT_PROC/$$/stat"\nprintf "0 %.0s" {1..18} >> "$TT_PROC/$$/stat"\nprintf "777 0\\n" >> "$TT_PROC/$$/stat"\nkill(){ command "$CASE_ROOT/bin/kill" "$@"; }\n')
            env = dict(os.environ, CASE_ROOT=str(root), BASH_ENV=str(init), TT_STATE_ROOT=str(root / 'state'), TT_OPERATOR_ROOT=str(root), TT_RUNTIME=str(root / 'runtime'), TT_STAGE=str(root / 'stage'), TT_PROC=str(root / 'proc'), TT_OWNER_UID='20011206', TT_EXPECT_BOOT='fixture-boot', TT_MAX_POLLS=str(polls), TT_MAX_ATTEMPTS='3', TT_SOCKET=str(root / 'socket'), TT_RECOVERY_EXECUTE='1' if execute else '0', PATH=str(root / 'bin') + ':' + os.environ['PATH'])
            env.update({k: str(v).replace('$RUNTIME', str(root / 'runtime')) for k, v in (env_extra or {}).items()})
            if model and model.get('state_alias'):
                env['TT_STATE_ROOT'] = str(root / 'alias')
            if model and model.get('attach_existing'):
                # Existing process fixture is created BEFORE invoking the candidate.
                for pid, uid, ppid in [(100, '0', 1), (200, '20011206', 100)]:
                    d = root / 'proc' / str(pid); d.mkdir()
                    (d / 'ns').mkdir()
                    (d / 'role').write_text('parent' if pid == 100 else 'child')
                    (d / 'status').write_text('Uid:\t' + '\t'.join([uid] * 4) + '\n')
                    (d / 'stat').write_text(f'{pid} (fixture) S {ppid} ' + ' '.join(['0'] * 17) + ' 123 0\n')
                (root / 'state/sequence').write_text('118\n')
                env.update(TT_PARENT_PID='100', TT_PARENT_BIRTH='123', TT_CHILD_PID='200', TT_CHILD_BIRTH='123')
            if model and model.get('fail_before_launch'):
                (root / 'state' / model['fail_before_launch']).mkdir()
            proc = subprocess.run(['/bin/bash', str(WATCH)], env=env, capture_output=True, text=True, timeout=15)
            calls = [json.loads(l) for l in (root / 'calls.jsonl').read_text().splitlines()] if (root / 'calls.jsonl').exists() else []
            files = {str(p.relative_to(root)): p.read_bytes().decode(errors='replace') for p in (root / 'state').rglob('*') if p.is_file() and not p.is_symlink()}
            # Preserve original command recordings and results, not only the test summary.
            case_root = Path(os.environ.get('R1_TEST_EVIDENCE', str(D / 'evidence/cases')))
            case_root.mkdir(parents=True, exist_ok=True)
            case = Path(tempfile.mkdtemp(prefix='case-', dir=case_root))
            (case / 'commands.jsonl').write_text(''.join(json.dumps(c) + '\n' for c in calls))
            (case / 'stdout.txt').write_text(proc.stdout)
            (case / 'stderr.txt').write_text(proc.stderr)
            (case / 'state-files.json').write_text(json.dumps(files, indent=2))
            (case / 'case.json').write_text(json.dumps({'test': self.id(), 'candidate_sha256': hashlib.sha256(WATCH.read_bytes()).hexdigest(), 'model': model or {}, 'polls': polls, 'stop': stop, 'lock': lock, 'execute': execute, 'returncode': proc.returncode, 'sentinel_before': sentinels, 'sentinel_after': {n: hashlib.sha256((root / 'runtime' / n / 'sentinel').read_bytes()).hexdigest() for n in sentinels}}, indent=2))
            for name, sha in sentinels.items():
                self.assertEqual(hashlib.sha256((root / 'runtime' / name / 'sentinel').read_bytes()).hexdigest(), sha)
            self.assertFalse(list((root / 'runtime').glob('operator-selfheal-*')))
            self.assertFalse(set(c['command'] for c in calls) & {'uinput', 'kill', 'pkill', 'killall', 'reboot', 'setenforce', 'begetctl', 'chown', 'chcon', 'mount'})
            return proc, calls, files

class ConsentTests(Harness):
    def test_privacy_then_manual_feed_no_touch_and_no_consent_flag(self):
        p, c, f = self.run_case({'frames': ['privacy', 'feed', 'feed']})
        self.assertEqual(p.returncode, 0, p.stderr)
        self.assertIn('privacy_no_touch', f['state/events.log'])
        self.assertEqual(f['state/state'].strip(), 'READY')
        self.assertIn('feed_confirmed_without_auto_consent', f['state/events.log'])
        self.assertEqual(sum(x['command'] == 'snapshot_display' for x in c), 3)

    def test_snapshot_failure_unknown_and_classifier_failure_do_not_kill_or_claim_ready(self):
        for model in [{'frames': ['snapshot_error'], 'stale_frame': True}, {'frames': ['unknown']}, {'frames': ['feed'], 'classifier_fail': True}]:
            with self.subTest(model=model):
                p, c, f = self.run_case(model)
                self.assertEqual(p.returncode, 0, p.stderr)
                self.assertEqual(f['state/state'].strip(), 'UI_UNVERIFIED')
                self.assertNotIn('reason=feed_confirmed', f['state/events.log'])
                self.assertIn('alive_no_cleanup', f['state/events.log'])
                self.assertEqual(sum(x['command'] == 'spawn_tool' for x in c), 1)

class DataTests(Harness):
    def test_same_boot_explicit_reentry_preserves_parent_child_and_sequence(self):
        p, c, f = self.run_case({'attach_existing': True, 'frames': ['feed', 'feed']})
        self.assertEqual(p.returncode, 0, p.stderr)
        self.assertEqual(f['state/state'].strip(), 'READY')
        self.assertEqual(f['state/sequence'].strip(), '119')
        self.assertIn('parent=100', f['state/instance.txt'])
        self.assertFalse(set(x['command'] for x in c) & {'parent_tool', 'spawn_tool'})

    def test_exit_retries_preserve_data_and_parent_with_bound_and_backoff(self):
        p, c, f = self.run_case({'exit_every_sleep': True}, polls=20)
        self.assertEqual(p.returncode, 4, p.stderr)
        self.assertEqual(sum(x['command'] == 'spawn_tool' for x in c), 3)
        self.assertEqual(sum(x['command'] == 'parent_tool' for x in c), 1)
        self.assertEqual(f['state/state'].strip(), 'RETRY_LIMIT')
        log = f['state/events.log']
        for field in ['boot=fixture-boot', 'seq=', 'child=', 'child_birth=', 'parent=', 'parent_birth=', 'retry_backoff_seconds=5', 'retry_backoff_seconds=10']:
            self.assertIn(field, log)

    def test_spawn_failure_is_observable_not_silent_success(self):
        p, c, f = self.run_case({'spawn_fail': True})
        self.assertEqual(p.returncode, 3)
        self.assertIn('spawn_command_nonzero', f['state/events.log'])

class OwnershipTests(Harness):
    def test_owner_write_or_exact_readback_failure_blocks_all_launch(self):
        for model in [{'owner_directory': True}, {'owner_readback_wrong': True}]:
            with self.subTest(model=model):
                p, c, f = self.run_case(dict(model, frames=['feed', 'feed']))
                self.assertNotEqual(p.returncode, 0, p.stderr)
                self.assertFalse(set(x['command'] for x in c) & {'parent_tool', 'spawn_tool'})
                self.assertNotEqual(f.get('state/state', '').strip(), 'READY')

    def test_control_persistence_failure_before_launch_stops_without_launch(self):
        for path in ['sequence', 'instance.txt', 'state', 'events.log']:
            with self.subTest(path=path):
                p, c, f = self.run_case({'fail_before_launch': path, 'frames': ['feed', 'feed']})
                self.assertNotEqual(p.returncode, 0, p.stderr)
                self.assertFalse(set(x['command'] for x in c) & {'parent_tool', 'spawn_tool'})
                self.assertNotEqual(f.get('state/state', '').strip(), 'READY')

    def test_control_persistence_failure_after_spawn_preserves_app_and_stops(self):
        for path in ['sequence', 'instance.txt', 'state', 'events.log']:
            with self.subTest(path=path):
                p, c, f = self.run_case({'fail_after_spawn': path, 'frames': ['feed', 'feed']})
                self.assertNotEqual(p.returncode, 0, p.stderr)
                self.assertEqual(sum(x['command'] == 'spawn_tool' for x in c), 1)
                self.assertNotEqual(f.get('state/state', '').strip(), 'READY')

    def test_unreadable_identity_does_not_count_as_exit_but_zombie_does(self):
        p, c, f = self.run_case({'stat_missing_after_sleep': True})
        self.assertEqual(p.returncode, 2, p.stderr)
        self.assertIn('identity_unreadable_no_relaunch', f['state/events.log'])
        self.assertEqual(sum(x['command'] == 'spawn_tool' for x in c), 1)
        p, c, f = self.run_case({'zombie_every_sleep': True}, polls=20)
        self.assertEqual(p.returncode, 4, p.stderr)
        self.assertEqual(sum(x['command'] == 'spawn_tool' for x in c), 3)

    def test_boot_and_data_root_mismatch_refuse_before_effects(self):
        p, c, f = self.run_case(env_extra={'TT_EXPECT_BOOT': 'wrong-boot'})
        self.assertEqual(p.returncode, 2)
        self.assertIn('BOOT_MISMATCH', p.stderr)
        self.assertTrue(all(x['command'] == 'cat' for x in c), c)
        p, c, f = self.run_case(env_extra={'TT_STATE_ROOT': '$RUNTIME/app-data'})
        self.assertEqual(p.returncode, 2)
        self.assertIn('STATE_ROOT_OVERLAPS_USER_DATA', p.stderr)
        self.assertTrue(all(x['command'] == 'cat' for x in c), c)
        p, c, f = self.run_case({'state_alias': True})
        self.assertEqual(p.returncode, 2)
        self.assertIn('STATE_ROOT_OVERLAPS_USER_DATA', p.stderr)
        self.assertTrue(all(x['command'] == 'cat' for x in c), c)

    def test_pid_reuse_refuses_instead_of_signal_or_relaunch(self):
        p, c, f = self.run_case({'recycle_after_sleep': True})
        self.assertEqual(p.returncode, 2, p.stderr)
        self.assertIn('child_identity_changed_no_signal', f['state/events.log'])
        self.assertEqual(sum(x['command'] == 'spawn_tool' for x in c), 1)

    def test_uid_exe_sha_root_namespace_fail_closed(self):
        for model in [{'uid': '0', 'exe': '/system/bin/appspawn-x'}, {'uid': '20010053'}, {'sha': '0' * 64}, {'inode': '9:9'}, {'namespace': 'global'}]:
            with self.subTest(model=model):
                p, c, f = self.run_case(model)
                self.assertEqual(p.returncode, 2, p.stderr)
                self.assertEqual(f['state/state'].strip(), 'OWNER_REFUSED')

    def test_ownerless_live_and_stale_locks_never_reclaimed(self):
        for owner in ['ownerless', '123 456 fixture-boot\n', '777 999 old-boot\n']:
            with self.subTest(owner=owner):
                p, c, f = self.run_case(lock=owner)
                self.assertEqual(p.returncode, 2)
                self.assertIn('LOCK_CONFLICT_NO_TAKEOVER', p.stderr)
                self.assertFalse(any(x['command'] == 'parent_tool' for x in c))

    def test_stop_and_no_arm_refuse_before_launch_and_keep_marker(self):
        p, c, f = self.run_case(stop=True)
        self.assertEqual(p.returncode, 2)
        self.assertEqual(f['state/stop'], 'original operator stop')
        self.assertTrue(all(x['command'] == 'cat' for x in c), c)
        p, c, f = self.run_case(execute=False)
        self.assertEqual(p.returncode, 2)
        self.assertFalse(c)

    def test_new_stop_ends_observation_without_clearing_it(self):
        p, c, f = self.run_case({'stop_after_sleep': True})
        self.assertEqual(p.returncode, 0)
        self.assertEqual(f['state/stop'], 'operator marker')
        self.assertIn('existing_stop', f['state/events.log'])

if __name__ == '__main__':
    unittest.main(verbosity=2)
