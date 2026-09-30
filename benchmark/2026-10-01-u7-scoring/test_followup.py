import copy
from pathlib import Path
import unittest

import intake
import signed_intake
import signed_score


HERE = Path(__file__).resolve().parent


class IntakeTests(unittest.TestCase):
    def test_partition_and_first_attempts(self):
        main = dict(records=[dict(key=str(number)) for number in range(16)], not_run=[str(number) for number in range(16, 22)], batch_error="target cleanup could not be verified; stop before next app")
        resume = dict(records=[dict(key=str(number)) for number in range(16, 22)], not_run=[])
        signed_intake.validate_segments([main, resume], [str(number) for number in range(22)])
        bad = copy.deepcopy(resume)
        bad['records'][0]['key'] = '0'
        with self.assertRaisesRegex(ValueError, 'unique'):
            signed_intake.validate_segments([main, bad], [str(number) for number in range(22)])
        with self.assertRaisesRegex(ValueError, 'later timed'):
            intake.first_attempt('second', [dict(record='first', clicked_at=1), dict(record='second', clicked_at=2)])
        self.assertTrue(intake.first_attempt('first', [dict(record='prelaunch', clicked_at=None), dict(record='first', clicked_at=1)]))

    def test_actual_seal_and_forecast_unchanged(self):
        prepared = intake.u6.read(HERE / 'signed-44/5cd-prepared.json')
        self.assertEqual(len(prepared['rows']), 22)
        seal = next(row for row in prepared['rows'] if row['key'] == 'fd-seal')
        self.assertIsNone(seal['t20_sha256'])
        self.assertFalse(seal['first_attempt'])
        self.assertFalse(seal['identity_verified'])
        self.assertEqual(len(intake.verify_freeze()['files']), 149)


class ScoreTests(unittest.TestCase):
    def test_signed_axes_and_gains(self):
        report = signed_score.build()
        self.assertEqual(report, intake.u6.read(HERE / 'signed-44/results.json'))
        self.assertEqual(signed_score.markdown(report), (HERE / 'signed-44/SCORING.md').read_text())
        self.assertEqual(report['shards']['5ea']['axes']['t20'], {'hit': 21, 'unknown': 1})
        self.assertEqual(report['shards']['5cd']['axes']['t20'], {'hit': 17, 'false_positive': 1, 'unknown': 4})
        rows = {row['key']: row for row in report['shards']['5cd']['rows']}
        self.assertEqual(rows['fd-plus']['root_line'], 60357)
        self.assertEqual(rows['fd-reader']['scores']['checkpoints'], 'unknown')
        old = {row['key']: row for row in intake.u6.read(HERE / 'signed-44/gains-u6-evidence.json')}
        self.assertEqual(old['fd-reader']['termination']['root']['event']['line'], 65240)
        self.assertIsNone(old['fd-organicmaps']['termination']['root'])

    def test_capture_and_native_reason_drift_reject(self):
        prepared = intake.u6.read(HERE / 'signed-44/5cd-prepared.json')
        review = intake.u6.read(HERE / 'signed-44/reviews.json')
        authority = intake.u6.read(HERE / 'signed-44/outer-signoffs.json')
        row = next(row for row in prepared['rows'] if row['key'] == 'fd-fluffychat')
        changed = copy.deepcopy(review['rows'][row['key']])
        changed['t20_sha256'] = '0' * 64
        with self.assertRaisesRegex(ValueError, 'evidence drift'):
            signed_score.score_row(row, changed, authority)
        changed = copy.deepcopy(review['rows'][row['key']])
        changed['reason_line'] = 1
        with self.assertRaisesRegex(ValueError, 'native wall'):
            signed_score.score_row(row, changed, authority)


class FullTests(unittest.TestCase):
    def test_full_replay_rates_and_unknowns(self):
        report = signed_score.build(full=True)
        self.assertEqual(report, intake.u6.read(HERE / 'formal-66/results.json'))
        self.assertEqual(signed_score.markdown(report), (HERE / 'formal-66/SCORING.md').read_text())
        self.assertEqual(report['forecast_counts'], {'own-ui': 28, 'unlit': 32, 'unknown': 6})
        self.assertEqual(report['axes']['first_wall'], {'hit': 48, 'unknown': 18})
        self.assertEqual(report['axes']['t20'], {'hit': 59, 'false_positive': 1, 'unknown': 6})
        self.assertAlmostEqual(report['rates']['t20']['hit_fraction_on_scored'], 59 / 60)
        self.assertEqual(report['confirmed_unpredicted_fatal_walls'], [])
        self.assertEqual(report['visual_counts']['own-ui'], 34)
        self.assertEqual(len(report['unknown_first_wall_keys']), 18)


if __name__ == '__main__':
    unittest.main()
