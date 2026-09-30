#!/usr/bin/env python3
from collections import Counter
from datetime import datetime
import json
import unittest

from collect import PID, normalized
from score import HERE, SWEEP, FROZEN, build, read, references, render, sha


class IdentityTests(unittest.TestCase):
    def test_frozen_cohort_and_record_identity(self):
        report = read(SWEEP / 'J6N4-SCORING.json')
        predictions = {row['key']: row for row in read(SWEEP / 'j6n4-predictions/criteria.json')['rows']}
        indices = {item['key']: item for shard in ('5cd', '5ea', '61b')
                   for item in read(HERE / 'evidence' / ('index-' + shard + '.json'))['selected']}
        self.assertEqual(len(report['rows']), 66)
        self.assertEqual({row['key'] for row in report['rows']}, set(predictions))
        self.assertEqual(set(predictions), set(indices))
        audit = read(HERE / 'source-verification.json')
        self.assertEqual(audit['verified_files'], 135)
        pinned = {item['path']: item for item in audit['files']}
        FROZEN.verify_freeze(SWEEP, read(SWEEP / 'scoring-inputs/J6N4-predictions-reference.json'))
        binding = read(HERE / 'evidence/inputs.json')
        self.assertEqual(binding['prediction_sha256'], report['prediction_sha256'])
        planned = datetime.fromisoformat(binding['planned_at']).timestamp()
        self.assertEqual(sha((HERE / 'evidence/runtime-fingerprint.txt').read_bytes().strip())[:12], '73ecf422dba2')
        self.assertEqual(sha((HERE / 'evidence/boot-image-fingerprint.txt').read_bytes().strip())[:12], '0876029078e2')
        self.assertIn(binding['jar_sha256'], (HERE / 'evidence/runtime-fingerprint.txt').read_text())
        for row in report['rows']:
            with self.subTest(key=row['key']):
                key = row['key']
                source = row['source']
                data = (HERE / 'evidence/records' / (key + '.json')).read_bytes()
                record = json.loads(data)
                self.assertEqual(sha(data), source['record_sha256'])
                self.assertEqual(sha(data), indices[key]['record_sha256'])
                self.assertEqual(sha(data), pinned['evidence/records/' + key + '/record.json']['sha256'])
                self.assertEqual(source['record'], indices[key]['record'])
                self.assertEqual(record['apk_sha256'], predictions[key]['apk_sha256'])
                self.assertEqual(record['package'], predictions[key]['package'])
                self.assertEqual(source['u4_record_sha256'], predictions[key]['record_sha256'])
                self.assertEqual(source['sidecars'], source['u4_sidecars'])
                if record.get('clicked_at'):
                    self.assertLess(planned, record['clicked_at'])
                if source['t20_sha256']:
                    shot = next(shot for shot in record['screenshots'] if shot['scheduled_seconds'] == 20)
                    self.assertTrue(shot['captured'])
                    self.assertEqual(source['t20_sha256'], shot['sha256'])
                    self.assertEqual(source['t20_sha256'], pinned['evidence/t20/' + key + '.jpeg']['sha256'])
                if key in ('fd-seal', 'toutiao', 'subwaysurfers'):
                    self.assertFalse(record['clicked'])
                    self.assertIsNone(source['t20_sha256'])
                    self.assertEqual(row['verdict'], 'unknown')
        organic = next(row for row in report['rows'] if row['key'] == 'fd-organicmaps')
        self.assertEqual(organic['source']['status'], 'batch_interrupted')
        self.assertIn('/u5-5ea/', organic['source']['record'])

    def test_raw_line_pins_and_target_attribution(self):
        report = read(SWEEP / 'J6N4-SCORING.json')
        for name, expected in report['input_pins'].items():
            self.assertEqual(sha((HERE / name).read_bytes()), expected, name)
        for row in report['rows']:
            key = row['key']
            data = (HERE / 'evidence/logs' / (key + '.json')).read_bytes()
            self.assertEqual(sha(data), row['source']['excerpts_sha256'])
            log = json.loads(data)
            by_line = {item['line']: item['text'] for item in log}
            self.assertEqual(len(by_line), len(log))
            for item in log:
                match = PID.match(item['text'])
                self.assertIsNotNone(match)
                self.assertIn(match[1], row['source']['target_pids'])
                self.assertLessEqual(item['line'], row['source']['log_lines'])
            evidence = row['observed']['old_wall_evidence'][:]
            for check in row['observed']['checkpoints'].values():
                evidence += check['evidence'] + check['partial_evidence']
            for missed in row['missed_signatures']:
                evidence += missed['evidence']
            for number in evidence:
                self.assertIn(number, by_line)
            for number in row['source']['binding_lines']:
                self.assertIn('bundle=' + row['source']['package'] + ' ', by_line[number])
        self.assertEqual(sum(bool(row['source']['t20_sha256']) for row in report['rows']), 63)
        self.assertEqual(sum(row['source']['identity_and_capture_valid'] for row in report['rows']), 63)


