#!/usr/bin/env python3
import copy,csv,json,tempfile,unittest
import hashlib
from pathlib import Path
from detector import inspect_method,resolve_intent,classify,HERE
from backtest import score,verify_freeze

class PredictionTests(unittest.TestCase):
    def test_bglaunch_backtest(self):
        root=HERE/'backtests/v0-bglaunch-5ea'
        stored=json.loads((root/'results.json').read_text())
        observations=json.loads((root/'observations.json').read_text())
        receipt=verify_freeze(HERE/'freezes/v0')
        predictions=[r['prediction'] for r in json.loads((HERE/'freezes/v0/predictions.json').read_text())]
        actual=score(predictions,observations,receipt['frozen_at'],require_pre_intervention=False)
        self.assertEqual(stored['metrics'],actual['metrics'])
        self.assertEqual(actual['metrics']['calibration']['advance']['correct'],4)
        self.assertEqual(actual['metrics']['calibration']['page']['correct'],1)
        self.assertEqual(actual['metrics']['calibration']['page']['scored'],5)
        self.assertIsNone(actual['metrics']['unseen']['page']['accuracy'])
        self.assertEqual(actual['metrics']['unseen']['page']['coverage'],0)
        excluded=json.loads((root/'excluded.json').read_text())
        self.assertEqual([r['observation']['key'] for r in excluded],['wikipedia'])
        captures=alive=processes=0
        for path in (root/'evidence').glob('*/record.json'):
            record=json.loads(path.read_text());uid=str(record['bms']['uid']);found=[]
            for line in (path.parent/'processes-t5.txt').read_text().splitlines():
                fields=line.split()
                if len(fields)>=4 and fields[2]==uid and fields[3] in ('appspawn-x',record['package']):found.append(fields[0])
            alive+=bool(found);processes+=len(found)
            if record['key']=='vlc':self.assertEqual(found,[])
            for shot in record['screenshots']:
                if shot.get('captured') is True:
                    captures+=1
                    self.assertEqual(hashlib.sha256((path.parent/Path(shot['path']).name).read_bytes()).hexdigest(),shot['sha256'])
        self.assertEqual((captures,alive,processes),(14,4,5))
        self.assertEqual(next(x for x in observations if x['key']=='vlc')['advance_observed'],'yes')

    def test_rules(self):
        code=[('0000',1,'new-instance v0, Landroid/content/Intent; // type@0'),('0002',2,'const-class v1, Lapp/MainActivity; // type@1'),('0004',3,'invoke-direct {v0, v2, v1}, Landroid/content/Intent;.<init>:(Landroid/content/Context;Ljava/lang/Class;)V // method@0'),('0007',4,'invoke-virtual {v2, v0}, Landroid/app/Activity;.startActivity:(Landroid/content/Intent;)V // method@1'),('000a',5,'invoke-virtual {v2}, Landroid/app/Activity;.finish:()V // method@2')]
        calls=inspect_method('app/Splash.onCreate(Landroid/os/Bundle;)V','classes.dex',code)
        self.assertEqual(resolve_intent(calls[0]['intent'],{}),(['app/MainActivity'],'explicit-class'))
        self.assertEqual(calls[0]['finish_lexical_order'],'after_start')
        bridge=code[:3]+[('0007',4,'invoke-virtual {v3, v0, v4}, Landroidx/activity/result/ActivityResultLauncher;.launch:(Ljava/lang/Object;Landroidx/core/app/ActivityOptionsCompat;)V // method@1')]
        found=inspect_method('app/Main.onCreate(Landroid/os/Bundle;)V','classes.dex',bridge)[0]
        self.assertEqual(found['dispatch_kind'],'activity-result-bridge')
        self.assertEqual(resolve_intent(found['intent'],{})[0],['app/MainActivity'])
        import scan
        methods={'app/A.onCreate()V':{'edges':[{'target':'app/Base.go()V','kind':'invoke-virtual'}]},'app/B.go()V':{'edges':[]},'app/C.go()V':{'edges':[]}}
        roots=[{'method':'app/A.onCreate()V','category':'launcher_activity'}]
        for parents in [{'app/B':'app/Base'},{'app/B':'app/Base','app/C':'app/Base'}]:
            old_paths,old_unresolved,_=scan.ORIGINAL_PATHS(methods,parents,{},roots)
            new_paths,new_unresolved,_=scan.lifecycle_paths(methods,parents,{},roots)
            self.assertEqual(old_paths,new_paths);self.assertEqual(old_unresolved,new_unresolved)

        branch=code[:3]+[('0006',9,'if-eqz v2, 0007 // +1')]+code[3:]
        self.assertEqual(resolve_intent(inspect_method('app/Splash.onCreate(Landroid/os/Bundle;)V','classes.dex',branch)[0]['intent'],{}),([], 'unknown'))
        self.assertEqual(resolve_intent({'kind':'factory','method':'a.f()Landroid/content/Intent;'},{'a.f()Landroid/content/Intent;':[{'kind':'intent','target':'app/MainActivity'}]})[0],['app/MainActivity'])
        self.assertEqual(resolve_intent({'kind':'factory','method':'a.f()Landroid/content/Intent;'},{'a.f()Landroid/content/Intent;':[None]})[0],[])
        self.assertEqual(classify('fd-gallery',[],'scanned')['tier'],'screen_likely')
        self.assertEqual(classify('unknown-app',[],'scanned')['expected_advance'],'unknown')
        self.assertEqual(classify('fd-gallery',[],'unknown')['expected_page'],'unknown')
        p={'key':'a','apk_sha256':'exact','expected_advance':'yes','expected_page':'yes','calibration':False}
        good={'key':'a','apk_sha256':'exact','grant_verified':True,'clicked_at':'2026-09-30T04:00:00+08:00','intervention_at':'2026-09-30T03:00:00+08:00','advance_observed':'yes','predicted_page_observed':'yes','transition_evidence':'hilog:42','screenshot_evidence':'shot.jpeg','comparable_profile':True}
        frozen='2026-09-30T02:00:00+08:00'
        self.assertEqual(score([p],[good],frozen)['metrics']['unseen']['page']['accuracy'],1.0)
        for field,value,reason in [('grant_verified',False,'grant_not_verified'),('apk_sha256','other','apk_identity_mismatch'),('clicked_at',frozen,'not_strictly_post_freeze'),('intervention_at','2026-09-30T01:00:00+08:00','freeze_not_before_intervention')]:
            changed=dict(good,**{field:value});result=score([p],[changed],frozen)
            self.assertEqual(result['metrics']['all']['page']['scored'],0);self.assertIn(reason,result['rows'][0]['reasons'])
        no_shot=dict(good,screenshot_evidence=None)
        self.assertEqual(score([p],[no_shot],frozen)['metrics']['all']['page']['known_outcomes'],0)
        with self.assertRaisesRegex(ValueError,'duplicate'):score([p],[good,good],frozen)

    def test_freeze(self):
        freezes=sorted((HERE/'freezes').iterdir())
        self.assertTrue(freezes)
        for root in freezes:
            receipt=verify_freeze(root);rows=json.loads((root/'predictions.json').read_text());preds=[r['prediction'] for r in rows]
            self.assertEqual(receipt['keys'],66);self.assertEqual(len({p['key'] for p in preds}),66)
            self.assertFalse(receipt['post_intervention_results_read'])
            self.assertEqual(sum(p['calibration'] for p in preds),6)
            self.assertEqual(next(p for p in preds if p['key']=='subwaysurfers')['scan_status'],'unknown')
            for row in rows:
                if row['prediction']['apk_sha256'] is None:
                    self.assertTrue(receipt['initial_calibration_only']);self.assertEqual(row['prediction']['expected_advance'],'unknown')
                else:self.assertEqual(len(row['prediction']['apk_sha256']),64)
                if row['static_detection_independent_of_calibration']:
                    self.assertTrue(any(c['startup_reachable']=='yes-static' and c['non_launcher_targets'] for c in row['selected_witnesses']))
                if not receipt['initial_calibration_only']:
                    evidence=(root/row['prediction']['evidence']).resolve()
                    self.assertEqual(hashlib.sha256(evidence.read_bytes()).hexdigest(),row['prediction']['evidence_sha256'])
            if not receipt['initial_calibration_only']:
                self.assertEqual(sum(p['scan_status']=='scanned' for p in preds),65)
                wiki=next(r for r in rows if r['prediction']['key']=='wikipedia')
                self.assertTrue(any(c['dispatch_kind']=='activity-result-bridge' and 'org/wikipedia/onboarding/InitialOnboardingActivity' in c['non_launcher_targets'] for c in wiki['selected_witnesses']))
            with tempfile.TemporaryDirectory() as tmp:
                dest=Path(tmp)
                for f in root.rglob('*'):
                    if f.is_file():
                        target=dest/f.relative_to(root);target.parent.mkdir(parents=True,exist_ok=True);target.write_bytes(f.read_bytes())
                (dest/'predictions.csv').write_text('tampered')
                with self.assertRaisesRegex(ValueError,'changed'):verify_freeze(dest)
if __name__=='__main__':unittest.main()
