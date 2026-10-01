import copy
import importlib.util
import json
from pathlib import Path
import sys
import unittest

import score

HERE=Path(__file__).resolve().parent
V2=score.ROOT/'benchmark/2026-10-01-corpus-v2/apk-scan-v2'
sys.path.insert(0,str(V2))
import rules
import collect


def version_two():
    spec=importlib.util.spec_from_file_location('cv2_v2_report',V2/'report.py')
    module=importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def arguments():
    return [
        (score.V1/'PREDICTIONS.csv').read_bytes(),
        json.loads((score.V1/'FREEZE.json').read_text()),
        json.loads((HERE/'outer-signoff.json').read_text()),
        json.loads((HERE/'run-evidence.json').read_text()),
        json.loads((score.V1/'results.json').read_text())]


class IdentityTests(unittest.TestCase):
    def test_changed_csv(self):
        inputs=arguments()
        inputs[0]+=b'\n'
        with self.assertRaisesRegex(ValueError,'CSV SHA'):
            score.score(*inputs)

    def test_duplicate_missing_and_wrong_keys(self):
        for mode in ['duplicate','missing','wrong-key']:
            inputs=arguments()
            if mode=='duplicate':
                inputs[2]['keys'][-1]=copy.deepcopy(inputs[2]['keys'][0])
            elif mode=='missing':
                inputs[2]['keys'].pop()
            else:
                inputs[2]['keys'][0]['key']='unrecognized-key'
            with self.assertRaises(ValueError):
                score.score(*inputs)

    def test_identity_and_screenshot_missing(self):
        for field in ['apk_sha256','version_code','screenshot']:
            inputs=arguments()
            inputs[3]['rows'][0][field]=None
            with self.assertRaises(ValueError):
                score.score(*inputs)

    def test_unknown_class(self):
        with self.assertRaisesRegex(ValueError,'class'):
            score.confusion([dict(predicted_t20='own-ui',observed_t20='READY')])


class ConfusionTests(unittest.TestCase):
    def test_exact_six_classes(self):
        result=score.generate()
        self.assertEqual(result['confusion']['own-ui'],dict(zip(score.VERDICTS,[54,2,3,0,14,0])))
        self.assertEqual(result['confusion']['unknown'],dict(zip(score.VERDICTS,[11,0,0,2,13,1])))
        self.assertEqual(sum(sum(row.values()) for row in result['confusion'].values()),100)
        self.assertTrue(result['late_freeze'])

    def test_abstention_not_negative_and_fallback_separate(self):
        result=score.generate()
        self.assertIsNone(result['metrics']['false_negative'])
        self.assertIsNone(result['metrics']['true_negative'])
        self.assertIsNone(result['metrics']['binary_accuracy'])
        self.assertEqual(result['metrics']['functional_positive_precision'],dict(numerator=54,denominator=73))
        self.assertEqual(result['metrics']['own_ui_positive_precision'],dict(numerator=56,denominator=73))
        self.assertEqual(result['metrics']['abstention_functional_lit'],11)


