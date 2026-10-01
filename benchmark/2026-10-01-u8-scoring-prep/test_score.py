import copy
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

import score


def inputs():
    frozen = score.predictions()
    prior, _ = score.baselines(frozen)
    signed = json.loads((score.ROOT/score.CV2_BASELINE).read_text())
    return frozen, prior, signed


def formal_fixture(frozen, prior):
    rows = [dict(key=key, verdict='lit' if before['own_ui'] else 'dead', board='fixture-only')
            for key, before in prior.items()]
    return dict(schema='outer-signoff-v1', signed_by='synthetic-test-only', board_entry='fixture-not-a-board-signoff',
                state=score.U8_STATE.copy(), keys=rows, counts=dict(score.Counter(row['verdict'] for row in rows)))


class IdentityTests(unittest.TestCase):
    def test_frozen_drift(self):
        path, pin, count = score.PINS['cv2']
        with self.assertRaisesRegex(ValueError, 'SHA mismatch'):
            score.parse_prediction((score.ROOT/path).read_bytes()+b'\n', pin, count)

    def test_formal_refuses_one_hundred_keys(self):
        frozen, prior, signed = inputs()
        with self.assertRaises(ValueError):
            score.build(frozen, prior, signed)

    def test_duplicate_and_wrong_keys(self):
        frozen, prior, _ = inputs()
        for change in ['duplicate', 'wrong']:
            signed = formal_fixture(frozen, prior)
            signed['keys'][0]['key'] = signed['keys'][1]['key'] if change=='duplicate' else 'not-a-signed-key'
            with self.subTest(change=change), self.assertRaises(ValueError):
                score.build(frozen, prior, signed)

    def test_state_and_totals(self):
        frozen, prior, _ = inputs()
        for change in ['state', 'counts', 'authority']:
            signed = formal_fixture(frozen, prior)
            if change=='state':
                signed['state'] = score.BASELINE_STATE
            elif change=='counts':
                signed['counts']['lit'] += 1
            else:
                signed['signed_by'] = ''
            with self.subTest(change=change), self.assertRaises(ValueError):
                score.build(frozen, prior, signed)

    def test_cli_refusal_publishes_nothing(self):
        with tempfile.TemporaryDirectory() as temporary:
            output = Path(temporary)/'score'
            self.assertEqual(score.main(['--signoff', str(score.ROOT/score.CV2_BASELINE), '--output', str(output)]), 2)
            self.assertFalse(output.exists())


class VisualTests(unittest.TestCase):
    def test_unknown_is_not_negative(self):
        frozen, prior, signed = inputs()
        result = score.build(frozen, prior, signed, replay=True)
        metrics = result['cv2']['metrics']
        self.assertEqual(metrics['abstentions'], 27)
        self.assertIsNone(metrics['true_negative'])
        self.assertIsNone(metrics['false_negative'])
        self.assertEqual(metrics['functional_precision'], dict(numerator=54, denominator=73))
        self.assertEqual(metrics['own_ui_precision'], dict(numerator=56, denominator=73))

    def test_functional_fallback_regression_separate(self):
        frozen, prior, signed = inputs()
        observed = {row['key']:copy.deepcopy(row) for row in signed['keys']}
        key = next(key for key in frozen['cv2'] if prior[key]['visual']=='lit')
        observed[key]['verdict'] = 'lit-webview-fallback'
        row = next(row for row in score.changes(frozen, prior, observed)['rows'] if row['key']==key)
        self.assertEqual(row['own_ui_change'], 'unchanged')
        self.assertEqual(row['functional_change'], 'regression')

    def test_new_lit_and_regression(self):
        frozen, prior, signed = inputs()
        observed = {row['key']:copy.deepcopy(row) for row in signed['keys']}
        dark = next(key for key in frozen['cv2'] if not prior[key]['own_ui'])
        bright = next(key for key in frozen['cv2'] if prior[key]['own_ui'])
        observed[dark]['verdict'] = 'lit'
        observed[bright]['verdict'] = 'dead'
        rows = {row['key']:row for row in score.changes(frozen, prior, observed)['rows']}
        self.assertEqual(rows[dark]['own_ui_change'], 'new-lit')
        self.assertEqual(rows[bright]['own_ui_change'], 'regression')

    def test_old_labels_not_fake_functional_or_death(self):
        frozen, prior, _ = inputs()
        result = score.build(frozen, prior, formal_fixture(frozen, prior))
        old_rows = [row for row in result['changes']['rows'] if row['key'] not in frozen['cv2']]
        self.assertEqual(len(old_rows), 66)
        self.assertTrue(all(row['functional_change']=='unknown-old-coarse-or-unobserved' for row in old_rows))
        self.assertIn('desktop', {row['baseline_visual'] for row in old_rows})


