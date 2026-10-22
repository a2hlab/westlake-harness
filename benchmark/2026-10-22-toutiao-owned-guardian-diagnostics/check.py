#!/usr/bin/env python3
"""Execute the pinned watchdog main with synthetic process/filesystem seams only."""
import argparse
import hashlib
import json
from pathlib import Path
import shutil
import subprocess
import tempfile
import time

if not __debug__:
    raise RuntimeError("T46 refuses optimized Python: acceptance assertions must remain enabled")

ROOT = Path(__file__).resolve().parent
CASES = ('birth', 'uid', 'exe', 'namespace', 'ppid', 'success',
         'existing', 'symlink', 'directory', 'write_failure', 'quiet')

def sha(p):
    return hashlib.sha256(p.read_bytes()).hexdigest()

def function(text, start, end, rename):
    body = text[text.index(start):text.index(end)]
    return body.replace(start, rename, 1)

FIXTURE = r'''
set -u
export TT_STATE_ROOT="$PWD/state" TT_RUNTIME="$PWD/runtime" TT_PROC="$PWD/proc"
export TT_OPERATOR_ROOT="$PWD" TT_STAGE="$PWD/stage" TT_SOCKET="$PWD/socket"
export TT_OWNER_UID=12345 TT_RECOVERY_EXECUTE=1 TT_EXPECT_BOOT=fixture-boot
export TT_PARENT_PID=43 TT_PARENT_BIRTH=90 TT_CHILD_PID=42 TT_CHILD_BIRTH=200
export TT_MAX_ATTEMPTS=1 TT_MAX_POLLS=1
mkdir "$TT_PROC/$$"
cp "$TT_PROC/42/stat" "$TT_PROC/$$/stat"
. "$PWD/functions.sh"
# These are local fake process operations; no real process inspection or control.
parent_owned() { echo parent_owned >> trace; return 0; }
capture_init() { echo capture_init >> trace; }
capture_release() { echo capture_release >> trace; }
capture_frame() { echo capture_frame >> trace; capture_rc=125; capture_reason=synthetic_no_frame; return 1; }
kill() { echo FORBIDDEN_kill >> trace; exit 97; }
rb_signal() { echo FORBIDDEN_signal >> trace; exit 97; }
rb_script_signal() { echo FORBIDDEN_script_signal >> trace; exit 97; }
timeout() { echo FORBIDDEN_launch_or_probe >> trace; exit 97; }
sleep() { echo FORBIDDEN_retry >> trace; exit 97; }
readlink() {
 echo readlink >> trace
 case "$1" in
  "$PROC/42/exe")
   if [ "$MODE" = exe ] && [ "$(cat birth-count)" -ge 5 ]; then echo /wrong/synthetic-exe
   else echo /data/local/tmp/asx/appspawn-x; fi;;
  "$PROC/42/ns/mnt")
   if [ "$MODE" = namespace ] && [ "$(cat birth-count)" -ge 5 ]; then echo 'mnt:[1]'
   else echo 'mnt:[2]'; fi;;
  "$PROC/1/ns/mnt") echo 'mnt:[1]';;
  *) echo FORBIDDEN_readlink >> trace; exit 97;;
 esac
}
stat() {
 echo stat >> trace
 case "$4" in "$RUNTIME/run.sh"|"$PROC/42/root/data/local/tmp/asx/run.sh") echo 77:88;;
 *) echo FORBIDDEN_stat >> trace; exit 97;; esac
}
sha256sum() {
 echo sha256sum >> trace
 [ "$1" = "$PROC/42/exe" ] || { echo FORBIDDEN_sha >> trace; exit 97; }
 printf '%s  synthetic-exe\n' "$RB_SPAWNER_SHA"
}
rb_birth() {
 printf 'birth %s\n' "$(if [ "$1" = "$$" ]; then echo SELF; else echo "$1"; fi)" >> trace
 if [ "$1" = 42 ]; then
  count=$(cat birth-count); count=$((count+1)); echo "$count" > birth-count
  if [ "$count" -ge 5 ]; then
   case "$MODE" in
    birth|existing|symlink|directory|write_failure) echo 201; return 0;;
    uid) printf 'Uid: 54321 54321 54321 54321\n' > "$PROC/42/status";;
    ppid) cp "$PWD/wrong-ppid" "$PROC/42/stat";;
   esac
  fi
 fi
 fixture_real_birth "$1"
}
if [ "$MODE" = write_failure ]; then
 # Inject a partial encoder/write failure, not a fake successful persistence.
 rb_guard_json() { printf '{partial' >&2; return 5; }
fi
if [ "$MODE" = quiet ]; then
 RB_AUDIT_QUIET=1
 rb_deny uid synthetic expected
 exit $?
fi
main
exit $?
'''