class DecisionTests(unittest.TestCase):
    def test_reproduction_and_denominators(self):
        report = build()
        self.assertEqual(report, read(SWEEP / 'J6N4-SCORING.json'))
        self.assertEqual(render(report), (SWEEP / 'J6N4-SCORING.md').read_text())
        self.assertEqual(report['counts'], {'hit': 38, 'false_positive': 2, 'unknown': 26})
        self.assertEqual(report['evaluable'], 40)
        self.assertEqual(report['primary_checkpoints'], {'count': 18, 'verdicts': {'unknown': 17, 'false_positive': 1}})
        self.assertEqual(Counter(row['verdict'] for row in report['rows'] if row['preservation_control']), {'hit': 23, 'false_positive': 1})
        self.assertEqual(sum(row['t20'] == 'own-ui' for row in report['rows']), 24)
        self.assertEqual((report['missed_signature_families'], report['missed_signature_keys']), (7, 14))
        for row in report['rows']:
            if 'N4-owner' in row['fix_ids']:
                self.assertEqual(row['source']['marker_counts']['[N2-OWNER] ABI global ready'], 0)
            if row['observed']['old_wall_evidence']:
                predicted = next(item for item in read(SWEEP / 'j6n4-predictions/criteria.json')['rows'] if item['key'] == row['key'])
                log = read(HERE / 'evidence/logs' / (row['key'] + '.json'))
                for number in row['observed']['old_wall_evidence']:
                    text = next(item['text'] for item in log if item['line'] == number)
                    self.assertEqual(normalized(text), normalized(predicted['current_wall_evidence']))

    def test_no_absence_only_or_mixed_checkpoint_success(self):
        row = {'prediction': '过墙', 'fix_ids': ['owner', 'metadata'], 'preservation_control': False}
        observed = {'identity_and_capture_valid': True, 'checkpoints': {
            'owner': {'state': 'crossed', 'evidence': [10]}, 'metadata': {'state': 'unknown', 'evidence': []}}}
        self.assertEqual(FROZEN.score_reviewed(row, observed), 'unknown')
        observed['checkpoints']['metadata'] = {'state': 'crossed', 'evidence': [20]}
        self.assertEqual(FROZEN.score_reviewed(row, observed), 'hit')
        observed['checkpoints']['metadata'] = {'state': 'old-wall', 'evidence': [30]}
        self.assertEqual(FROZEN.score_reviewed(row, observed), 'false_positive')
        observed['identity_and_capture_valid'] = False
        self.assertEqual(FROZEN.score_reviewed(row, observed), 'unknown')
        with self.assertRaises(ValueError):
            references([{'line': 1, 'text': 'registration only'}], ['executed eglInitialize'])

    def test_ui_and_unknown_forecasts_cannot_be_reclassified(self):
        row = {'prediction': '不变', 'fix_ids': [], 'preservation_control': True}
        observed = {'identity_and_capture_valid': True, 'own_ui': True, 't20_sha256': 'pinned'}
        self.assertEqual(FROZEN.score_reviewed(row, observed), 'unknown')
        observed['outer_review'] = 'outer signed first t20'
        self.assertEqual(FROZEN.score_reviewed(row, observed), 'hit')
        observed['own_ui'] = False
        self.assertEqual(FROZEN.score_reviewed(row, observed), 'false_positive')
        row['prediction'] = 'unknown'
        self.assertEqual(FROZEN.score_reviewed(row, observed), 'unknown')


if __name__ == '__main__':
    unittest.main()
