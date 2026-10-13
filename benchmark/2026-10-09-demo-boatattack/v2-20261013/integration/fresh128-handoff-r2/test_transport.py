#!/usr/bin/env python3
"""Offline real-input driver tests. All subprocesses are intercepted; no board/VM calls."""
import ast
import contextlib
import hashlib
import importlib.util
import io
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

HERE = Path(__file__).resolve().parent
ROOT = next(p for p in HERE.parents if (p / 'scripts/lab/lab_paths.py').is_file())
os.environ.setdefault('WORKSPACES', str(ROOT.parent))
sys.dont_write_bytecode = True
spec = importlib.util.spec_from_file_location('transport_driver', HERE / 'run_candidate_post_reboot.py')
d = importlib.util.module_from_spec(spec)
spec.loader.exec_module(d)
COMPILED = d.MASTER / 'benchmark/2026-10-09-demo-boatattack/v2-20261013/outer/identity-table-correction/compiled'
PROOF_SHA = 'd8f13bf33e431bc8821e4e29c573161c41d1527e276828b8e725efad3e959b22'
SERIAL = '5ea34a4500000000000000001123012c'
ORIGINAL_SHA = '4d8f3f6443828db2cc8fb044291bdecaa5bea3c4e9b5d37cdf10f44f9a272a60'


