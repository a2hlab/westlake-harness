import copy
import importlib.util
from pathlib import Path
import unittest
import json
import tempfile
from unittest.mock import patch

H = Path(__file__).resolve().parent
spec = importlib.util.spec_from_file_location('promotion_hook', H / 'promotion_hook.py')
hook = importlib.util.module_from_spec(spec)
spec.loader.exec_module(hook)


class PromotionSafety(unittest.TestCase):
    def setUp(self):
        self.c = {'bundle_sha256': 'bundle', 'native_manifest_sha256': 'manifest'}
        self.base = {'keys': {str(i): {'verdict': 'lit' if i < 115 else 'dead'} for i in range(165)} | {'toutiao': {'verdict': 'dead'}}}
        self.good = {'signed_by': 'outer(claude)', **self.c, 'keys': copy.deepcopy(self.base['keys']), 'controls_t20_lit': ['helloworld', 'zigzag'], 'confirmed_regressions': []}
        self.good['keys']['toutiao']['verdict'] = 'lit'

    def reason(self, decision, smoke=None):
        return hook.retention_reason(decision, self.c, self.base, {'passed': True} if smoke is None else smoke)

    def test_full_outer_signed_no_regression_can_retain(self):
        self.assertIsNone(self.reason(self.good))

    def test_missing_or_wrong_identity_or_smoke_rolls_back(self):
        self.assertIsNotNone(self.reason(None))
        d = copy.deepcopy(self.good)
        d['bundle_sha256'] = 'other'
        self.assertIsNotNone(self.reason(d))
        self.assertIsNotNone(self.reason(self.good, {'passed': False}))

    def test_partial_unknown_and_inconclusive_never_promote(self):
        d = copy.deepcopy(self.good)
        del d['keys']['0']
        self.assertIsNotNone(self.reason(d))
        for value in ['unknown', 'inconclusive']:
            d = copy.deepcopy(self.good)
            d['keys']['165' if '165' in d['keys'] else '164']['verdict'] = value
            self.assertIsNotNone(self.reason(d))

    def test_u9_lit_and_toutiao_regressions_refuse(self):
        for key in ['0', 'toutiao']:
            d = copy.deepcopy(self.good)
            d['keys'][key]['verdict'] = 'alive-white-window'
            self.assertIsNotNone(self.reason(d))

    def test_unarmed_candidate_blocks_before_vm(self):
        with patch.object(hook.previous, 'vm') as vm:
            with self.assertRaisesRegex(AssertionError, 'outer package review pending'):
                hook.admission()
            vm.assert_not_called()

    def test_all_plans_refuse_before_infra_and_lock(self):
        spec = importlib.util.spec_from_file_location('dispatch', H / 'promotion_dispatch.py')
        dispatch = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(dispatch)
        with patch.object(dispatch.subprocess, 'run') as run:
            for short in ['5ea', '5cd', '61b']:
                plan = json.loads((H / 'window' / ('plan-' + short + '.json')).read_text())
                with self.assertRaisesRegex(RuntimeError, 'REVIEW-ONLY plan is not executable'):
                    dispatch.prelock(plan)
            run.assert_not_called()

    def test_full_shards_match_signed_u9_keys(self):
        base = json.loads((H.parents[1] / 'benchmark/2026-10-01-u9-sweep/outer-signoff.json').read_text())
        keys = []
        for short, lit_count in [('5ea', 37), ('5cd', 38), ('61b', 40)]:
            plan = json.loads((H / 'window' / ('plan-' + short + '.json')).read_text())
            board_keys = []
            for shard in plan['shards']:
                board_keys += (H / 'window' / Path(shard['keys_file']).name).read_text().split()
            self.assertEqual(sum(base['keys'][key]['verdict'] == 'lit' for key in board_keys), lit_count)
            ordinary = board_keys[1:] if short == '5ea' else board_keys
            self.assertTrue(all(base['keys'][key]['verdict'] == 'lit' for key in ordinary[:lit_count]))
            self.assertTrue(all(base['keys'][key]['verdict'] != 'lit' for key in ordinary[lit_count:]))
            self.assertIn('--finish-observation', plan['before_unlock'])
            self.assertNotIn('--decision', plan['before_unlock'])
            self.assertEqual(plan['window_limit_minutes'], 45)
            self.assertEqual(plan['stop_new_tests_by_minute'], 35)
            keys += board_keys
        self.assertEqual(len(keys), 166)
        self.assertEqual(len(set(keys)), 166)
        self.assertEqual(set(keys), set(base['keys']))

    def test_finish_without_stage_a_falls_back_to_u9(self):
        composition = json.loads((H / 'composition.json').read_text())
        baseline = json.loads((H.parents[1] / 'benchmark/2026-10-01-u9-sweep/outer-signoff.json').read_text())
        good = {'signed_by': 'outer(claude)', 'bundle_sha256': composition['bundle_sha256'], 'native_manifest_sha256': composition['native_manifest_sha256'], 'keys': copy.deepcopy(baseline['keys']), 'controls_t20_lit': ['helloworld', 'zigzag'], 'confirmed_regressions': []}
        good['keys']['toutiao']['verdict'] = 'lit'
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / 'runner/smoke').mkdir(parents=True)
            (root / 'runner/smoke/smoke-result.json').write_text('{"passed":true}')
            decision = root / 'decision.json'
            decision.write_text(json.dumps(good))
            with patch.object(hook.previous, 'finish') as rollback:
                hook.finish('61b0657200000000000000000324012c', root, root / 'restored.json', decision)
                rollback.assert_called_once()
            report = json.loads((root / 'retention.json').read_text())
            self.assertFalse(report['retained'])
            self.assertEqual(report['reason'], 'Stage A prerequisite absent')

    def test_observation_always_rolls_back(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / 'outer-promotion.json').write_text(json.dumps(self.good))
            with patch.object(hook.previous, 'finish') as rollback, patch.object(hook, 'admission') as admission:
                hook.finish_observation('serial', root, root / 'restored.json')
                rollback.assert_called_once()
                admission.assert_not_called()
            self.assertFalse(json.loads((root / 'retention.json').read_text())['retained'])
            self.assertTrue(json.loads((root / 'observation-restored.json').read_text())['passed'])

    def test_stage_b_requires_separate_authorization_and_full_same_sha_signoff(self):
        with tempfile.TemporaryDirectory() as directory:
            decision = Path(directory) / 'A.json'
            with patch.object(hook, 'retention_reason', return_value=None):
                decision.write_text(json.dumps({'phase': 'A'}))
                with self.assertRaisesRegex(AssertionError, 'separate Stage B'):
                    hook.stage_a_admission(decision)
            with self.assertRaisesRegex(AssertionError, 'Stage A prerequisite'):
                hook.stage_a_admission(None)
        for short in ['5ea', '5cd', '61b']:
            plan = json.loads((H / 'window' / ('plan-promotion-' + short + '.json')).read_text())
            self.assertEqual(plan['phase'], 'B')
            self.assertEqual(plan['window_limit_minutes'], 30)
            self.assertFalse(plan['execution_enabled'])
            self.assertEqual(len(plan['shards']), 1)
            self.assertIn('--stage-a-decision', plan['after_lock'])
            self.assertIn('--decision', plan['before_unlock'])

    def test_stage_b_fresh_review_failure_rolls_back(self):
        for field, value in [('toutiao_t20', 'white'), ('window_root', 'other'), ('controls_t20_lit', []), ('bundle_sha256', 'other')]:
            with tempfile.TemporaryDirectory() as directory:
                root = Path(directory)
                (root / 'runner/smoke').mkdir(parents=True)
                (root / 'runner/smoke/smoke-result.json').write_text('{"passed":true}')
                composition = json.loads((H / 'composition.json').read_text())
                decision = {'phase': 'B', 'serial': 'serial', 'window_root': str(root),
                    'signed_by': 'outer(claude)', 'bundle_sha256': composition['bundle_sha256'],
                    'native_manifest_sha256': composition['native_manifest_sha256'],
                    'toutiao_t20': 'lit', 'controls_t20_lit': ['helloworld', 'zigzag'], 'confirmed_regressions': []}
                decision[field] = value
                path = root / 'decision.json'; path.write_text(json.dumps(decision))
                with patch.object(hook, 'stage_a_admission'), patch.object(hook.previous, 'finish') as rollback, patch.object(hook, 'verify_candidate') as verify:
                    hook.finish('serial', root, root / 'restored.json', path, root / 'A.json')
                    rollback.assert_called_once(); verify.assert_not_called()

    def test_stage_b_fresh_review_and_identity_can_retain(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / 'runner/smoke').mkdir(parents=True)
            (root / 'runner/smoke/smoke-result.json').write_text('{"passed":true}')
            composition = json.loads((H / 'composition.json').read_text())
            decision = {'phase': 'B', 'serial': 'serial', 'window_root': str(root),
                'signed_by': 'outer(claude)', 'bundle_sha256': composition['bundle_sha256'],
                'native_manifest_sha256': composition['native_manifest_sha256'], 'toutiao_t20': 'lit',
                'controls_t20_lit': ['helloworld', 'zigzag'], 'confirmed_regressions': []}
            path = root / 'decision.json'; path.write_text(json.dumps(decision))
            with patch.object(hook, 'stage_a_admission'), patch.object(hook, 'admission'), patch.object(hook.previous, 'finish') as rollback, patch.object(hook, 'verify_candidate') as verify:
                hook.finish('serial', root, root / 'restored.json', path, root / 'A.json')
                rollback.assert_not_called(); verify.assert_called_once()
            self.assertTrue(json.loads((root / 'retention.json').read_text())['retained'])

    def test_failed_observation_finish_never_writes_success_receipt(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            with patch.object(hook.previous, 'finish', side_effect=RuntimeError('recovery failed')):
                with self.assertRaises(RuntimeError):
                    hook.finish_observation('serial', root, root / 'restored.json')
            self.assertFalse((root / 'observation-restored.json').exists())


if __name__ == '__main__':
    unittest.main()
