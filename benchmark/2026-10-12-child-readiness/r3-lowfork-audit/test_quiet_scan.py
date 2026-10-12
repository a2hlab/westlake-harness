#!/usr/bin/env python3
"""Execute the real discovery/guard functions offline; no device or signals."""
from pathlib import Path
import hashlib, importlib.util, json, os, subprocess, tempfile, unittest

D = Path(__file__).resolve().parent
OLD = D.parent
R2 = OLD / 'r2-quiet-scan'
C = D / 'candidate'
S = 'a7a358c60bec293c26531b0eecbf14979f77411c227cec4767742c0c82791a0c'
def sha(p): return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def load(path, name):
    spec = importlib.util.spec_from_file_location(name, path)
    mod = importlib.util.module_from_spec(spec); spec.loader.exec_module(mod)
    return mod

class QuietScanTests(unittest.TestCase):
    def test_batched_json_matches_old_encoder_special_values(self):
        script='''
RB_OWNER_UID=20011206; . "$1"
OD_COUNT=$2
od(){ printf 'od\n' >> "$OD_COUNT"; command od "$@"; }
RB_AUDIT_PHASE=$3; RB_AUDIT_PID=$4; RB_AUDIT_BIRTH=$5
rb_guard_json "$6" "$7" "$8"
'''
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp)
            for values in (['strict','6243','6558','uid','0:0:0:0','20011206'],
                           ['', '', '', 'quote"\\\n\t', 'actual"\\\n', '']):
                outputs=[]
                for index,helper in enumerate((OLD/'r2b-quiet-reset/candidate/route-b-owner.sh',C/'route-b-owner.sh')):
                    count=root/f'count-{index}';count.unlink(missing_ok=True)
                    p=subprocess.run(['bash','-c',script,'fixture',str(helper),str(count),*values],capture_output=True,text=True)
                    self.assertEqual(p.returncode,0,p.stderr)
                    outputs.append(json.loads(p.stderr))
                    self.assertEqual(len(count.read_text().splitlines()),6 if index==0 else 1)
                self.assertEqual(outputs[0],outputs[1])

    def test_encoder_and_output_errors_are_nonzero(self):
        for fault in ('od(){ return 9; }',
                      '''printf(){ [ "$1" != '{"phase":"' ] || return 9; command printf "$@"; }'''):
            script='RB_OWNER_UID=20011206; . "$1"; '+fault+'; rb_guard_json uid actual expected'
            p=subprocess.run(['bash','-c',script,'fixture',str(C/'route-b-owner.sh')],capture_output=True,text=True)
            self.assertEqual(p.returncode,5)

    def scan(self, helper, target=False):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp); proc = root/'proc'; proc.mkdir()
            for pid in range(101, 153):
                p = proc/str(pid); p.mkdir()
                (p/'stat').write_text(f'{pid} (fixture) S 1 '+ ' '.join(['0']*17)+' 500 0\n')
                uid = '20011206' if pid in (151, 152) else '0'
                (p/'status').write_text('Uid:\t'+'\t'.join([uid]*4)+'\n')
                (p/'exe').symlink_to('/data/local/tmp/asx/appspawn-x')
            counter = root/'od-count'
            script = '''
RB_PROC=$1; RB_RUNTIME=/fixture/runtime; RB_OWNER_UID=20011206
. "$2"
OD_COUNT=$3
od(){ printf 'od\n' >> "$OD_COUNT"; command od "$@"; }
# Replay captured executable SHA and private inode tool results; all guard
# functions, real proc-field reads, alias checks, and discovery remain intact.
sha256sum(){ printf '%s  %s\n' "$FIXTURE_SHA" "$1"; }
stat(){ printf '66352:423310\n'; }
rb_owned_pids
if [ "$4" = target ]; then
 [ "${RB_AUDIT_QUIET:-0}" = 0 ] || exit 99
 RB_AUDIT_PID=101; RB_AUDIT_BIRTH=500; RB_AUDIT_PHASE=strict
 rb_owned 101
fi
'''
            p = subprocess.run(['bash','-c',script,'fixture',str(proc),str(helper),str(counter), 'target' if target else 'scan'],
                               env=dict(os.environ,FIXTURE_SHA=S),capture_output=True,text=True)
            calls = len(counter.read_text().splitlines()) if counter.exists() else 0
            return p, calls

    def test_quiet_same_owned_set_zero_od(self):
        old, old_calls = self.scan(OLD/'candidate/route-b-owner.sh')
        new, new_calls = self.scan(C/'route-b-owner.sh')
        self.assertEqual(old.returncode,0,old.stderr)
        self.assertEqual(new.returncode,0,new.stderr)
        self.assertEqual(old.stdout,new.stdout)
        self.assertEqual(new.stdout.splitlines(),['151','152'])
        self.assertEqual(old_calls,300)
        self.assertEqual(new_calls,0)
        self.assertEqual(new.stderr,'')

    def test_target_diagnostics_remain_and_quiet_not_leaked(self):
        p, calls = self.scan(C/'route-b-owner.sh',target=True)
        self.assertEqual(p.returncode,1)
        self.assertEqual(calls,1)
        rows=[json.loads(x) for x in p.stderr.splitlines()]
        self.assertEqual(len(rows),1)
        self.assertEqual(rows[0]['field'],'uid')
        self.assertEqual(rows[0]['actual'],'0:0:0:0')
        self.assertEqual(rows[0]['expected'],'20011206:20011206:20011206:20011206')

    def test_inherited_quiet_flag_cannot_suppress_target_diagnostic(self):
        script = '\n'.join([
            'RB_AUDIT_QUIET=1; export RB_AUDIT_QUIET',
            '. "$1"',
            '[ "$RB_AUDIT_QUIET" = 0 ] || exit 99',
            'RB_AUDIT_PID=101; RB_AUDIT_BIRTH=500; RB_AUDIT_PHASE=strict',
            'rb_deny uid "0:0:0:0" "20011206:20011206:20011206:20011206"',
        ])
        p = subprocess.run(['bash','-c',script,'fixture',str(C/'route-b-owner.sh')],capture_output=True,text=True)
        self.assertEqual(p.returncode,1)
        rows=[json.loads(line) for line in p.stderr.splitlines()]
        self.assertEqual(len(rows),1)
        self.assertEqual(rows[0]['field'],'uid')
        self.assertEqual(rows[0]['actual'],'0:0:0:0')
        self.assertEqual(rows[0]['expected'],'20011206:20011206:20011206:20011206')
        old_script=script.replace('[ "$RB_AUDIT_QUIET" = 0 ] || exit 99','true')
        old = subprocess.run(['bash','-c',old_script,'fixture',str(R2/'candidate/route-b-owner.sh')],capture_output=True,text=True)
        self.assertEqual(old.returncode,1)
        self.assertEqual(old.stderr,'')

    def test_existing_worker_composition_binding(self):
        old_compose=load(OLD/'compose.py','old_compose')
        new_compose=load(D/'compose.py','quiet_compose')
        base=OLD.parent/'2026-10-12-recovery-executor'
        with tempfile.TemporaryDirectory() as tmp:
            r=Path(tmp); initial=json.loads((base/'plan.disabled.json').read_text())
            target=next(m['target'] for m in initial['members'] if m['target'].endswith('/watchdog.sh') and '/recovery-attempts/' in m['target']).rsplit('/',1)[0]+'/readiness-probe.sh'
            absent=r/'absent.json';absent.write_text(json.dumps({'target':target,'exists':False,'proof':'old isolated fixture'}))
            old_compose.compose(base,base/'plan.disabled.json',sha(base/'plan.disabled.json'),absent,sha(absent),r/'base24')
            before={'target':target,'exists':True,'sha256':sha(OLD/'candidate/readiness-probe.sh'),'mode':'550','uid':0,'gid':0,'label':'u:object_r:data_file:s0'}
            pre=r/'present.json';pre.write_text(json.dumps(before));plan=r/'base24/plan.disabled.json'
            result=new_compose.compose(r/'base24',plan,sha(plan),pre,sha(pre),r/'new24')
            self.assertEqual(result['members'],24);self.assertFalse(result['execution_enabled'])
            output=json.loads((r/'new24/plan.disabled.json').read_text())
            members=[m for m in output['members'] if m['target']==target]
            self.assertEqual(len(members),1);self.assertEqual(members[0]['before'],before)
            self.assertEqual((r/'new24/payload/members.tsv').read_text().count(' readiness-probe.sh 550'),1)
            with self.assertRaises(ValueError):
                new_compose.compose(r/'base24',plan,sha(plan),absent,sha(absent),r/'invalid-absence')
            before['sha256']='0'*64;pre.write_text(json.dumps(before))
            with self.assertRaises(ValueError):
                new_compose.compose(r/'base24',plan,sha(plan),pre,sha(pre),r/'invalid-sha')

    def test_exact_patch_and_bindings(self):
        old=(OLD/'candidate/route-b-owner.sh').read_text()
        previous=(OLD/'r2b-quiet-reset/candidate/route-b-owner.sh').read_text()
        current=(C/'route-b-owner.sh').read_text()
        def without_emitter(text):
            a=text.index('rb_guard_json(){');b=text.index('\nrb_deny(){',a)
            return text[:a]+text[b:]
        self.assertEqual(without_emitter(previous),without_emitter(current))
        for name in ('watchdog.sh','launch-common.sh'):
            self.assertEqual((C/name).read_bytes(),(OLD/'candidate'/name).read_bytes())
        worker=(C/'readiness-probe.sh').read_text()
        prior=(OLD/'r2b-quiet-reset/candidate/readiness-probe.sh').read_text()
        self.assertEqual(worker,prior.replace('   rb_guard_json readiness ready requires_final_original_child_owned || exit 5\n   exit 0;;','   # Success must leave the 2-second envelope without diagnostic subprocesses.\n   # The caller still runs the final original complete child_owned guard.\n   exit 0;;'))
        self.assertIn(sha(C/'route-b-owner.sh'),(C/'entry.sh').read_text())
        self.assertIn(sha(C/'members.tsv'),(C/'startup.env').read_text())
        self.assertEqual((C/'startup.expected.sha256').read_text().strip(),sha(C/'startup.env'))

