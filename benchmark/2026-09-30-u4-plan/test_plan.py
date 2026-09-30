import copy
import importlib.util
import json
import os
import subprocess
import tempfile
import unittest
from pathlib import Path

import plan


spec = importlib.util.spec_from_file_location('probe_run', plan.HERE / 'probes/run.py')
probe_run = importlib.util.module_from_spec(spec); spec.loader.exec_module(probe_run)


class Predictions(unittest.TestCase):
    def test_coverage_and_protections(self):
        rows = plan.predictions()
        self.assertEqual(len(rows), 66)
        self.assertEqual(len({r['key'] for r in rows}), 66)
        self.assertEqual(sum(r['baseline_lit'] for r in rows), 25)
        self.assertEqual({r['key'] for r in rows if r['apk_changed']}, {'subwaysurfers'})
        self.assertTrue(all(r['predicted_new_light'] is None for r in rows))
        self.assertEqual(plan.read(plan.HERE / 'predictions.json'), rows)

    def test_not_all_cluster_proposals_are_built(self):
        rows = {r['key']: r for r in plan.predictions()}
        for key in ['fd-reader', 'fd-musicplayer', 'fd-client', 'fd-api', 'wikipedia', 'x', 'fd-gallery', 'fd-feeder', 'fd-plus']:
            self.assertEqual(rows[key]['prediction'], '不变')
        self.assertTrue(rows['newpipe']['baseline_lit'])
        self.assertEqual(rows['noice']['prediction'], '解锁')
        self.assertEqual(rows['fd-noice']['prediction'], '不变')
        self.assertEqual(rows['fd-tutanota']['prediction'], '不变')

    def test_sources_and_shards(self):
        for entry in plan.read(plan.HERE / 'sources.json'):
            self.assertEqual(plan.sha(plan.HERE / entry['snapshot']), entry['sha256'])
        old = plan.read(plan.HERE / 'inputs/shards.json')
        current = plan.read(plan.HERE / 'shards.json')
        self.assertEqual(current['shards'], old['shards'])
        self.assertEqual([len(s['keys']) for s in current['shards']], [17, 17, 16, 16])
        self.assertIsNone(current['shards'][-1]['serial'])


class Commands(unittest.TestCase):
    def setUp(self):
        self.t = tempfile.TemporaryDirectory(); self.addCleanup(self.t.cleanup)
        self.j5 = Path(self.t.name) / 'test J5.jar'; self.j5.write_bytes(b'fake only')
        self.p = plan.read(plan.HERE / 'shards.json')
        self.boards = {s['serial']: s['name'] for s in self.p['shards'] if s['serial']}
        self.fake_serial = 'aaaaaaaa000000000000000000000001'

    def render(self):
        return plan.commands(self.p, self.j5, plan.sha(self.j5), plan.HERE / 'cohort.json', self.boards, Path(self.t.name), 'test')

    def test_missing_fourth(self):
        with self.assertRaisesRegex(ValueError, 'registered OH'):
            self.render()

    def test_complete_renders_only_master(self):
        self.p['shards'][-1]['serial'] = self.fake_serial
        self.boards[self.fake_serial] = 'fake-oh-test-only'
        data = self.render()
        self.assertFalse(data['device_io'])
        self.assertEqual(len(data['commands']), 4)
        for row in data['commands']:
            args = row['vm_argv']
            self.assertIn('westlake-harness/benchmark/', args[1])
            self.assertIn('--reinstall', args)
            self.assertIn('--focus-check', args)
            self.assertIn(row['serial'], args[args.index('--run-id') + 1])

    def test_duplicate_keys_and_bad_sha(self):
        self.p['shards'][-1]['serial'] = self.fake_serial
        self.boards[self.fake_serial] = 'fake'
        self.p['shards'][0]['keys'][0] = self.p['shards'][1]['keys'][0]
        with self.assertRaisesRegex(ValueError, 'disjoint'):
            self.render()
        with self.assertRaisesRegex(ValueError, 'J5'):
            plan.commands(self.p, self.j5, '0'*64, plan.HERE / 'cohort.json', self.boards, Path(self.t.name), 'test')

    def test_known_unpaired_j5_rejected(self):
        with self.assertRaisesRegex(ValueError, 'cross-layer contract unresolved'):
            plan.commands(self.p, self.j5, 'dbce2eeada1d40d34d7904936bc09860d6ad30009781444ecd73661ad7e7e223',
                          plan.HERE / 'cohort.json', self.boards, Path(self.t.name), 'test')


class FakeBoard:
    def __init__(self, mode='ok'):
        self.mode = mode; self.boot = 'same-boot'; self.layers = ['10 9 0:1 /j3 ' + probe_run.TARGET + ' rw - none x rw']
        self.hashes = {probe_run.TARGET: 'base', '/proc/42/root' + probe_run.TARGET: 'base'}
        self.calls = []

    def ready(self):
        pass

    def send(self, local, remote):
        self.hashes[remote] = 'candidate'

    def shell(self, cmd):
        self.calls.append(cmd)
        if cmd == 'cat /proc/self/mountinfo': return 0, '\n'.join(self.layers)
        if cmd.startswith('sha256sum '): return 0, self.hashes[cmd.split()[1]] + ' file'
        if cmd.startswith('mount --bind '):
            remote = cmd.split()[2]
            self.layers.append('11 9 0:1 ' + remote.removeprefix('/data') + ' ' + probe_run.TARGET + ' rw - none x rw')
            self.hashes[probe_run.TARGET] = 'candidate'
            if self.mode != 'root-diverged': self.hashes['/proc/42/root' + probe_run.TARGET] = 'candidate'
            if self.mode == 'ambiguous': raise RuntimeError('transport failed after mount')
        if cmd.startswith('umount '):
            self.layers.pop()
            self.hashes[probe_run.TARGET] = self.hashes['/proc/42/root' + probe_run.TARGET] = 'base'
        return 0, ''


