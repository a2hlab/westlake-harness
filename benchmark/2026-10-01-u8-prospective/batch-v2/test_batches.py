import copy
import hashlib
import json
from pathlib import Path
import unittest

import report

HERE = Path(__file__).resolve().parent


def validate(result):
    keys = [app['key'] for row in result['batches'] for app in row['apps']]
    if len(keys) != 32 or len(set(keys)) != 32:
        raise ValueError('cohort changed')
    for row in result['batches']:
        for donor in row['donor_ids']:
            if donor not in result['donors']:
                raise ValueError('unbound donor')
        if row['predicted_first_wall_moves'] and row['donor_grade'] != 'prior-bundle-movement':
            raise ValueError('unverified movement promoted')
        if row['built_verified_fix']:
            raise ValueError('no built fix in batch intake')


class DonorTests(unittest.TestCase):
    def test_three_trees_and_pins(self):
        intake = report.load_intake()
        searches = intake['searches']
        self.assertEqual(set(searches['repositories']), {'Westlake','00.Workspace','real-work'})
        self.assertEqual(len(searches['searches']), 33)
        self.assertTrue(all(entry['returncode'] in (0,1) for entry in searches['searches']))
        for donor in intake['sources'].values():
            self.assertEqual(len(donor['commit']),40)
            self.assertEqual(len(donor['last_change_commit']),40)
            self.assertEqual(len(donor['sha256']),64)
            self.assertTrue(donor['path'] and donor['excerpt'])
        for quote in intake['authority']:
            self.assertEqual(hashlib.sha256(quote['text'].encode()).hexdigest(),quote['sha256'])
        self.assertIn('08:28:40', {quote['timestamp'] for quote in intake['authority']})

    def test_missing_donor_rejected(self):
        result = report.build(report.load_intake())
        result['donors'].pop('color-matrix')
        with self.assertRaisesRegex(ValueError,'unbound donor'):
            validate(result)


class CoverageTests(unittest.TestCase):
    def test_exact_cohort_and_routes(self):
        intake = report.load_intake()
        result = report.build(intake)
        validate(result)
        self.assertEqual(result['route_counts'], {'N10':18,'J8':9,'deferred':5})
        self.assertEqual(len({row['parent_cluster'] for row in result['batches']}),22)
        self.assertEqual(len(result['batches']),23)
        rows = {row['id']:row for row in result['batches']}
        self.assertEqual(rows['white-B2']['apps'][0]['key'],'termux')
        self.assertEqual(rows['white-A']['conditional_first_wall_moves'],['wikipedia'])
        for identifier in ['osmand-map-info-null','system-exit-unknown','mcd-datasource-null','installer-no-bm-record','toutiao-boolean-null']:
            self.assertEqual(rows[identifier]['predicted_first_wall_moves'],[])
            self.assertEqual(rows[identifier]['conditional_first_wall_moves'],[])
        self.assertEqual(sum(len(row['predicted_first_wall_moves']) for row in result['batches']),6)

    def test_secondary_cause_cannot_be_promoted(self):
        result = copy.deepcopy(report.build(report.load_intake()))
        row = next(row for row in result['batches'] if row['id']=='osmand-map-info-null')
        row['predicted_first_wall_moves'] = ['fd-plus']
        with self.assertRaisesRegex(ValueError,'unverified movement'):
            validate(result)


class ReplayTests(unittest.TestCase):
    def test_artifacts_match(self):
        result = report.build(report.load_intake())
        self.assertEqual(json.loads((HERE/'results.json').read_text()),result)
        self.assertEqual((HERE/'README.md').read_text(),report.markdown(result))
        self.assertFalse(result['freeze_authorized'])
        self.assertFalse(result['expected_run_created'])
        self.assertIn('superseded',(HERE.parent/'README.md').read_text())
        self.assertEqual(list(HERE.glob('*.csv')),[])
        self.assertFalse((HERE/'expected-run.json').exists())
        self.assertFalse((HERE/'FREEZE.json').exists())


if __name__ == '__main__':
    unittest.main()
