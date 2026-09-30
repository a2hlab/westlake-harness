import hashlib
import json
from pathlib import Path
import sys
import unittest

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
J3 = HERE.parent / '2026-09-30-round1-plan/j3-feedback'
sys.path.insert(0, str(J3.parent / 'shard'))
from merge_facts import record_facts

def read(path):
    return json.loads(path.read_text())

def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()

class ReceiptTests(unittest.TestCase):
    def test_real_inputs_and_explicit_revision(self):
        result = read(HERE / 'results.json')
        batch = HERE.parent / '2026-09-28-bms-route-deploy/batch'
        self.assertEqual(result['batch_sha256'], sha(batch / 'bms_batch.py'))
        self.assertEqual(result['manifest_sha256'], sha(batch / 'apps.json'))
        self.assertEqual(result['source_allowlist_sha256'], sha(Path(result['source_allowlist'])))
        expected = {'fd-seal': (9, 3), 'toutiao': (138, 1), 'subwaysurfers': (20, 0)}
        self.assertEqual({r['key'] for r in result['inputs']}, set(expected))
        for row in result['inputs']:
            self.assertEqual(row['status'], 'host-preflight-pass')
            self.assertEqual(sha(Path(row['metadata'])), row['input_metadata_sha256'])
            app = row['resolved']
            self.assertEqual(sha(Path(app['apk'])), app['apk_sha256'])
            libs = app['native_sidecars']
            self.assertEqual((len(libs), sum(bool(x.get('payload_exception')) for x in libs)), expected[row['key']])
        pair = result['subway_pair']
        self.assertEqual(len(pair), 2)
        self.assertEqual(pair[0]['signer_sha256'], pair[1]['signer_sha256'])
        for item in pair:
            self.assertIn("versionCode='95769'", item['package_line'])
            self.assertEqual(item['sha256'], sha(Path(item['path'])))
        self.assertEqual(result['subway_split_non_native_members'], ['stamp-cert-sha256'])
        apps = read(batch / 'apps.json')
        if isinstance(apps, dict):
            apps = apps['apps']
        subway = next(x for x in apps if x['key'] == 'subwaysurfers')
        self.assertEqual(subway['apk_sha256'], pair[0]['sha256'])
        self.assertIn('5904cda2', json.dumps(subway['identity_revision']))
        self.assertIsNone(result['screenshots'])
        self.assertIsNone(result['alive'])

    def test_current_records_and_unlock_boundaries(self):
        evidence = read(J3 / 'evidence.json')
        clusters = read(J3 / 'next-clusters.json')
        result = read(J3 / 'results.json')
        runs = read(J3 / 'run-audit.json')
        facts = read(J3 / 'record-facts.json')
        self.assertEqual(len(evidence), 66)
        self.assertEqual(sum(r['lit'] for r in evidence), 25)
        unlit = {r['key'] for r in evidence if not r['lit']}
        self.assertEqual(len(unlit), 41)
        self.assertEqual(set().union(*(set(c['currently_unlit_keys']) for c in clusters)), unlit)
        self.assertEqual(runs[0]['fingerprint'], runs[1]['fingerprint'])
        self.assertEqual(len(runs[0]['fingerprint']), 119)
        self.assertEqual(facts, [record_facts(Path(row['record'])) for row in facts])
        self.assertEqual(sum(f['captured'] for f in facts), result['captured'])
        self.assertEqual(result['captured'], 126)
        for t in ['t5', 't20']:
            actual = dict(yes=sum(f['alive_'+t] is True for f in facts), no=sum(f['alive_'+t] is False for f in facts), unknown=sum(f['alive_'+t] is None for f in facts))
            self.assertEqual(actual, result['alive'][t])
        byid = {c['cluster_id']: c for c in clusters}
        self.assertEqual(byid['J4-boot-api']['expected_unlock_keys'], [])
        self.assertEqual(len(byid['J4-boot-api']['conditional_unlock_keys']), 5)
        self.assertEqual(byid['J4-platform-signature']['expected_new_lights'], 0)
        self.assertEqual(byid['J4-alias-theme']['expected_unlock_keys'], [])
        self.assertEqual(byid['N3-no-fatal-observation']['expected_unlock_keys'], [])
        for c in clusters:
            self.assertTrue(set(c['expected_unlock_keys']) <= unlit)
            self.assertTrue(c['execution_lane'])
        bykey = {r['key']: r for r in evidence}
        for key, excerpts in read(J3 / 'target-evidence.json').items():
            lines = Path(bykey[key]['log']).read_text(errors='replace').splitlines()
            for excerpt in excerpts:
                self.assertEqual(lines[excerpt['line']-1], excerpt['text'])
                self.assertIn(excerpt['text'].split()[2], bykey[key]['pids'])
        for path, digest in result['source_sha256'].items():
            self.assertEqual(sha(Path(path)), digest)
        self.assertEqual(result['device_actions'], 0)

if __name__ == '__main__':
    unittest.main()