class Experiments(unittest.TestCase):
    def test_success_and_app_failure_restore(self):
        for fail in [False, True]:
            b = FakeBoard(); receipt = {}
            def batch():
                if fail: raise RuntimeError('app failed')
            if fail:
                with self.assertRaisesRegex(RuntimeError, 'app failed'):
                    probe_run.overlay(b, Path('fake'), 'candidate', 'base', '42', receipt, batch)
            else:
                probe_run.overlay(b, Path('fake'), 'candidate', 'base', '42', receipt, batch)
            self.assertEqual(receipt['rollback'], 'verified')
            self.assertEqual(len(b.layers), 1)

    def test_failed_root_and_ambiguous_mount_restore(self):
        for mode in ['root-diverged', 'ambiguous']:
            b = FakeBoard(mode); r = {}
            with self.assertRaises(RuntimeError):
                probe_run.overlay(b, Path('fake'), 'candidate', 'base', '42', r, lambda: self.fail('must not launch'))
            self.assertEqual(r['rollback'], 'verified')

    def test_competing_mount_is_never_removed(self):
        b = FakeBoard(); r = {}
        def changed():
            b.layers.append('12 9 0:1 /other ' + probe_run.TARGET + ' rw - none x rw')
        with self.assertRaisesRegex(RuntimeError, 'top mount changed'):
            probe_run.overlay(b, Path('fake'), 'candidate', 'base', '42', r, changed)
        self.assertEqual(r['rollback'], 'unverified')
        self.assertFalse(any(c.startswith('umount ') for c in b.calls))

    def test_probe_artifacts_and_only_helper_ab_delta(self):
        receipt = plan.read(plan.HERE / 'probes/build-receipt.json')
        base = plan.ROOT / 'bms/src/.work/u4-probes'
        for name, row in receipt['variants'].items():
            self.assertEqual(plan.sha(base / name / 'oh-adapter-runtime.jar'), row['sha256'])
            self.assertEqual(row['changed_existing_classes'], ['adapter/activity/AppSchedulerBridge.smali'])
        a = base / 'A-observe/post'; b = base / 'B-app-theme/post'
        changed = [str(p.relative_to(a)) for p in a.rglob('*.smali') if p.read_bytes() != (b / p.relative_to(a)).read_bytes()]
        self.assertEqual(changed, ['adapter/diagnostics/U4Probe.smali'])

    def test_real_jvm_forwarding_and_theme_intervention(self):
        jdk = Path(os.environ.get('U4_TEST_JDK', '/opt/homebrew/opt/openjdk@17/libexec/openjdk.jdk/Contents/Home'))
        with tempfile.TemporaryDirectory() as td:
            d = Path(td); (d / 'android/app').mkdir(parents=True)
            (d/'android/app/IActivityClientController.java').write_text('''package android.app;
public interface IActivityClientController { boolean finishActivity(Object t,int c,Object d,int f); Object asBinder(); void fail(); }''')
            (d/'Main.java').write_text('''import adapter.diagnostics.U4Probe; import android.app.IActivityClientController;
public class Main {
 public static class Info { public String packageName; public int theme=0x7f1402f9; }
 public static class Controller implements IActivityClientController {
  public int calls; public final Object binder=new Object(); public final RuntimeException error=new RuntimeException("original");
  public boolean finishActivity(Object t,int c,Object d,int f) { calls++; if(c!=7||f!=3)throw new AssertionError(); return false; }
  public Object asBinder(){return binder;} public void fail(){throw error;}
 }
 public static void main(String[] args) {
  Info ai=new Info();ai.packageName="other";U4Probe.beforeBind(ai);Controller d=new Controller();
  if(U4Probe.controller(d)!=d)throw new AssertionError("non-target changed");
  ai.packageName="org.videolan.vlc";U4Probe.beforeBind(ai);
  if(ai.theme!=Integer.decode(args[0]))throw new AssertionError("theme");
  ai.packageName="com.termux";U4Probe.beforeBind(ai);
  IActivityClientController p=(IActivityClientController)U4Probe.controller(d);
  if(p==d||p.asBinder()!=d.binder||p.finishActivity(new Object(),7,null,3)||d.calls!=1)throw new AssertionError("forward");
  try {p.fail();throw new AssertionError("swallowed");}catch(RuntimeException e){if(e!=d.error)throw new AssertionError("wrapped");}
  System.out.println("PASS forwarding, exception identity, non-target, theme");
 }
}''')
            source = (plan.HERE / 'probes/U4Probe.java').read_text()
            for change in [False, True]:
                out = d / ('b' if change else 'a'); out.mkdir()
                helper = d / 'U4Probe.java'
                helper.write_text(source.replace('CHANGE_APP_THEME = false;', 'CHANGE_APP_THEME = true;') if change else source)
                subprocess.run([str(jdk/'bin/javac'), '--release', '8', '-d', str(out), str(helper), str(d/'Main.java'), str(d/'android/app/IActivityClientController.java')], check=True, capture_output=True)
                p = subprocess.run([str(jdk/'bin/java'), '-cp', str(out), 'Main', '0x7f1402ec' if change else '0x7f1402f9'], check=True, text=True, capture_output=True)
                self.assertIn('[U4-TERMUX-FINISH]', p.stderr)
                self.assertIn('Main.main', p.stderr)
                self.assertIn('PASS forwarding', p.stdout)


if __name__ == '__main__':
    unittest.main()
