import argparse
import hashlib
import importlib.util
import json
from pathlib import Path
import subprocess
import time
import unittest


class IndependentReadinessTests(unittest.TestCase):
    candidate = None
    snapshot = None

    def check_rejected(self, model, field):
        result, rows, elapsed = self.candidate.run_case(model)
        self.assertNotEqual(result.returncode, 0, result.stderr)
        self.assertFalse(any(row['actual'] == 'ready' for row in rows), rows)
        self.assertTrue(any(row['field'] == field for row in rows), rows)
        return elapsed

    def test_root_parent_ready_child(self):
        result, rows, _ = self.candidate.run_case({})
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(rows[-1]['actual'], 'ready')

    def test_root_to_owner_transition(self):
        result, rows, _ = self.candidate.run_case({'uid': '0', 'transition': True})
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertTrue(any(row['actual'] == '0:0:0:0' for row in rows))
        self.assertEqual(rows[-1]['actual'], 'ready')

    def test_root_timeout(self):
        elapsed = self.check_rejected({'uid': '0'}, 'uid')
        self.assertLess(elapsed, 2.5)

    def test_foreign_uid(self):
        self.check_rejected({'uid': '20011300'}, 'uid')

    def test_root_wrong_non_uid_identity(self):
        cases = [({'sha': '0' * 64}, 'exe_sha'),
                 ({'exe': '/system/bin/appspawn-x'}, 'exe'),
                 ({'ppid': 1}, 'ppid'), ({'global_ns': True}, 'namespace'),
                 ({'inode': '1:2'}, 'private_inode'), ({'birth': 777}, 'birth')]
        for model, field in cases:
            with self.subTest(field=field):
                elapsed = self.check_rejected(dict(model, uid='0'), field)
                self.assertLess(elapsed, 1)

    def test_read_exit_stop_boot(self):
        for model, field in [({'read_error': True}, 'uid'), ({'exited': True}, 'birth'),
                             ({'stop': True}, 'stop'), ({'boot': 'changed'}, 'boot')]:
            with self.subTest(field=field):
                self.check_rejected(model, field)

    def test_drift_during_root_wait(self):
        module = self.candidate
        original_thread = module.threading.Thread
        mutations = ['boot', 'birth', 'ppid', 'namespace', 'parent_birth', 'guardian_birth']
        for mutation in mutations:
            with self.subTest(mutation=mutation):
                def thread_factory(*args, **kwargs):
                    callback = kwargs['target']
                    closure = dict(zip(callback.__code__.co_freevars,
                                       (cell.cell_contents for cell in callback.__closure__)))
                    proc = closure['proc']

                    def mutate_then_transition():
                        time.sleep(.06)
                        if mutation == 'boot':
                            (proc / 'sys/kernel/random/boot_id').write_text('changed')
                        elif mutation == 'namespace':
                            link = proc / '9544/ns/mnt'
                            link.unlink()
                            link.symlink_to('mnt:[4026531841]')
                        else:
                            pid = {'parent_birth': 4421, 'guardian_birth': 9000}.get(mutation, 9544)
                            ppid = 1 if mutation == 'ppid' or pid != 9544 else 4421
                            birth = 999 if mutation != 'ppid' else 63926
                            (proc / str(pid) / 'stat').write_text(module.statline(pid, ppid, birth))
                        callback()

                    kwargs['target'] = mutate_then_transition
                    return original_thread(*args, **kwargs)

                module.threading.Thread = thread_factory
                try:
                    result, rows, _ = module.run_case({'uid': '0', 'transition': True})
                    self.assertNotEqual(result.returncode, 0, result.stderr)
                    self.assertFalse(any(row['actual'] == 'ready' for row in rows), rows)
                finally:
                    module.threading.Thread = original_thread

    def test_attach_has_no_root_exception(self):
        result, rows, elapsed = self.candidate.run_case({'uid': '0'}, strict=True)
        self.assertNotEqual(result.returncode, 0)
        self.assertEqual(rows[-1]['field'], 'uid')
        self.assertLess(elapsed, 1)

    def test_new_spawn_only_and_final_original_guard(self):
        source = (self.snapshot / 'candidate/watchdog.sh').read_text()
        branch = source[source.index('# Explicit attach'):source.index('attempt=$((attempt+1))')]
        self.assertEqual(branch.count('timeout 2 sh'), 1)
        self.assertLess(branch.index('else\n'), branch.index('timeout 2 sh'))
        self.assertLess(branch.index('timeout 2 sh'),
                        branch.index('child_owned "$child" "$child_birth" ||'))
        worker = (self.snapshot / 'candidate/readiness-probe.sh').read_text()
        for forbidden in ('kill ', 'pkill ', 'rm ', 'rmdir ', 'host_spawn ', 'spawn.sh'):
            self.assertNotIn(forbidden, worker)

    def test_publish_binding_closure(self):
        candidate = self.snapshot / 'candidate'

        def digest(path):
            return hashlib.sha256(path.read_bytes()).hexdigest()

        for name in ('watchdog.sh', 'route-b-owner.sh'):
            self.assertIn(digest(candidate / name), (candidate / 'entry.sh').read_text())
        mapping = {'start-parent.sh': 'start-parent-prepared.sh',
                   'spawn.sh': 'spawn-prepared.sh', 'screen-gate': 'screen-gate-feed'}
        original = self.snapshot.parent / '2026-10-12-recovery-executor/payload'
        for line in (candidate / 'members.tsv').read_text().splitlines():
            expected, name, _ = line.split()
            path = candidate / mapping.get(name, name)
            if not path.exists():
                path = original / mapping.get(name, name)
            self.assertEqual(digest(path), expected, name)
        self.assertIn(digest(candidate / 'members.tsv'), (candidate / 'startup.env').read_text())
        self.assertEqual(digest(candidate / 'startup.env'),
                         (candidate / 'startup.expected.sha256').read_text().strip())
        self.assertEqual(digest(original / 'watchdog.sh'),
                         '9763171a0b6dab1b23b72e454cb2c6256181298bc282e81b6ae8e38fa9577072')
        alias = self.snapshot.parent / '2026-10-12-recovery-exe-alias/candidate/watchdog.sh'
        self.assertEqual(digest(alias),
                         '9a54b2fc470a483e55caa93cfc952cc6e14d2530ed3ffaf6a758c21e08837ff2')


