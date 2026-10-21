#!/usr/bin/env python3
"""T37: execute production functions with synthetic OS seams; never device entry."""
import argparse
import hashlib
import json
import re
import subprocess
import tempfile
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
BASE = ROOT / 'benchmark/2026-10-21-t34-demo61b-video/reentry-retirement-01/deploy-package-r3-root/payload'

def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()

def functions(path):
    text = path.read_text()
    return '\n'.join(re.findall(r'^\w+\(\) \{[^\n]+\}$', text, re.M) +
                     re.findall(r'^\w+\(\) \{\n.*?^\}', text, re.M | re.S))

SETUP = r'''
set -u
F=$1; PROC=$F/proc; BOOT=fixture; self_birth=1; child=7172; child_birth=7475
parent=5177; parent_birth=5834; seq=1; ret_key='fixture 1 7172 7475'
keep_lock=0; polls=0; owner_verified=1; RB_OWNER_UID=20011206
RUNTIME=$F/runtime; RB_SPAWNER_SHA=synthetic; enum_rc=0; phase=exited
parent_rc=0; spawn_calls=0; ticks=0; max_ticks=4; fail_spawn=0; bound_wid=30
mkdir -p "$F/lock" "$PROC/sys/kernel/random"
echo "$BOOT" > "$PROC/sys/kernel/random/boot_id"
printf '%s %s %s\n' "$$" "$self_birth" "$BOOT" > "$F/lock/owner"
echo 1 > "$F/sequence"
parent_owned() { return "$parent_rc"; }
rb_birth() { if [ "$1" = 8080 ]; then echo 222; elif [ "$phase" = reused ]; then echo 9999; elif [ "$phase" = alive ]; then echo 7475; else return 1; fi; }
child_owned() { return 0; }
child_exit_verdict() { echo exited; }
rb_owned_pids() { return "$enum_rc"; }
event() { printf 'EVENT %s\n' "$*"; }
state() { printf 'STATE %s\n' "$*"; }
control_file() { :; }
io_fail() { echo "IO_FAIL $*"; exit 70; }
verify_exact() { [ "$(cat "$1")" = "$2" ]; }
rb_guard_json() { :; }
timeout() {
 case "$*" in
  *strings*) printf 'WL_PARENT_ID=%s\nASX_RUNTIME_OWNER_UID=20011206\n' "$bound_wid";;
  *spawn.sh*) spawn_calls=$((spawn_calls+1)); [ "$fail_spawn" = 0 ] || return 1; echo 'HOST_SPAWN result=0 pid=8080';;
  *) :;;
 esac
}
rc_capture_wms() { return 0; }
rc_verify_window_process() { RC_WINDOW_BIRTH=7475; return 0; }
rc_stop_present() { [ "$ticks" -ge "$max_ticks" ]; }
rc_sleep() { :; }
rc_after_spawn_ok() { return 0; }
loop_focus() { ticks=$((ticks+1)); case "$ticks" in 1|3|5) rc_focus_result=desktop;; *) rc_focus_result='host 30';; esac; }
printf '%s\n' 'WindowName DisplayId Pid WinId Type Mode Flag ZOrd Orientation [ x y w h ]' 'imehost0 0 55 30 1 1 0 1 0 [ 0 0 100 100 ]' 'Focus window: 30' 'All Focus window:' 'DisplayId: 0 WindowId: 30' 'Total window num: 1' 'Highlighted windows: 30' > "$F/wms-owned.txt"
cp "$F/wms-owned.txt" "$F/wms-focus.txt"
'''

