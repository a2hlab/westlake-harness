import hashlib
import json
from pathlib import Path
import sys
import tempfile
import unittest

HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[1]
sys.path.insert(0,str(HERE))
import build as report
sys.path.insert(0,str(ROOT/'benchmark/2026-09-29-static-wall-prediction'))
from scan_classes_v3 import jar_classes


def read(name):return json.loads((HERE/name).read_text())
def verify_pins(base,pins):
    errors=[]
    for name,wanted in pins.items():
        p=base/name
        if not p.is_file() or report.sha(p)!=wanted:errors.append(name)
    return errors

class EligibilityTests(unittest.TestCase):
    def test_independent_blob_and_evidence(self):
        audits=read('audit.json');by={r['candidate']:r for r in audits}
        good=by['JarVerificationProviderFix'];held=by['AlarmVibratorFetcher']
        self.assertTrue(good['eligible']);self.assertFalse(held['eligible'])
        self.assertTrue(good['source_blob_matches']);self.assertTrue(held['source_blob_matches'])
        self.assertFalse(held['independent_single_fix_file'])
        self.assertTrue(all(r['id_collision'] for r in audits))
        for row in audits:
            self.assertGreaterEqual(len(set(row['packages'])),2)
            for e in row['evidence']:
                a=e['after'];lines=(report.W/a['log']).read_text(errors='replace').splitlines()
                self.assertFalse(a['negative_failure_hits'])
                for hit in a['positive_hits']:
                    self.assertEqual(lines[hit['line']-1],hit['text'])
                    self.assertIn(hit['text'].split()[2],a['pids'])
                record=json.loads((report.W/a['record']).read_text())
                self.assertTrue(any(x['captured'] is True and x.get('scheduled_seconds')==20 and x['sha256']==report.sha(report.W/a['t20']) for x in record['screenshots']))
            self.assertTrue(all(x['source_sha_matches'] and x['helper_emitted'] for x in row['build_carriage']))
        proposal=read('registration-proposal.json')['entries']
        self.assertEqual(len(proposal),1);self.assertEqual(proposal[0]['id'],'FZ-004')
        self.assertEqual(report.check_frozen.validate(proposal),[])
        lines,bad=report.check_frozen.check_sources(proposal,report.WALLS)
        self.assertEqual(bad,0,lines)

    def test_threshold_negative_controls(self):
        self.assertTrue(report.admission(True,True,['a','b'],['a']))
        for args in [(False,True,['a','b'],['a']), (True,False,['a','b'],['a']), (True,True,['a','a'],['a']), (True,True,['a','b'],[])]:
            self.assertFalse(report.admission(*args))

class ContractTests(unittest.TestCase):
    def test_actual_dex_union_and_native_string(self):
        gap=read('webview-contract-gap.json');definitions=set()
        for row in gap['jars']:
            path=report.W/row['path'];self.assertEqual(report.sha(path),row['sha256'])
            definitions.update(x['class'] for x in jar_classes(path))
        self.assertNotIn(gap['required_class'],definitions)
        self.assertIn('adapter/core/WestlakeWebViewInstall',definitions)
        self.assertIn('android/webkit/WebViewFactory',definitions)
        native=report.W/gap['native']['path'];data=native.read_bytes()
        self.assertEqual(report.sha(native),gap['native']['sha256'])
        self.assertEqual(data.find((gap['required_class']+'\0').encode()),gap['native']['required_class_string_offset'])
        tutu=next(r for r in read('predictions.json') if r['key']=='fd-tutanota')
        self.assertEqual(tutu['prediction'],'不变');self.assertFalse(tutu['expected_lit'])
        self.assertFalse(read('profile.json')['provider_declared'])

class PredictionTests(unittest.TestCase):
    def test_complete_cohort_and_separate_functional_predictions(self):
        rows=read('predictions.json');by={r['key']:r for r in rows};self.assertEqual(len(rows),len(by));self.assertEqual(len(by),66)
        plan=json.loads((ROOT/'benchmark/2026-09-30-round1-plan/four-board-v1/shards.json').read_text())
        self.assertEqual(set(by),set(plan['expected_keys']))
        for key,r in by.items():self.assertEqual(r['apk_sha256'],plan['expected_apk_sha256'][key])
        self.assertEqual(sum(r['baseline_lit'] for r in rows),25)
        self.assertEqual([r['key'] for r in rows if r['expected_new_light'] is True],['noice'])
        self.assertTrue(by['newpipe']['expected_lit']);self.assertFalse(by['newpipe']['expected_new_light'])
        self.assertEqual(by['newpipe']['checkpoint_outcome'],'predicted_pass_functional_only')
        self.assertTrue(by['fd-noice']['expected_lit']);self.assertEqual(by['fd-noice']['prediction'],'不变')
        self.assertEqual(by['fd-immich']['prediction'],'不变');self.assertEqual(by['vlc']['prediction'],'不变')
        self.assertTrue(by['subwaysurfers']['apk_changed'])
        self.assertEqual(sum(r['expected_lit'] is None for r in rows),17)
        self.assertEqual(read('profile.json')['native_delta_paths'],len(read('native-delta.json')))

    def test_freeze_integrity_and_mutation_rejection(self):
        self.assertEqual(verify_pins(HERE,read('freeze.json')['files']),[])
        # Source drift is reported instead of silently refreshing a frozen prediction.
        self.assertEqual(verify_pins(report.W,read('source-pins.json')),[])
        with tempfile.TemporaryDirectory() as d:
            p=Path(d)/'source';p.write_text('before');pins={'source':report.sha(p)}
            self.assertEqual(verify_pins(Path(d),pins),[])
            p.write_text('after');self.assertEqual(verify_pins(Path(d),pins),['source'])
            p.unlink();self.assertEqual(verify_pins(Path(d),pins),['source'])
        with self.assertRaisesRegex(SystemExit,'frozen'):report.main()

if __name__=='__main__':unittest.main()
