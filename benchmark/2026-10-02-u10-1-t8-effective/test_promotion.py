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

    def test_unapproved_gates_block_before_vm(self):
        with patch.object(hook.previous, 'vm') as vm:
            with self.assertRaisesRegex(AssertionError, 'offline gates are not all green'):
                hook.admission()
            vm.assert_not_called()

    def test_all_plans_refuse_before_infra_and_lock(self):
        spec = importlib.util.spec_from_file_location('dispatch', H / 'promotion_dispatch.py')
        dispatch = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(dispatch)
        with patch.object(dispatch.subprocess, 'run') as run:
            for short in ['5ea', '5cd', '61b']:
                plan = json.loads((H / 'window' / ('plan-' + short + '.json')).read_text())
                with self.assertRaisesRegex(RuntimeError, 'REFUSE before infra or LOCK'):
                    dispatch.prelock(plan)
            run.assert_not_called()

    def test_full_shards_match_signed_u9_keys(self):
        base = json.loads((H.parents[1] / 'benchmark/2026-10-01-u9-sweep/outer-signoff.json').read_text())
        keys = []
        for short in ['5ea', '5cd', '61b']:
            for group in ['original', 'cv2']:
                keys += (H / 'window' / ('keys-' + short + '-' + group + '.txt')).read_text().split()
        self.assertEqual(len(keys), 166)
        self.assertEqual(len(set(keys)), 166)
        self.assertEqual(set(keys), set(base['keys']))

    def test_finish_refused_admission_falls_back_to_u9(self):
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
            self.assertIn('offline gates are not all green', report['reason'])


if __name__ == '__main__':
    unittest.main()
