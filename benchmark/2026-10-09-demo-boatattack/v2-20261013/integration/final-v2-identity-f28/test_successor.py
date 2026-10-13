"""Offline tests. Synthetic indexes/transport never authorize an actual round."""
import ast
import contextlib
import copy
import hashlib
import io
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch
import prepare_identity as p

HERE = Path(__file__).resolve().parent
OLD = HERE / 'evidence/original'
PREVIEW = HERE / 'preview-final-5cd'

def save(path, doc):
    path.write_text(json.dumps(doc, indent=2) + '\n')

def functions(path):
    return {node.name: node for node in ast.parse(path.read_text()).body
            if isinstance(node, ast.FunctionDef)}

def normalize(node):
    node = copy.deepcopy(node)
    # Diagnostic scope wording changes; predicates/AST remain intact.
    class Scope(ast.NodeTransformer):
        def visit_Constant(self, n):
            if isinstance(n.value, str):
                n.value = n.value.replace('61b', 'same-board')
            return n
    return ast.dump(Scope().visit(node))

class IdentityTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tmp = tempfile.TemporaryDirectory(dir=HERE / 'tmp')
        cls.preview = Path(cls.tmp.name) / 'actual-disabled'
        composition = p.MAIN / 'benchmark/2026-10-09-demo-boatattack/v2-20261013/outer/final-v2-f28-main/composed/composition.json'
        with patch('subprocess.run', side_effect=AssertionError('ZERO TRANSPORT')):
            p.build(composition, '70016aeb02fea955095593b0472d786a607cdd2a6ccf518ca0956cbc38754bf7', cls.preview)

    @classmethod
    def tearDownClass(cls):
        cls.tmp.cleanup()

    def test_real_main_preview_has_complete_exact_union(self):
        c = p.load(HERE.parent / 'final-v2-identity-f28-5cd/candidate_identity.py', 'f28_test_actual')
        proof = c.read(self.preview / 'identity/candidate-proof.json')
        with patch('subprocess.run', side_effect=AssertionError('ZERO TRANSPORT')):
            self.assertEqual(len(c.validate(proof)), 954)
        planned = c.read(c.pinned(proof['planned_selfcheck']))
        self.assertEqual(proof['expected'], planned['all_expected_sha256'])
        self.assertEqual((len(proof['presence_metadata']), len(proof['directory_metadata'])), (507, 5))
        self.assertEqual(proof['expected'][c.RUNTIME], c.F28)
        self.assertEqual(proof['boat_uid'], 20011301)
        self.assertFalse(proof['synthetic']); self.assertFalse(proof['execution_enabled'])
        self.assertEqual(proof['absent_files'], [])
        self.assertEqual(len(proof['replacements']), 4)
        base = c.read(c.BASE)['expected']
        self.assertEqual(sum(proof['expected'][t] == h for t, h in base.items()), 315)
        self.assertEqual(proof['base_source']['kind'], 'activation')
        self.assertIn('$WORKSPACES/westlake-harness/', proof['placement_plan']['path'])
        result = c.read(self.preview / 'result.json')
        self.assertEqual(result['round_status'], 'PENDING_SAME_BOARD_INSTALLED_RECORDS_AND_REBOOT_ORIGIN')
        self.assertFalse((self.preview / 'round').exists())
        self.assertNotIn('user unseal', result['pending'])

    def test_original_check_reader_metadata_parser_are_preserved(self):
        old = functions(OLD / 'candidate_identity.py')
        for board in ('61b', '5cd'):
            sibling = HERE.parent / ('final-v2-identity-f28-' + board)
            new = functions(sibling / 'candidate_identity.py')
            for name in ('check', 'parse_hashes', 'validate_round_inputs', 'validate_round_bindings'):
                self.assertEqual(normalize(old[name]), normalize(new[name]), (board, name))
            self.assertEqual(hashlib.sha256((sibling / 'presence_reader.py').read_bytes()).hexdigest(),
                             '7059cc45215f3f260402763fb6e8ac24994a3913614d6c6d635335f61df898f6')

    def test_actual_cli_wrong_pin_pending_and_940_input_reject(self):
        with tempfile.TemporaryDirectory(dir=HERE / 'tmp') as directory:
            root = Path(directory)
            composition = p.MAIN / 'benchmark/2026-10-09-demo-boatattack/v2-20261013/outer/final-v2-f28-main/composed/composition.json'
            result = subprocess.run([sys.executable, str(HERE / 'prepare_identity.py'),
                '--composition', str(composition), '--composition-sha256', '0'*64,
                '--out', str(root / 'wrong-pin')], capture_output=True, text=True)
            self.assertEqual(result.returncode, 2); self.assertIn('full SHA differs', result.stderr)
            self.assertFalse((root / 'wrong-pin').exists())
            for board in ('61b', '5cd'):
                sibling = HERE.parent / ('final-v2-identity-f28-' + board)
                result = subprocess.run([sys.executable, str(sibling / 'compile_candidate.py'),
                    '--request', str(sibling / 'request.pending.json'), '--out', str(root / board)],
                    capture_output=True, text=True)
                self.assertNotEqual(result.returncode, 0)
                self.assertIn('pending actual', result.stderr); self.assertFalse((root / board).exists())
            old940 = p.MAIN / 'benchmark/2026-10-09-demo-boatattack/v2-20261013/outer/r5-experiment-main-r4/run/restored-r5.json'
            result = subprocess.run([sys.executable, str(HERE / 'prepare_identity.py'),
                '--composition', str(old940), '--composition-sha256', hashlib.sha256(old940.read_bytes()).hexdigest(),
                '--out', str(root / 'old940')], capture_output=True, text=True)
            self.assertEqual(result.returncode, 2); self.assertFalse((root / 'old940').exists())