class DriverTransport(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix='fresh128-transport-')
        self.addCleanup(self.temp.cleanup)
        self.out = Path(self.temp.name) / 'round'
        self.calls = []
        self.boards = 0
        self.failure = None
        self.addCleanup(patch.stopall)
        patch.object(sys, 'platform', 'darwin').start()
        patch.object(subprocess, 'run', side_effect=self.fake_run).start()
        patch.object(subprocess, 'check_output', side_effect=self.fake_facts).start()
        patch.object(subprocess, 'Popen', side_effect=AssertionError('unexpected Popen')).start()
        with contextlib.redirect_stdout(io.StringIO()):
            self.config = d.prepare(d.BASE / 'demo-manifest.json', d.HERE / 'shot-tiers.json',
                d.BASE / 't3/install-index-final.json', self.out,
                'd0e1f5eb-ac35-4c39-9e1a-7c40d9251220', COMPILED / 'smoke.json',
                serial=SERIAL, candidate_proof=COMPILED / 'candidate-proof.json', candidate_sha=PROOF_SHA)

    def fake_facts(self, argv, **kwargs):
        self.assertEqual(argv[1], str(d.MASTER / 'scripts/lab/run_facts.py'))
        return 'SYNTHETIC_RECORDING_ONLY: no screenshots or device evidence\n'

    def fake_run(self, argv, **kwargs):
        argv = list(map(str, argv))
        self.calls.append(argv)
        if '--resolve-inputs' in argv:
            rc = 9 if self.failure == 'resolve' else 0
        elif argv == ['orb', '-m', 'a2hlab', 'true'] or argv == ['hdc', 'list', 'targets']:
            rc = 0
        elif str(d.CANDIDATE_HOOK) in argv:
            self.assertEqual(argv[:7], d.identity_python())
            self.assertEqual(argv[6], 'python3')
            self.assertNotIn(sys.executable, argv[:7])
            rc = 7 if self.failure == 'identity' else 0
        elif argv[0].endswith('/board_note.sh'):
            rc = 0
        elif len(argv) > 1 and argv[1] == str(d.BASE / 't3/demo_board_run.py'):
            self.assertEqual(argv[0], sys.executable)
            self.boards += 1
            planpath = Path(argv[2])
            plan = d.read(planpath)
            self.assertTrue(plan['execution_enabled'])
            self.assertEqual((plan['window_limit_minutes'], plan['stop_new_tests_by_minute']), (45, 35))
            for hook in ('after_lock', 'before_unlock'):
                self.assertEqual(plan[hook][:7], d.identity_python())
                self.assertEqual(plan[hook][7], d.portable(d.CANDIDATE_HOOK))
            runner = planpath.parent / 'runner'
            runner.mkdir()
            d.save(runner / 'board-run-result.json', {
                'smoke': 3 if self.failure == 'smoke' else 0,
                'before_unlock': 4 if self.failure == 'unlock' else 0})
            skipped = False
            for shard in plan['shards']:
                for key in d.expand(shard['keys_file']).read_text().split():
                    if self.failure == 'missing' and not skipped:
                        skipped = True
                        continue
                    folder = runner / shard['name'] / SERIAL / key
                    folder.mkdir(parents=True)
                    d.save(folder / 'record.json', {'key': key, 'synthetic': True, 'captured': []})
            rc = 0
        else:
            raise AssertionError('unmocked external call: ' + repr(argv))
        if rc and kwargs.get('check'):
            raise subprocess.CalledProcessError(rc, argv)
        return subprocess.CompletedProcess(argv, rc)

    def execute(self, authorization='SYNTHETIC_TEST_REFERENCE'):
        with contextlib.redirect_stdout(io.StringIO()):
            d.execute(self.out, authorization)

    def test_complete_driver_128_eight_windows_real_inputs_fake_transport(self):
        self.assertEqual(len(self.config['windows']), 8)
        self.assertFalse(self.config['execution_enabled'])
        self.assertEqual(self.config['bindings']['hdc_shim'], d.pin(d.MAC_HDC_SHIM))
        self.execute()
        self.assertEqual(self.boards, 8)
        self.assertTrue(any('--resolve-inputs' in x for x in self.calls))
        self.assertEqual(sum(str(d.CANDIDATE_HOOK) in x for x in self.calls), 8)
        self.assertEqual(len(d.regress.records(self.out / 'final')), 128)
        self.assertEqual(d.read(self.out / 'round-complete.json'),
                         {'recorded_keys': 128, 'UI_verdict': 'pending_outer_review'})

    def test_prelock_identity_failure_stops_before_board_run(self):
        self.failure = 'identity'
        with self.assertRaises(subprocess.CalledProcessError): self.execute()
        self.assertEqual(self.boards, 0)
        self.assertFalse(d.read(d.expand(self.config['windows'][0]))['execution_enabled'])

    def test_input_resolution_failure_stops_before_identity_and_lock(self):
        self.failure = 'resolve'
        with self.assertRaisesRegex(RuntimeError, 'resolution failed'): self.execute()
        self.assertEqual(self.boards, 0)
        self.assertFalse(any(str(d.CANDIDATE_HOOK) in x for x in self.calls))

    def test_missing_record_stops_after_first_window_collects_partial(self):
        self.failure = 'missing'
        with self.assertRaisesRegex(RuntimeError, 'missing key'): self.execute()
        self.assertEqual(self.boards, 1)
        self.assertEqual(len(d.regress.records(self.out / 'final')), 17)
        self.assertFalse((self.out / 'round-complete.json').exists())

    def test_smoke_failure_stops_after_first_window(self):
        self.failure = 'smoke'
        with self.assertRaisesRegex(RuntimeError, 'window failed'): self.execute()
        self.assertEqual(self.boards, 1)
        self.assertFalse((self.out / 'round-complete.json').exists())

    def test_final_identity_failure_stops_after_first_window(self):
        self.failure = 'unlock'
        with self.assertRaisesRegex(RuntimeError, 'window failed'): self.execute()
        self.assertEqual(self.boards, 1)
        self.assertFalse((self.out / 'round-complete.json').exists())

    def test_binding_drift_before_any_external_call(self):
        with (self.out / 'shot-tiers.json').open('a') as f: f.write(' ')
        with self.assertRaisesRegex(ValueError, 'pinned driver/input'): self.execute()
        self.assertEqual(self.calls, [])

    def test_window_drift_before_any_external_call(self):
        with d.expand(self.config['windows'][0]).open('a') as f: f.write(' ')
        with self.assertRaisesRegex(ValueError, 'window plan drift'): self.execute()
        self.assertEqual(self.calls, [])

    def test_127_members_refused_before_any_external_call(self):
        apps = d.read(self.out / 'batch-apps.json')
        apps['apps'].pop()
        d.save(self.out / 'batch-apps.json', apps)
        with self.assertRaisesRegex(ValueError, 'membership lost'): self.execute()
        self.assertEqual(self.calls, [])

    def test_authorization_required_before_any_external_call(self):
        with self.assertRaisesRegex(ValueError, 'authorization'): self.execute(' ')
        self.assertEqual(self.calls, [])

    def test_special_slots_unchanged_and_reject_unbound_boat(self):
        self.config['special_slots']['boatattack']['enabled'] = True
        d.save(self.out / 'round.json', self.config)
        with self.assertRaisesRegex(ValueError, 'approved bound plan'): self.execute()
        self.assertEqual(self.calls, [])

    def test_special_slots_reject_toutiao_on_5ea(self):
        self.config['special_slots']['toutiao']['enabled'] = True
        d.save(self.out / 'round.json', self.config)
        with self.assertRaisesRegex(ValueError, '61b only'): self.execute()
        self.assertEqual(self.calls, [])

    def test_main_dispatch_preserves_mac_and_native_shim(self):
        def dispatched(out, authorization):
            self.assertEqual(out, self.out.resolve())
            self.assertEqual(authorization, 'fake-reference')
            self.assertEqual(os.environ['PATH'].split(os.pathsep)[0], str(d.MAC_HDC_SHIM.parent))
            self.assertEqual(os.environ['MAC_HOME'], str(Path.home()))
        with patch.dict(os.environ), patch.object(d, 'execute', side_effect=dispatched) as run:
            with patch.object(sys, 'argv', ['driver', '--out', str(self.out), '--execute',
                                         '--serial', SERIAL, '--authorization', 'fake-reference']):
                self.assertEqual(d.main(), 0)
            run.assert_called_once()
        self.assertEqual(self.calls, [])

    def test_original_core_functions_unchanged(self):
        original = (d.LOCAL / 'run_candidate_post_reboot.py').read_bytes()
        self.assertEqual(hashlib.sha256(original).hexdigest(), ORIGINAL_SHA)
        old = {n.name: ast.dump(n) for n in ast.parse(original).body if isinstance(n, ast.FunctionDef)}
        new = {n.name: ast.dump(n) for n in ast.parse((HERE / 'run_candidate_post_reboot.py').read_bytes()).body if isinstance(n, ast.FunctionDef)}
        for name in ('resolve_inputs', 'collect', 'validate_special_slots', 'validate_serial'):
            self.assertEqual(new[name], old[name], name)


if __name__ == '__main__':
    unittest.main(verbosity=2)
