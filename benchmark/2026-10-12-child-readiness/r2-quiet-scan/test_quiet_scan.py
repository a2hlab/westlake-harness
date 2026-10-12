#!/usr/bin/env python3
"""Execute the real discovery/guard functions offline; no device or signals."""
from pathlib import Path
import hashlib, importlib.util, json, os, subprocess, tempfile, unittest

D = Path(__file__).resolve().parent
OLD = D.parent
C = D / 'candidate'
S = 'a7a358c60bec293c26531b0eecbf14979f77411c227cec4767742c0c82791a0c'
def sha(p): return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def load(path, name):
    spec = importlib.util.spec_from_file_location(name, path)
    mod = importlib.util.module_from_spec(spec); spec.loader.exec_module(mod)
    return mod

class QuietScanTests(unittest.TestCase):
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
        self.assertEqual(calls,6)
        rows=[json.loads(x) for x in p.stderr.splitlines()]
        self.assertEqual(len(rows),1)
        self.assertEqual(rows[0]['field'],'uid')
        self.assertEqual(rows[0]['actual'],'0:0:0:0')
        self.assertEqual(rows[0]['expected'],'20011206:20011206:20011206:20011206')

    def test_existing_worker_composition_binding(self):
        old_compose=load(OLD/'compose.py','old_compose')
        new_compose=load(D/'compose.py','quiet_compose')
        base=OLD.parent/'2026-10-12-recovery-executor'
        with tempfile.TemporaryDirectory() as tmp:
            r=Path(tmp); initial=json.loads((base/'plan.disabled.json').read_text())
            target=next(m['target'] for m in initial['members'] if m['target'].endswith('/watchdog.sh') and '/recovery-attempts/' in m['target']).rsplit('/',1)[0]+'/readiness-probe.sh'
            absent=r/'absent.json';absent.write_text(json.dumps({'target':target,'exists':False,'proof':'old isolated fixture'}))
            old_compose.compose(base,base/'plan.disabled.json',sha(base/'plan.disabled.json'),absent,sha(absent),r/'base24')
            before={'target':target,'exists':True,'sha256':sha(C/'readiness-probe.sh'),'mode':'550','uid':0,'gid':0,'label':'u:object_r:data_file:s0'}
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
        expected=old.replace('rb_deny(){ rb_guard_json "$1" "$2" "$3" || return 5; return 1; }',
            'rb_deny(){\n # Discovery-only subshell sets this flag. Reject identically without encoding.\n [ "${RB_AUDIT_QUIET:-0}" = 1 ] && return 1\n rb_guard_json "$1" "$2" "$3" || return 5; return 1\n}')
        expected=expected.replace('  rb_owned "$p" && echo "$p"','  ( RB_AUDIT_QUIET=1; rb_owned "$p" ) && echo "$p"')
        self.assertEqual((C/'route-b-owner.sh').read_text(),expected)
        for name in ('watchdog.sh','readiness-probe.sh','launch-common.sh'):
            self.assertEqual((C/name).read_bytes(),(OLD/'candidate'/name).read_bytes())
        self.assertIn(sha(C/'route-b-owner.sh'),(C/'entry.sh').read_text())
        self.assertIn(sha(C/'members.tsv'),(C/'startup.env').read_text())
        self.assertEqual((C/'startup.expected.sha256').read_text().strip(),sha(C/'startup.env'))

if __name__=='__main__':
    # The original real-context readiness and strict rejection fixtures run
    # against this NEW helper/worker; no old frozen files are changed.
    legacy=load(OLD/'test_readiness.py','legacy_readiness')
    legacy.C=C
    suite=unittest.TestSuite()
    for group in (QuietScanTests,legacy.TransitionTests,legacy.RejectTests):
        suite.addTests(unittest.defaultTestLoader.loadTestsFromTestCase(group))
    runner=unittest.TextTestRunner(verbosity=2)
    raise SystemExit(not runner.run(suite).wasSuccessful())