class RiskTests(unittest.TestCase):
    def test_later_lit_is_not_false_positive(self):
        frozen, prior, signed = inputs()
        result = score.build(frozen, prior, signed, replay=True)
        controls = result['actionbar']['previously_lit_later_only']
        self.assertEqual(controls['keys'], 22)
        self.assertIsNone(result['actionbar']['tiers']['later-activity-only']['binary_accuracy'])
        self.assertTrue(all(row['wall_score'].startswith('unknown') for row in result['actionbar']['rows']))
        self.assertTrue(all(row['provider_checkpoint_score'].startswith('unknown') for row in result['webview']['rows']))

    def test_root_uses_terminal_linked_chain_not_context(self):
        fatal = dict(status='termination-found', root=dict(status='linked-exception', event=dict(message='NullPointerException: WebSettings'), chain=[]),
                     context=[dict(message='at AppCompatActivity.setSupportActionBar')])
        self.assertEqual(score.root_family(fatal), 'webview-settings-null')
        fatal['status'] = 'no-termination-found'
        self.assertEqual(score.root_family(fatal), 'unknown')

    def test_family_does_not_claim_provider_checkpoint(self):
        frozen, prior, signed = inputs()
        key = next(key for key,row in frozen['webview'].items() if row['first_screen_prediction']=='blocked-WebSettings-null')
        result = score.build(frozen, prior, signed, replay=True, logs={key:dict(family='webview-settings-null')})
        row = next(row for row in result['webview']['rows'] if row['key']==key)
        self.assertEqual(row['first_wall_score'], 'family-hit-needs-callsite-review')
        self.assertTrue(row['provider_checkpoint_score'].startswith('unknown'))

    def test_raw_duplicates_sha_and_state(self):
        frozen, _, _ = inputs()
        key = next(iter(frozen['actionbar']))
        record = dict(key=key, package=frozen['actionbar'][key]['package'], apk_sha256=frozen['actionbar'][key]['apk_sha256'])
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            first = root/'first'
            first.mkdir()
            path = first/'record.json'
            path.write_text(json.dumps(record))
            output = score.diagnostics([root], frozen, score.U8_STATE)
            self.assertEqual(output[key]['status'], 'unbound-run-state')
            second = root/'second'
            second.mkdir()
            (second/'record.json').write_text(json.dumps(record))
            with self.assertRaisesRegex(ValueError, 'Duplicate'):
                score.diagnostics([root], frozen, score.U8_STATE)
            (second/'record.json').unlink()
            (root/'facts.txt').write_text('RUNTIME fingerprint=000000000000\nBOOTIMAGE fingerprint=000000000000\n')
            with self.assertRaisesRegex(ValueError, 'runtime/image mismatch'):
                score.diagnostics([root], frozen, score.U8_STATE)
            (root/'facts.txt').unlink()
            record['apk_sha256'] = '0'*64
            path.write_text(json.dumps(record))
            with self.assertRaisesRegex(ValueError, 'APK/package mismatch'):
                score.diagnostics([root], frozen, score.U8_STATE)

    def test_bound_logs_use_first_fatal(self):
        frozen, _, _ = inputs()
        key = next(iter(frozen['actionbar']))
        prediction = frozen['actionbar'][key]
        fatal = dict(status='termination-found', root=dict(status='linked-exception', event=dict(message='already has an action bar'), chain=[]))
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            (root/'record.json').write_text(json.dumps(dict(key=key, package=prediction['package'], apk_sha256=prediction['apk_sha256'])))
            (root/'hilog.txt').write_text('fixture')
            (root/'facts.txt').write_text('\n'.join(field+' fingerprint='+pin for field,pin in score.U8_STATE.items()))
            with patch.object(score.first_fatal, 'load_run', return_value=({},[],set(),[],False,{'fixture':True})) as loader, patch.object(score.first_fatal, 'analyze', return_value=fatal):
                output = score.diagnostics([root], frozen, score.U8_STATE)
            loader.assert_called_once_with(root)
            self.assertEqual(output[key]['family'], 'appcompat-actionbar-theme')

    def test_real_parser_pid_chain_and_diagnostic_pin(self):
        frozen, _, _ = inputs()
        key = next(iter(frozen['actionbar']))
        prediction = frozen['actionbar'][key]
        messages = [(999, 'FATAL EXCEPTION: foreign'), (999, 'java.lang.IllegalStateException: already has an action bar'),
                    (123, 'FATAL EXCEPTION: main'), (123, 'java.lang.RuntimeException: outer'),
                    (123, 'Caused by: java.lang.NullPointerException: WebSettings.getUserAgentString on null'),
                    (123, 'at target.MainActivity.onCreate(MainActivity.java:4)')]
        payload = ''.join(f'10-01 04:30:00.000 {pid} 456 I C00f00/AppSpawnXJava: {message}\n' for pid,message in messages).encode()
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            record = dict(key=key, package=prediction['package'], apk_sha256=prediction['apk_sha256'], observed_pids=[123],
                          diagnostics=dict(sha256=score.digest(payload)))
            (root/'record.json').write_text(json.dumps(record))
            (root/'hilog.txt').write_bytes(payload)
            (root/'facts.txt').write_text('\n'.join(field+' fingerprint='+pin for field,pin in score.U8_STATE.items()))
            result = score.diagnostics([root], frozen, score.U8_STATE)[key]
            self.assertEqual(result['family'], 'webview-settings-null')
            self.assertEqual(result['first_fatal']['root']['event']['line'], 5)
            self.assertEqual(result['first_fatal']['terminal']['event']['pid'], 123)
            (root/'hilog.txt').write_bytes(payload+b'changed')
            with self.assertRaisesRegex(ValueError, 'diagnostic receipt'):
                score.diagnostics([root], frozen, score.U8_STATE)


class ReplayTests(unittest.TestCase):
    def test_actual_cv2_replay(self):
        frozen, prior, signed = inputs()
        result = score.build(frozen, prior, signed, replay=True)
        self.assertFalse(result['formal'])
        self.assertEqual(result['changes']['own_ui_counts'], {'unchanged':100, 'unobserved':66})
        self.assertEqual(len(result['changes']['rows']), 166)
        self.assertEqual(result['webview']['exact_t20'], dict(hits=5, observed=7))
        self.assertTrue(result['cv2']['late_freeze'])
        self.assertTrue(result['webview']['late_freeze'])

    def test_cli_outputs_all_three_tables(self):
        with tempfile.TemporaryDirectory() as temporary:
            output = Path(temporary)
            self.assertEqual(score.main(['--signoff', str(score.ROOT/score.CV2_BASELINE), '--output', str(output), '--replay-cv2']), 0)
            self.assertEqual({path.name for path in output.iterdir()}, {'SCORING.json','SCORING.md','CHANGES.csv','CV2.csv','ACTIONBAR.csv','WEBVIEW.csv'})
            self.assertEqual(json.loads((output/'SCORING.json').read_text())['observed_keys'], 100)


if __name__ == '__main__':
    unittest.main()