class TransitionTests(unittest.TestCase):
    def test_async_root_to_exact_uid(self):
        p,rows,_=legacy.run_case({'uid':'0','transition':True})
        self.assertEqual(p.returncode,0,p.stderr)
        self.assertTrue(any(x['phase']=='readiness_pending' and x['actual']=='0:0:0:0' for x in rows))
        self.assertFalse(any(x['actual']=='ready' for x in rows))
    def test_already_ready_no_success_encoding(self):
        p,rows,_=legacy.run_case({})
        self.assertEqual(p.returncode,0,p.stderr);self.assertEqual(rows,[])
    def test_root_parent_does_not_overwrite_valid_child_uid(self):
        p,rows,elapsed=legacy.run_case({'uid':'20011206'})
        self.assertEqual(p.returncode,0,p.stderr);self.assertLess(elapsed,1);self.assertEqual(rows,[])
    def test_final_strict_guard_still_required(self):
        p,_,_=legacy.run_case({});self.assertEqual(p.returncode,0)
        p,rows,_=legacy.run_case({'uid':'0'},strict=True)
        self.assertNotEqual(p.returncode,0);self.assertEqual(rows[-1]['field'],'uid')
        text=(C/'watchdog.sh').read_text()
        self.assertIn('timeout 2 sh "$F/readiness-probe.sh"',text)
        self.assertIn('child_owned "$child" "$child_birth" ||',text)

if __name__=='__main__':
    # The original real-context readiness and strict rejection fixtures run
    # against this NEW helper/worker; no old frozen files are changed.
    legacy=load(OLD/'test_readiness.py','legacy_readiness')
    legacy.C=C
    suite=unittest.TestSuite()
    for group in (QuietScanTests,TransitionTests,legacy.RejectTests):
        suite.addTests(unittest.defaultTestLoader.loadTestsFromTestCase(group))
    runner=unittest.TextTestRunner(verbosity=2)
    raise SystemExit(not runner.run(suite).wasSuccessful())