class DriverTests(unittest.TestCase):
    def test_original_driver_all_function_bodies_unchanged(self):
        old = functions(OLD / 'run_candidate_post_reboot.py')
        for board in ('61b', '5cd'):
            new = functions(HERE.parent / ('final-v2-identity-f28-' + board) / 'run_candidate_post_reboot.py')
            self.assertEqual(set(old), set(new))
            for name in old:
                self.assertEqual(ast.dump(old[name]), ast.dump(new[name]), (board, name))

    def test_synthetic_full128_eight_windows_and_real_index_rejection(self):
        c = p.load(HERE.parent / 'final-v2-identity-f28-5cd/candidate_identity.py', 'f28_test_driver_gate')
        proof = c.read(PREVIEW / 'identity/candidate-proof.json')
        # Relocated evidence keeps author paths; this synthetic planning fixture
        # explicitly binds its local copied smoke. It is never serialized as admission.
        proof['smoke'] = c.pin(PREVIEW / 'identity/smoke.json')
        with p.local_import(c):
            driver = p.load(HERE.parent / 'final-v2-identity-f28-5cd/run_candidate_post_reboot.py', 'f28_test_driver')
        with tempfile.TemporaryDirectory(dir=HERE / 'tmp') as directory:
            root = Path(directory); index = {}
            for app in c.read(c.MANIFEST)['apps']:
                if app.get('install') is False: continue
                record = root / (app['key'] + '.json')
                save(record, dict(synthetic=True, serial=c.SERIAL, key=app['key'], package=app['package'],
                    apk_sha256=app['apk_sha256'], install=dict(return_code=0, success_text=True)))
                index[app['key']] = dict(serial=c.SERIAL, success=True, apk_sha256=app['apk_sha256'],
                    record=c.pin(record)['path'], record_sha256=c.sha(record))
            indexpath = root / 'synthetic-index.json'; save(indexpath, index)
            with self.assertRaisesRegex(ValueError, 'synthetic record'):
                c.validate_round_inputs(proof, c.MANIFEST, c.TIERS, indexpath)
            with self.assertRaises(ValueError):
                c.validate_round_inputs(proof, c.MANIFEST, c.TIERS, driver.BASE / 't3/install-index-final.json')
            fixture = copy.deepcopy(proof); fixture['synthetic'] = True
            # Only load_proof is replaced for this explicit synthetic planning fixture.
            # All original per-record/tier/member guards below still run unchanged.
            with patch.object(c, 'load_proof', return_value=fixture), patch.object(sys, 'platform', 'darwin'), \
                 patch('subprocess.run', side_effect=AssertionError('ZERO TRANSPORT')), \
                 contextlib.redirect_stdout(io.StringIO()):
                driver.prepare(c.MANIFEST, c.TIERS, indexpath, root / 'round',
                    '00000000-0000-0000-0000-000000000001', PREVIEW / 'identity/smoke.json',
                    serial=c.SERIAL, candidate_proof=PREVIEW / 'identity/candidate-proof.json',
                    candidate_sha=c.sha(PREVIEW / 'identity/candidate-proof.json'))
                config = c.read(root / 'round/round.json')
                self.assertEqual((config['apps'], len(config['windows'])), (128, 8))
                self.assertFalse(config['execution_enabled'])
                for ref in config['windows']:
                    plan = c.read(driver.expand(ref)); self.assertFalse(plan['execution_enabled'])
                    for hook in ('after_lock', 'before_unlock'):
                        self.assertEqual(plan[hook][:4], ['orb', '-m', 'a2hlab', 'env'])
                with self.assertRaisesRegex(ValueError, 'synthetic'):
                    driver.execute(root / 'round', 'HOST TEST ONLY')
            tiers = c.read(c.TIERS)['apps']
            self.assertEqual((sum(x['screenshot_seconds']==10 for x in tiers),
                              sum(x['screenshot_seconds']==20 for x in tiers)), (121, 7))
            original = copy.deepcopy(index)
            for fault in ('serial', 'missing', 'sha', 'success', 'record-pin'):
                changed = copy.deepcopy(original); key = next(iter(changed))
                if fault == 'serial': changed[key]['serial'] = '61b0657200000000000000000324012c'
                elif fault == 'missing': changed.pop(key)
                elif fault == 'sha': changed[key]['apk_sha256'] = '0'*64
                elif fault == 'success': changed[key]['success'] = False
                else: changed[key]['record_sha256'] = '0'*64
                save(indexpath, changed)
                with self.assertRaises(ValueError):
                    c.validate_round_inputs(fixture, c.MANIFEST, c.TIERS, indexpath)

if __name__ == '__main__':
    (HERE / 'tmp').mkdir(exist_ok=True)
    unittest.main(verbosity=2)