# The baseline has known failures. 'observed' checks reproducibility, NOT safety.
CASES = [
 ('new_host_binding', 'phase=alive; bound_wid=29; rc_focus_state; echo RESULT focus=$rc_focus_result', 'RESULT focus=other', 'counterexample', 'Verified host with changed WID is silently other; no rebind.'),
 ('same_host_binding', 'phase=alive; rc_focus_state; echo RESULT focus=$rc_focus_result', 'RESULT focus=host 30', 'control', 'Matching WID is recognized.'),
 ('enumeration_failure_window', 'enum_rc=7; rc_owned_window_present; echo RESULT owned=$rc_owned_result', 'RESULT owned=no', 'counterexample', 'Enumeration failure becomes no owned window.'),
 ('enumeration_failure_launch', 'enum_rc=7; do_one_launch; r=$?; echo RESULT rc=$r calls=$spawn_calls', 'RESULT rc=0 calls=1', 'counterexample', 'Failed enumeration permits spawn helper entry.'),
 ('retired_tuple_reuse', 'phase=reused; rc_gates_ok; echo RESULT rc=$? state=$(rc_child_state)', 'RESULT rc=0 state=gone', 'control', 'Strictly retired tuple remains gone after numeric PID reuse.'),
 ('unretired_reuse', 'ret_key=; phase=reused; rc_gates_ok; echo RESULT rc=$? reason=$rc_gate_reason', 'RESULT rc=1 reason=child_identity', 'control', 'Unconfirmed reuse refuses.'),
 ('parent_drift', 'parent_rc=1; rc_gates_ok; echo RESULT rc=$? reason=$rc_gate_reason', 'RESULT rc=1 reason=parent_identity', 'control', 'Parent identity loss refuses.'),
 ('live_child_two_edges', 'ret_key=; phase=alive; rc_focus_state() { loop_focus; }; rc_reentry_loop; echo RESULT calls=$spawn_calls', 'RESULT calls=0', 'control', 'Warm live child cannot spawn.'),
 ('two_edges_one_spawn', 'rc_focus_state() { loop_focus; }; rc_reentry_loop; echo RESULT calls=$spawn_calls child=$child seq=$seq', 'RESULT calls=1 child=8080 seq=2', 'control', 'Successful spawn persists child in current shell.'),
 ('unknown_spawn_two_edges', 'fail_spawn=1; max_ticks=6; rc_focus_state() { loop_focus; }; rc_reentry_loop; echo RESULT calls=$spawn_calls hold=$rc_hold', 'RESULT calls=1 hold=1', 'control', 'Indeterminate spawn sticks in hold.'),
 ('malformed_wms', 'echo broken > "$F/wms-owned.txt"; rc_owned_window_present; echo RESULT owned=$rc_owned_result', 'RESULT owned=unknown', 'control', 'Malformed window dump is unknown.'),
 ('retired_pid_window', 'echo "old 0 7172 99 1 1 0 1 0 [ 0 0 100 100 ]" >> "$F/wms-owned.txt"; rc_owned_window_present; echo RESULT owned=$rc_owned_result', 'RESULT owned=unknown', 'control', 'Window at retired PID is unattributable.'),
]

def run(out=None):
    pins = {p.name: sha(p) for p in sorted(BASE.iterdir()) if p.is_file()}
    production = '\n'.join(functions(BASE / n) for n in ('watchdog.sh', 'reentry-common.sh'))
    production += '\n' + (BASE / 'reentry-seams.sh').read_text()
    rows = []
    for name, body, expected, kind, meaning in CASES:
        script = production + '\n' + SETUP + '\n' + body + '\n'
        with tempfile.TemporaryDirectory(prefix='t37-') as td:
            p = Path(td); (p / 'case.sh').write_text(script)
            result = subprocess.run(['/bin/sh', 'case.sh', 'fixture'], cwd=p, capture_output=True, text=True, timeout=10)
        row = dict(case=name, kind=kind, meaning=meaning, expected_observation=expected,
                   rc=result.returncode, stdout=result.stdout, stderr=result.stderr,
                   reproduced=result.returncode == 0 and expected in result.stdout,
                   script_sha256=hashlib.sha256(script.encode()).hexdigest())
        rows.append(row)
        if out:
            (out / (name + '.sh')).write_text(script)
            (out / (name + '.receipt.json')).write_text(json.dumps(row, indent=2) + '\n')
    result = dict(schema='t37-baseline-replay/v1', source_root=str(BASE.relative_to(ROOT)), source_sha256=pins,
                  source_unchanged=pins == {p.name: sha(p) for p in sorted(BASE.iterdir()) if p.is_file()},
                  argv=['/bin/sh', 'case.sh', 'fixture'], device_access=False,
                  scope='Extracted production functions; synthetic OS/process/transport seams; entry and actual OS operations not executed.',
                  cases=rows)
    result['all_reproduced'] = all(r['reproduced'] for r in rows) and result['source_unchanged']
    if out:
        (out / 'results.json').write_text(json.dumps(result, indent=2) + '\n')
    return result

if __name__ == '__main__':
    parser = argparse.ArgumentParser(); parser.add_argument('--out', type=Path); args = parser.parse_args()
    if args.out: args.out.mkdir(parents=True, exist_ok=False)
    report = run(args.out)
    print(json.dumps(report, indent=2))
    raise SystemExit(0 if report['all_reproduced'] else 1)
