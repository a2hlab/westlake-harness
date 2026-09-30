#!/usr/bin/env python3
import json,unittest
from pathlib import Path
from rules_installer_background import detect
from scan_installer_background import backtest
HERE=Path(__file__).resolve().parent

def activity(name,line=1,tag='activity',target=None,enabled='true'):
    return {'class':name,'line':line,'tag':tag,'target':target,'attrs':{'enabled':enabled}}
def manifest(name,line=1):return {'launchers':[{'class':name.replace('/','.'),'line':line}]}

class Rules(unittest.TestCase):
    def test_alias_resolution_is_not_secondary_launch(self):
        nodes=[activity('app/Icon',1,'activity-alias','app/Main'),activity('app/Main',2)]
        r=detect(manifest('app/Icon'),nodes,permission='absent')
        self.assertEqual(r['launchers'],['app/Main']);self.assertEqual(len(r['launcher_aliases']),1)
        self.assertFalse(r['static_risk'])

    def test_splash_and_handler_are_candidates_not_execution_proof(self):
        for name in ['app/SplashActivity','app/IntentHandler']:
            r=detect(manifest(name),[activity(name),activity('app/MainActivity',2)],permission='absent')
            self.assertTrue(r['manifest_risk']);self.assertEqual(r['strength'],'candidate')
            self.assertEqual(r['status'],'conditional-installer-wall')
        self.assertFalse(detect(manifest('app/SplashActivity'),[activity('app/SplashActivity'),activity('app/MainActivity',2,enabled='false')])['static_risk'])

    def test_explicit_target_and_installer_gate(self):
        nodes=[activity('app/Main'),activity('app/Intro',2)]
        calls=[{'method':'app/Main.onCreate()V','dex':'classes.dex','line':42,'non_launcher_targets':['app/Intro'],'startup_reachable':'conditional-static'}]
        for permission,status in [('absent','conditional-installer-wall'),('granted','permission-requirement-satisfied'),('unknown','requires-installer-grant-check')]:
            r=detect(manifest('app/Main'),nodes,calls,permission)
            self.assertEqual(r['status'],status);self.assertEqual(r['strength'],'explicit-startup-target')
        calls[0]['non_launcher_targets']=['app/Main']
        self.assertFalse(detect(manifest('app/Main'),nodes,calls)['static_risk'])

    def test_evaluation_uses_trace_identity_and_no_negative_invention(self):
        rows=[{'key':'a','apk_sha256':'same','static_risk':True,'manifest_risk':False,'strength':'candidate'}, {'key':'b','apk_sha256':'same','static_risk':True,'manifest_risk':True,'strength':'candidate'}]
        truth={'rows':[{'key':k,'new_apk_sha256':'same','comparison_identity_verified':True,'new_background_denials':[{}] if k=='a' else []} for k in ['a','b']]}
        r=backtest(rows,truth)['combined'];self.assertEqual(r['hits'],1);self.assertEqual(r['misses'],0);self.assertEqual(r['additional_alerts_without_observed_denial'],1)
        rows[0]['apk_sha256']='changed'
        with self.assertRaisesRegex(ValueError,'APK mismatch'):backtest(rows,truth)

class Inventory(unittest.TestCase):
    def test_known_answers_and_coverage(self):
        rows=json.loads((HERE/'installer-background-r17p/matrix.json').read_text());by={r['key']:r for r in rows}
        self.assertEqual(len(rows),66);self.assertEqual(len(by),66)
        self.assertEqual(by['subwaysurfers']['status'],'unknown-input')
        self.assertTrue(by['anki']['manifest_risk'])
        self.assertTrue(by['wikipedia']['launcher_aliases']);self.assertEqual(by['wikipedia']['strength'],'explicit-startup-target')
        result=json.loads((HERE/'installer-background-r17p/results.json').read_text())
        self.assertEqual((result['combined']['hits'],result['combined']['misses']),(14,0))
        self.assertEqual((result['manifest_only']['hits'],result['manifest_only']['misses']),(3,11))
        self.assertEqual(result['combined']['additional_alerts_without_observed_denial'],18)
        from scan_installer_background import scan
        entries=json.loads((HERE.parent/'2026-09-30-v3c-r17j-prospective/freezes/v2/predictions.json').read_text())
        self.assertEqual([scan(e,'absent') for e in entries],rows)

if __name__=='__main__':unittest.main()
