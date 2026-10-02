import copy
import hashlib
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

HERE=Path(__file__).resolve().parent
sys.path.insert(0,str(HERE))
import process_selftest as probe
import promotion_hook_u13 as hook
import observe
from unittest.mock import patch

GOOD='10-03 02:00:00.001 123 124 I C00f00/AppSpawnXJava: [stderr] [WL-KS-PROBE] validateAead(random 256-bit SecretKeySpec)=OK'
BAD='10-03 02:00:00.002 123 124 I C00f00/AppSpawnXJava: [stderr] [WL-KS-PROBE] selftest error: java.lang.IllegalStateException: GCM cipher needs to be initialised'

class DraftTests(unittest.TestCase):
    def test_actual_archived_both_poles(self):
        for name, errors in [('u12-error',1),('u101t8-zero',0)]:
            row=probe.run_row(HERE/'evidence/known-answer'/name/'record.json')
            self.assertEqual(row['selftest_error_count'],errors)
            self.assertEqual(row['status'],'REJECT')
            self.assertEqual(row['badtag_count'],1 if name=='u101t8-zero' else 0)

    def test_shard_observer_records_rejection_and_returns_zero(self):
        with tempfile.TemporaryDirectory() as d, patch.object(observe,'ack') as ack, patch('builtins.print'):
            plan={'entry':'90','lane':'cx-t0','serial':'test'}
            root=HERE/'evidence/known-answer/u12-error'
            out=Path(d)/'assessment.json'
            data=observe.assess(plan,root,out,'test')
            self.assertEqual(data['selftest_error_count'],1)
            self.assertTrue(out.exists());self.assertIn('selftest error',ack.call_args.args[1])
            self.assertIn('record-only',ack.call_args.args[1])

    def test_longwait_disabled_and_cutoff_no_device(self):
        plan=json.loads((HERE/'plan-61b.json').read_text())
        with tempfile.TemporaryDirectory() as d, patch.object(observe.subprocess,'run') as run:
            with self.assertRaisesRegex(ValueError,'disabled'):observe.longwait(plan,Path(d),0)
            run.assert_not_called()
        plan['execution_enabled']=True;plan['bundle_sha256']='a'*64
        with tempfile.TemporaryDirectory() as d, patch.object(observe,'ack'), patch.object(observe.subprocess,'run') as run:
            self.assertEqual(observe.longwait(plan,Path(d),0),0);run.assert_not_called()
            rows=json.loads((Path(d)/'longwait-result.json').read_text())
            self.assertEqual(len(rows),2);self.assertTrue(all(r['status']=='unknown' for r in rows))

    def test_longwait_commands_keep_validated_capture_flags(self):
        plan=json.loads((HERE/'plan-61b.json').read_text())
        spec=json.loads((HERE/'longwait-61b.json').read_text())
        argv=observe.capture_command(plan,spec['observations'][0],Path('/tmp/fresh'),123)
        for flag,value in [('--wait','95'),('--hilog','95'),('--shots','20,45,90')]:
            self.assertEqual(argv[argv.index(flag)+1],value)
        self.assertNotIn('lock',argv);self.assertNotIn('unlock',argv)
        other=dict(spec['observations'][0],input_root='$WORKSPACES/westlake-inputs/corpus-v2/app-inputs')
        argv=observe.capture_command(plan,other,Path('/tmp/fresh'),123)
        self.assertNotIn('$WORKSPACES',argv[argv.index('--input-root')+1])

    def test_both_badtag_formats_reject_even_with_success(self):
        for message in ['selftest AEADBadTagException via default provider BC (ivLen=16) -> REPRODUCES the on-board root',
                        'validateAead AEADBadTagException -> REPRODUCED the on-board root']:
            line=BAD[:BAD.index('selftest error')]+message
            row=probe.scan_text(line+'\n'+GOOD,['123'])['123']
            self.assertEqual(row['status'],'REJECT');self.assertEqual(len(row['badtag_errors']),1)
            self.assertEqual(len(row['selftest_errors']),0)

    def test_probe_error_is_separate_failure(self):
        row=probe.scan_text(BAD.replace('selftest error:','probe error:')+'\n'+GOOD,['123'])['123']
        self.assertEqual(row['status'],'REJECT');self.assertEqual(len(row['probe_errors']),1)
        self.assertEqual(len(row['selftest_errors']),0);self.assertEqual(len(row['badtag_errors']),0)

    def test_success_formats_v3(self):
        for message in ['selftest validateAead(random 256-bit SecretKeySpec)=OK','validateAead round-trip=OK','validateAead=OK']:
            row=probe.scan_text(BAD[:BAD.index('selftest error')]+message,['123'])['123']
            self.assertEqual(row['status'],'PASS');self.assertEqual(probe.errors(row),[])

    def test_report_three_failure_counts(self):
        with tempfile.TemporaryDirectory() as d:
            root=Path(d);(root/'record.json').write_text(json.dumps({'key':'k','bms':{'uid':100},'diagnostics':{'complete':True}}))
            (root/'processes-t20.txt').write_text('123 1 100 appspawn-x')
            (root/'hilog.txt').write_text('\n'.join([BAD,BAD.replace('selftest error:','probe error:'),BAD[:BAD.index('selftest error')]+'validateAead AEADBadTagException -> REPRODUCED']))
            data=probe.report(root)
            self.assertEqual([data[k] for k in ('selftest_error_count','badtag_count','probe_error_count','error_count','error_runs')],[1,1,1,3,1])
            self.assertFalse(data['passed']);self.assertEqual(data['schema_version'],2)

    def test_success_actual_marker_shape(self):
        self.assertEqual(probe.scan_text(GOOD,['123'])['123']['status'],'PASS')
    def test_error_even_when_success_present(self):
        row=probe.scan_text(GOOD+'\n'+BAD,['123'])['123']
        self.assertEqual(row['status'],'REJECT');self.assertEqual(len(row['selftest_errors']),1)
    def test_silence_is_unknown(self):
        self.assertEqual(probe.scan_text('', ['123'])['123']['status'],'unknown')
    def test_pid_scope_excludes_other_process(self):
        row=probe.scan_text(BAD.replace('123 124','999 998')+'\n'+GOOD,['123'])['123']
        self.assertEqual(row['status'],'PASS');self.assertEqual(row['selftest_errors'],[])
    def test_old_baseline_badtag_is_known_failure(self):
        line=BAD.replace('selftest error: java.lang.IllegalStateException: GCM cipher needs to be initialised','selftest AEADBadTagException via default provider BC (ivLen=16)')
        row=probe.scan_text(line,['123'])['123'];self.assertEqual(row['selftest_errors'],[]);self.assertEqual(row['status'],'REJECT');self.assertEqual(len(row['badtag_errors']),1)
    def test_no_records_cannot_pass(self):
        with tempfile.TemporaryDirectory() as d:self.assertFalse(probe.report(Path(d))['passed'])
    def test_actual_u12_negative_capture_if_available(self):
        root=HERE.parents[1]/'benchmark/2026-10-02-u12-final-assembly/window4/u12-A4-20261003T002941/61b/runner/listmaker-1'
        files=list(root.glob('*/*/*/record.json'))
        if not files:self.skipTest('raw U12 capture unavailable; synthetic known answer still enforced')
        row=probe.run_row(files[0]);self.assertEqual(row['status'],'REJECT');self.assertGreater(row['selftest_error_count'],0)
    def test_disabled_sha_slots(self):
        for name in ['5ea','5cd','61b']:
            p=json.loads((HERE/f'plan-{name}.json').read_text())
            self.assertFalse(p['execution_enabled']);self.assertFalse(p['rollout_ready'])
            self.assertIsNone(p['bundle_sha256']);self.assertIsNone(p['package_manifest_sha256'])
            self.assertEqual(p['restore']['state'],'U10.1T8');self.assertTrue(p['restore']['unconditional'])
            self.assertEqual(p['regression_gate']['lit_required'],122)
    def test_longwait_six_balanced_observations(self):
        keys=[]
        for b in ['5ea','5cd','61b']:
            p=json.loads((HERE/f'longwait-{b}.json').read_text());self.assertFalse(p['execution_enabled'])
            self.assertEqual(len(p['observations']),2);self.assertFalse(p['regression_evidence'])
            keys+=p['keys']
            for row in p['observations']:
                self.assertEqual(row['runs'],1);self.assertIn('20,45,90',row['flags']);self.assertIn('95',row['flags'])
        self.assertEqual(set(keys),{'cv2-com-frequent-habits','fd-im-vector-app','fd-libretube','fd-plus','mcdonalds','toutiao'})
    def test_guard_refuses_even_if_flags_toggled(self):
        p=subprocess.run([sys.executable,str(HERE/'draft_guard.py'),'apply','--plan',str(HERE/'plan-61b.json')],capture_output=True,text=True)
        self.assertEqual(p.returncode,3);self.assertIn('no device/lock',p.stdout)
    def test_complete_166_and_six_consecutive_lottery(self):
        composition=json.loads((HERE/'composition.json').read_text());seen=set();runs=0
        for b in ['5ea','5cd','61b']:
            p=json.loads((HERE/f'plan-{b}.json').read_text());flat=[]
            for s in p['shards']:
                keys=(HERE/'keys'/b/Path(s['keys_file']).name).read_text().split();flat+=keys
            seen.update(flat);runs+=len(flat)+2
            for key in composition['boards'][b]['lottery_keys']:
                positions=[i for i,k in enumerate(flat) if k==key]
                self.assertEqual(len(positions),6);self.assertEqual(positions,list(range(positions[0],positions[0]+6)))
        self.assertEqual(len(seen),166);self.assertEqual(runs,192)

class CriterionTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.addCleanup(self.temp.cleanup)
        self.report=Path(self.temp.name)/'selftest.json'
        self.rows={'schema_version':2,'runs':[{'record':'r1','status':'PASS','validateAead_OK_count':1,'processes':{'123':{'status':'PASS','validateAead_OK':[{'line':'OK'}],'selftest_errors':[],'badtag_errors':[],'probe_errors':[]}}}], 'run_count':1}
        self.reference={'keys':{str(i):{'verdict':'lit'} for i in range(122)},'total_lit':122}
        self.comp={'bundle_sha256':'a'*64,'native_manifest_sha256':'b'*64}
        self.decision={'signed_by':'outer(claude)','bundle_sha256':'a'*64,'native_manifest_sha256':'b'*64,'confirmed_regressions':[],
          'stage_A_regression_verdict':{'u13_reference_lit_total':122,'measured':122,'same_or_lit_within_k_of_n':122,'confirmed_regressions':0}}
    def evaluate(self):
        self.report.write_text(json.dumps(self.rows))
        self.decision['process_selftest_gate']={'report_sha256':hashlib.sha256(self.report.read_bytes()).hexdigest(),'measured_records':['r1']}
        return hook.retention_reason(self.decision,self.comp,self.reference,{'passed':True},self.report)
    def test_all_failure_classes_hard_veto_even_with_forged_pass(self):
        for category in ('selftest_errors','badtag_errors','probe_errors'):
            self.rows['runs'][0]['processes']['123'][category]=[{'line_sha256':'c'*64}]
            self.assertIn('unconditionally rejects',self.evaluate())
            self.rows['runs'][0]['processes']['123'][category]=[]

    def test_obsolete_report_rejected(self):
        self.rows.pop('schema_version');self.assertIn('obsolete',self.evaluate())

    def test_one_silent_process_requires_its_own_explanation(self):
        self.rows['runs'][0]['processes']['456']={'status':'unknown','validateAead_OK':[]}
        self.assertIn('individual outer explanations',self.evaluate())

    def test_122_and_zero_error_pass(self):self.assertIsNone(self.evaluate())
    def test_old_116_certificate_rejected(self):
        self.decision['stage_A_regression_verdict']['measured']=116
        self.assertIn('must be measured',self.evaluate())
    def test_unknown_blocked(self):
        self.rows['runs'][0]['status']='unknown'
        self.assertIn('individual outer explanations',self.evaluate())
    def test_errors_blocked_even_if_ui_preserved(self):
        self.rows['runs'][0]['status']='REJECT';self.rows['runs'][0]['processes']['123']['selftest_errors']=[{'line_sha256':'c'*64}]
        self.assertIn('unconditionally rejects',self.evaluate())
    def test_wrong_bundle_rejected(self):
        self.decision['bundle_sha256']='d'*64;self.assertIn('another bundle',self.evaluate())
    def test_silent_report_not_promotion(self):
        self.rows={'schema_version':2,'runs':[],'run_count':0};self.assertIn('coverage absent',self.evaluate())

if __name__=='__main__':unittest.main()
