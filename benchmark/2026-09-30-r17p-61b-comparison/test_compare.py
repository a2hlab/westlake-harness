#!/usr/bin/env python3
import json,tempfile,unittest
from pathlib import Path
import compare as c

class Rules(unittest.TestCase):
    def test_permission_evidence(self):
        with tempfile.TemporaryDirectory() as t:
            p=Path(t)/'bundle.txt'
            self.assertEqual(c.permission_state(p,c.PERMS['background']),'unknown')
            p.write_text('pkg:\n'+json.dumps({'reqPermissions':[],'reqPermissionStates':[]}))
            self.assertEqual(c.permission_state(p,c.PERMS['background']),'absent')
            p.write_text(json.dumps({'reqPermissions':[c.PERMS['background']],'reqPermissionStates':[0]}))
            self.assertEqual(c.permission_state(p,c.PERMS['background']),'granted')
            p.write_text(json.dumps({'reqPermissions':[c.PERMS['background']],'reqPermissionStates':[]}))
            self.assertEqual(c.permission_state(p,c.PERMS['background']),'unknown')

    def test_counts_exclude_helpers_and_never_infer_ui(self):
        with tempfile.TemporaryDirectory() as t:
            p=Path(t);shot=p/'t5.jpeg';shot.write_bytes(b'fixture, not real UI')
            rec=p/'record.json';rec.write_text(json.dumps({'key':'sample','serial':'61b','boot_id':'boot','package':'pkg','clicked':True,'bms':{'uid':100},'screenshots':[{'path':str(shot),'sha256':c.sha(shot),'captured':True},{'captured':False}]}))
            (p/'processes-t5.txt').write_text('PID PPID UID NAME\n2 1 100 appspawn-x\n3 2 100 sh\n4 1 101 appspawn-x\n')
            f=c.record_facts(rec,{'board':'61b','boot_id':'boot','runtime_fingerprint':'fp'})
            counts=c.count_records([f])
            self.assertEqual(counts['captured'],1);self.assertEqual(counts['captures_verified'],1)
            self.assertEqual(counts['t5']['alive_apps'],1);self.assertEqual(counts['t5']['app_processes'],1)
            self.assertEqual(counts['t5']['same_uid_helpers_excluded'],1)
            self.assertEqual(counts['t20']['unknown_apps'],1);self.assertNotIn('lit',counts)

    def test_installer_effect_is_not_causal(self):
        row={'apk_same':True,'launcher_changed':False,'new_background':'absent','old_background':'granted','new_internet':'absent','old_internet':'granted','new_startability_codes':[2097205]}
        self.assertIn('causal_link_unproven',c.classify_installer(row))
        row['apk_same']=False
        self.assertEqual(c.classify_installer(row),'identity_unknown_or_changed')

class Rejection(unittest.TestCase):
    def test_expected_hash_is_not_prelaunch_identity_proof(self):
        row={'apk_same':True,'new_clicked':False,'new_record_errors':['record_not_clicked']}
        self.assertFalse(c.comparable_identity(row,{'clicked':False}))
        row.update(new_clicked=True,new_record_errors=[])
        self.assertTrue(c.comparable_identity(row,{'clicked':True,'errors':[]}))
        row['apk_same']=False
        self.assertFalse(c.comparable_identity(row,{'clicked':True}))

    def test_pid_isolation(self):
        with tempfile.TemporaryDirectory() as t:
            p=Path(t);rec=p/'record.json';rec.write_text(json.dumps({'key':'a','package':'pkg'}))
            (p/'hilog.txt').write_text('09-30 05:30:00.001 12 12 I tag: nativeOnScheduleLaunchApplication ENTRY bundle=pkg name=x\n09-30 05:30:01.000 99 99 E tag: FATAL EXCEPTION wrong process\n09-30 05:30:02.000 12 12 E tag: StartAbility returned 2097205 (0=success)\n')
            clues=c.extract(rec);self.assertEqual(clues['target_pids'],[12]);self.assertEqual(len(clues['clues']),1);self.assertEqual(clues['clues'][0]['line'],3)
            self.assertEqual(clues['startability_returns'][0]['code'],2097205)

    def test_async_denial_requires_target_and_trace(self):
        with tempfile.TemporaryDirectory() as t:
            p=Path(t);rec=p/'record.json';rec.write_text(json.dumps({'key':'a','package':'pkg'}))
            lines=[
                '09-30 05:30:00.001 12 12 I tag: nativeOnScheduleLaunchApplication ENTRY bundle=pkg name=x',
                '09-30 05:30:00.002 12 12 I tag: nativeStartAbility: bundle=pkg, ability=pkg.Next, action=',
                '09-30 05:30:00.003 888 888 I AMS: [abcdef1234567, 123, 0] NotifySCBPendingActivation for callerSession, target: pkg.NextrequestId:',
                '09-30 05:30:00.004 12 12 I tag: StartAbility returned 0 (0=success)',
                '09-30 05:30:00.005 1945 1945 W WMS: [abcdef1234567, 321, 0] DisallowActivationFromPendingBackground: no permission to start ability from Background, id:286',
                '09-30 05:30:00.006 1945 1945 W WMS: [fffffffffffff, 321, 0] DisallowActivationFromPendingBackground: no permission to start ability from Background, id:287']
            (p/'hilog.txt').write_text('\n'.join(lines))
            result=c.extract(rec)
            self.assertEqual(result['startability_returns'][0]['code'],0)
            self.assertEqual(len(result['background_denials']),1)
            self.assertEqual(result['background_denials'][0]['line'],5)

    def test_unfinished_and_disagreeing_summary(self):
        with tempfile.TemporaryDirectory() as t:
            p=Path(t);self.assertFalse(c.coverage(p,['a'])['complete'])
            with self.assertRaisesRegex(ValueError,'refuse final incomplete'):
                c.build(p,p/'refused-output')
            self.assertFalse((p/'refused-output').exists())
            (p/'summary.json').write_text(json.dumps({'records':[{'key':'a','status':'done'}]}))
            (p/'facts.txt').write_text('fixture');(p/'a').mkdir();(p/'a/record.json').write_text(json.dumps({'key':'a','status':'other'}))
            self.assertIn('summary_record_disagrees:a',c.coverage(p,['a'])['reason'])
            (p/'a/record.json').write_text(json.dumps({'key':'a','status':'done'}))
            self.assertTrue(c.coverage(p,['a'])['complete'])
            self.assertFalse(c.coverage(p,['a','b'])['complete'])

class Handoff(unittest.TestCase):
    def test_complete_pending_visual_review(self):
        result=json.loads((c.HERE/'final/results.json').read_text())
        self.assertTrue(result['complete']);self.assertEqual(len(result['rows']),66)
        self.assertEqual(result['same_profile_denominator'],0);self.assertIsNone(result['same_profile_accuracy'])
        self.assertEqual(result['visual_status'],'pending_outer_review')
        self.assertTrue(all(r['new_lit'] in ('pending_outer_review','not_observed_prelaunch') for r in result['rows']))
        self.assertTrue(all(not r['same_profile_score_eligible'] for r in result['rows']))
        c.pa.context()

if __name__=='__main__':unittest.main()