GROUPS = {
    'transition': ['test_root_parent_ready_child', 'test_root_to_owner_transition'],
    'reject': ['test_root_timeout', 'test_foreign_uid', 'test_root_wrong_non_uid_identity',
               'test_read_exit_stop_boot', 'test_drift_during_root_wait'],
    'bindings': ['test_attach_has_no_root_exception', 'test_new_spawn_only_and_final_original_guard',
                 'test_publish_binding_closure'],
}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--repository', type=Path, required=True)
    parser.add_argument('--commit', required=True)
    parser.add_argument('--snapshot', type=Path, required=True)
    parser.add_argument('--group', choices=list(GROUPS), required=True)
    args = parser.parse_args()
    prefix = 'benchmark/2026-10-12-child-readiness/'
    paths = subprocess.check_output(['git', '-C', str(args.repository), 'ls-tree', '-r',
                                     '--name-only', args.commit, '--', prefix], text=True).splitlines()
    if not paths:
        raise SystemExit('REFUSE: no child-readiness files in exact Git object')
    hashes = {}
    for relative in paths:
        original = subprocess.check_output(['git', '-C', str(args.repository), 'show',
                                            args.commit + ':' + relative])
        local = args.snapshot / relative
        if local.read_bytes() != original:
            raise SystemExit('REFUSE: snapshot differs from exact Git object: ' + relative)
        hashes[relative] = hashlib.sha256(original).hexdigest()
    path = args.snapshot / prefix / 'test_readiness.py'
    spec = importlib.util.spec_from_file_location('exact_frozen_readiness_fixture', path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    IndependentReadinessTests.candidate = module
    IndependentReadinessTests.snapshot = path.parent
    print(json.dumps({'commit': args.commit, 'group': args.group,
                      'source_hashes': hashes, 'board_calls': 0,
                      'fixture_scope': 'reuse frozen proc-field transport; independent assertions and timed mutations'}))
    suite = unittest.TestSuite(IndependentReadinessTests(name) for name in GROUPS[args.group])
    result = unittest.TextTestRunner(verbosity=2).run(suite)
    return 0 if result.wasSuccessful() else 1


if __name__ == '__main__':
    raise SystemExit(main())