def run_case(out, variant, mode):
    case = out / variant / mode
    case.mkdir(parents=True)
    for n in ('state', 'runtime/app-data', 'runtime/data', 'runtime/webview-t-data', 'proc/42', 'proc/sys/kernel/random'):
        (case/n).mkdir(parents=True, exist_ok=True)
    def statline(ppid):
        return '42 (synthetic) S '+str(ppid)+' '+'0 '*17+'200\n'
    (case/'proc/42/stat').write_text(statline(43))
    (case/'wrong-ppid').write_text(statline(99))
    (case/'proc/42/status').write_text('Uid: 12345 12345 12345 12345\n')
    (case/'proc/sys/kernel/random/boot_id').write_text('fixture-boot\n')
    (case/'proc/uptime').write_text('100.00 200.00\n')
    (case/'birth-count').write_text('0\n')
    (case/'trace').write_text('')
    victim = case/'victim'; victim.write_text('historical-evidence\n')
    diagnostic = case/'state/guardian-refusal-1.jsonl'
    if mode == 'existing': diagnostic.write_bytes(victim.read_bytes())
    if mode == 'symlink': diagnostic.symlink_to('../victim')
    if mode == 'directory': diagnostic.mkdir()
    src = ROOT/variant
    watchdog = (src/'watchdog.sh').read_text()
    assert watchdog.endswith('main "$@"\n')
    # Remove only the executable entry; call its actual main after installing seams.
    library = watchdog[:-len('main "$@"\n')]
    owner = (src/'route-b-owner.sh').read_text()
    library += function(owner, 'rb_birth(){', 'rb_uid(){', 'fixture_real_birth(){')
    (case/'functions.sh').write_text(library)
    shutil.copyfile(src/'route-b-owner.sh', case/'route-b-owner.sh')
    (case/'driver.sh').write_text(FIXTURE)
    env = {'PATH': '/usr/bin:/bin', 'MODE': mode, 'LC_ALL': 'C'}
    argv = ['/bin/sh', './driver.sh']
    (case/'argv.json').write_text(json.dumps(argv)+'\n')
    (case/'start').write_text(str(time.time())+'\n')
    try:
        with (case/'stdout').open('wb') as stdout, (case/'stderr').open('wb') as stderr:
            proc = subprocess.run(argv, cwd=case, env=env, stdout=stdout, stderr=stderr, timeout=10)
    finally:
        (case/'end').write_text(str(time.time())+'\n')
    (case/'rc').write_text(str(proc.returncode)+'\n')
    trace = (case/'trace').read_text().splitlines()
    assert not any('FORBIDDEN' in line for line in trace), (variant, mode, trace)
    assert victim.read_text() == 'historical-evidence\n'
    if mode == 'existing': assert diagnostic.read_bytes() == victim.read_bytes()
    if mode == 'symlink': assert diagnostic.is_symlink()
    state = (case/'state/state').read_text().strip() if (case/'state/state').exists() else None
    record = None
    if mode not in ('existing','symlink','directory','write_failure') and diagnostic.exists():
        record = json.loads(diagnostic.read_text())
    expected = 0 if mode == 'success' else 1 if mode == 'quiet' else 2
    if variant == 'candidate' and mode in ('existing','symlink','directory','write_failure'): expected = 5
    assert proc.returncode == expected, (variant, mode, proc.returncode, (case/'stderr').read_text())
    if variant == 'candidate':
        if mode in ('birth','uid','exe','namespace','ppid'):
            assert record['field'] == mode and record['pid'] == '42' and record['birth'] == '200', record
            assert record['phase'] == ('monitor' if mode == 'birth' else 'strict')
            values = {'birth': ('201', '200'),
                      'uid': ('54321:54321:54321:54321', '12345:12345:12345:12345'),
                      'exe': ('/wrong/synthetic-exe', 'exact_route_b_alias'),
                      'namespace': ('mnt:[1]', 'not:mnt:[1]'), 'ppid': ('99', '43')}
            assert (record['actual'], record['expected']) == values[mode]
            assert state == 'OWNER_REFUSED'
            events = (case/'state/events.log').read_text()
            assert ('child_birth_changed_no_signal' if mode == 'birth' else 'child_owner_check_failed_no_signal') in events
            assert json.loads((case/'stderr').read_text()) == record
        elif mode in ('success','quiet'):
            assert not list((case/'state').glob('guardian-refusal-*'))
        else:
            assert state == 'IO_FAILED' and 'R1-IO-FAIL' in (case/'stderr').read_text()
            assert (case/'state/lock/owner').exists()  # original io_fail keeps its lock
            if mode == 'write_failure':
                assert diagnostic.read_bytes() == b'{partial'
                assert 'diagnostic_write_failed' in (case/'stderr').read_text()
    if mode == 'success':
        assert 'capture_frame' in trace and 'observation_limit_no_app_control' in (case/'state/events.log').read_text()
    raw = {n: {'sha256': sha(case/n), 'size': (case/n).stat().st_size} for n in ('argv.json','stdout','stderr','rc','start','end')}
    return {'case': mode, 'variant': variant, 'rc': proc.returncode, 'state': state, 'record': record, 'trace': trace, 'raw': raw}

def check(out):
    out.mkdir(parents=True, exist_ok=False)
    sources = json.loads((ROOT/'sources.json').read_text())
    for row in sources['sources']:
        if sha(ROOT/'baseline'/Path(row['path']).name) != row['sha256']:
            raise ValueError('baseline source pin mismatch: '+Path(row['path']).name)
    rows = [run_case(out, v, mode) for mode in CASES for v in ('baseline','candidate')]
    # Original identity query/control order is identical, including birth short circuit.
    for mode in ('birth','uid','exe','namespace','ppid','success','quiet'):
        pair = [x for x in rows if x['case'] == mode]
        assert pair[0]['rc'] == pair[1]['rc']
        assert pair[0]['trace'] == pair[1]['trace'], (mode, pair)
    result = {'pass': True, 'scope': 'synthetic process main-branch replay only; no device acceptance',
              'case_count': len(CASES), 'executions': len(rows),
              'candidate': {n: sha(ROOT/'candidate'/n) for n in ('watchdog.sh','route-b-owner.sh')}, 'rows': rows}
    (out/'receipt.json').write_text(json.dumps(result, indent=2)+'\n')
    print(json.dumps({'pass': True, 'cases': len(CASES), 'executions': len(rows)}))
    return result

if __name__ == '__main__':
    parser = argparse.ArgumentParser(); parser.add_argument('--out', type=Path); args = parser.parse_args()
    if args.out:
        check(args.out.resolve())
    else:
        with tempfile.TemporaryDirectory(prefix='t46-synthetic-') as tmp:
            check(Path(tmp)/'run')