class FeedbackTests(unittest.TestCase):
    def test_exact_content_not_utility(self):
        self.assertTrue(rules.webview_content('Landroid/webkit/WebView;','loadUrl'))
        self.assertFalse(rules.webview_content('Landroid/webkit/MimeTypeMap;','getSingleton'))
        self.assertFalse(rules.webview_content('Landroid/webkit/WebSettings;','setJavaScriptEnabled'))
        self.assertFalse(rules.webview_content('Lsome/package/WebView;','loadUrl'))
        text='000000: |[000000] app.Main.onCreate:(Landroid/os/Bundle;)V\n000006: |0003: invoke-virtual {v0, v1}, Landroid/webkit/WebView;.loadUrl:(Ljava/lang/String;)V // method@0001\n000009: |0006: invoke-static {}, Landroid/webkit/MimeTypeMap;.getSingleton:()Landroid/webkit/MimeTypeMap; // method@0002'
        hits=collect.inspect_text(text,'classes.dex')
        self.assertEqual(len(hits),1)
        self.assertEqual(hits[0]['examples'][0]['line'],2)

    def test_startup_transition_and_koin_not_all_service_alerts(self):
        row=dict(key='fixture',package='example',apk_sha256='a'*64,t20='own-ui',first_wall_candidates=[])
        precise=dict(package='example',apk_sha256='a'*64,webview_content=[])
        for family,startup,expected in [('secondary-activity-window-session',1,'unknown'),('koin-init-or-use',1,'unknown'),('koin-init-or-use',0,'own-ui'),('system-service:clipboard',1,'own-ui')]:
            row['first_wall_candidates']=[dict(family=family,startup_occurrences=startup,evidence=[])]
            revised=rules.revise(row,precise)
            self.assertEqual(revised['t20'],'own-ui')
            self.assertEqual(revised['abstention_experiment_t20'],expected)
            self.assertEqual(revised['first_wall'],'unknown')

    def test_real_positive_and_negative_controls(self):
        module=version_two()
        result=module.generate()
        rows={row['key']:row for row in result['rows']}
        for key in ['cv2-com-paultirk-yatoo','cv2-ca-vaults-randomlydie']:
            self.assertIn('webview-content-contract',[candidate['family'] for candidate in rows[key]['candidates']])
        for key in ['cv2-org-secuso-privacyfriendlymemory','cv2-org-secuso-privacyfriendlyyahtzeedicer']:
            self.assertIn('startup-activity-transition-contract',[candidate['family'] for candidate in rows[key]['candidates']])
        self.assertIn('startup-koin-contract',[candidate['family'] for candidate in rows['cv2-com-better-alarm']['candidates']])
        self.assertEqual(rows['cv2-com-page-bizzle']['t20'],'own-ui')
        self.assertEqual(rows['cv2-com-page-bizzle']['candidates'],[])
        precise=module.load(V2/'precise-profile.json.gz.b64')
        app=next(app for app in precise['apps'] if app['package']=='org.secuso.privacyfriendlymemory')
        self.assertEqual(app['webview_content'],[])
        for key in ['cv2-com-omgodse-notally','cv2-com-benny-pxerstudio','cv2-com-asdoi-timetable','cv2-org-secuso-privacyfriendly2048']:
            self.assertTrue(rows[key]['candidates'])
            self.assertEqual(rows[key]['t20'],'own-ui')


class ReplayTests(unittest.TestCase):
    def test_scoring_replays(self):
        result=score.generate()
        self.assertEqual(json.loads((HERE/'SCORING.json').read_text()),result)
        self.assertEqual((HERE/'SCORING.csv').read_text(),score.csv_text(result))
        self.assertEqual(sum(bool(row['run_evidence']['screenshot']) for row in result['rows']),99)

    def test_retrospective_static_replays_and_old_freeze_intact(self):
        module=version_two()
        result=module.generate()
        self.assertEqual(json.loads((V2/'results.json').read_text()),result)
        self.assertEqual((V2/'PREDICTIONS.csv').read_text(),module.csv_text(result))
        self.assertEqual(score.digest((score.V1/'PREDICTIONS.csv').read_bytes()),score.CSV_SHA)
        self.assertTrue(all(row['t20']==row['v1_t20'] for row in result['rows']))

    def test_feedback_ablation_replays(self):
        import feedback
        result=feedback.generate()
        self.assertEqual(json.loads((HERE/'FEEDBACK.json').read_text()),result)
        self.assertFalse(result['abstention_experiment']['promoted'])
        self.assertEqual(result['abstention_experiment']['lost_positive_functional_ui'],27)
        self.assertEqual(result['abstention_experiment']['functional_precision'],dict(numerator=27,denominator=38))


if __name__=='__main__':
    unittest.main()
