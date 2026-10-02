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

GOOD='10-03 02:00:00.001 123 124 I C00f00/AppSpawnXJava: [stderr] [WL-KS-PROBE] validateAead(random 256-bit SecretKeySpec)=OK'
BAD='10-03 02:00:00.002 123 124 I C00f00/AppSpawnXJava: [stderr] [WL-KS-PROBE] selftest error: java.lang.IllegalStateException: GCM cipher needs to be initialised'

class DraftTests(unittest.TestCase):
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
    def test_old_baseline_expected_badtag_not_selftest_error(self):
        line=BAD.replace('selftest error: java.lang.IllegalStateException: GCM cipher needs to be initialised','selftest AEADBadTagException via default provider BC (ivLen=16)')
        row=probe.scan_text(line,['123'])['123'];self.assertEqual(row['selftest_errors'],[]);self.assertEqual(row['status'],'unknown')
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
        self.rows={'runs':[{'record':'r1','status':'PASS','validateAead_OK_count':1,'processes':{'123':{'selftest_errors':[]}}}], 'run_count':1}
        self.reference={'keys':{str(i):{'verdict':'lit'} for i in range(122)},'total_lit':122}
        self.comp={'bundle_sha256':'a'*64,'native_manifest_sha256':'b'*64}
        self.decision={'signed_by':'outer(claude)','bundle_sha256':'a'*64,'native_manifest_sha256':'b'*64,'confirmed_regressions':[],
          'stage_A_regression_verdict':{'u13_reference_lit_total':122,'measured':122,'same_or_lit_within_k_of_n':122,'confirmed_regressions':0}}
    def evaluate(self):
        self.report.write_text(json.dumps(self.rows))
        self.decision['process_selftest_gate']={'report_sha256':hashlib.sha256(self.report.read_bytes()).hexdigest(),'measured_records':['r1']}
        return hook.retention_reason(self.decision,self.comp,self.reference,{'passed':True},self.report)
    def test_122_and_zero_error_pass(self):self.assertIsNone(self.evaluate())
    def test_old_116_certificate_rejected(self):
        self.decision['stage_A_regression_verdict']['measured']=116
        self.assertIn('must be measured',self.evaluate())
    def test_unknown_blocked(self):
        self.rows['runs'][0]['status']='unknown'
        self.assertIn('individual outer explanations',self.evaluate())
    def test_errors_blocked_even_if_ui_preserved(self):
        self.rows['runs'][0]['status']='REJECT';self.rows['runs'][0]['processes']['123']['selftest_errors']=[{'line_sha256':'c'*64}]
        self.assertIn('individual outer explanations',self.evaluate())
    def test_wrong_bundle_rejected(self):
        self.decision['bundle_sha256']='d'*64;self.assertIn('another bundle',self.evaluate())
    def test_silent_report_not_promotion(self):
        self.rows={'runs':[],'run_count':0};self.assertIn('coverage absent',self.evaluate())

if __name__=='__main__':unittest.main()
