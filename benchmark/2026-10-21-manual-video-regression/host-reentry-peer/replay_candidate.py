#!/usr/bin/env python3
"""Adversarial replay of immutable T36 work-in-progress snapshot; no real signals."""
import argparse
import hashlib
import json
import re
import subprocess
import tempfile
from pathlib import Path
import replay

HERE = Path(__file__).resolve().parent
SNAP = HERE / 'candidate-01'

def functions(p):
    return '\n'.join(re.findall(r'^\w+\(\) \{[^\n]+\}$', p.read_text(), re.M) +
                     re.findall(r'^\w+\(\) \{[^\n]*\n.*?^\}', p.read_text(), re.M | re.S))

EXTRA = r'''
rc_epoch_hold=0; rc_epoch_reason=; terms=0; starts=0; unlinks=0
SOCKET=$F/socket; touch "$SOCKET"; stop_mode=exited; kids=; holders=5177
rc_direct_children() { [ "$kids" != unknown ] || return 1; [ -z "$kids" ] || echo "$kids"; return 0; }
rc_socket_inode_of() { echo 333; }
rc_fd_holders() { [ -z "$holders" ] || echo "$holders"; return 0; }
stat() { echo 1:20; }
sleep() { :; }
rc_send_term() { terms=$((terms+1)); holders=; echo ACTION_TERM; }
rb_birth() {
 if [ "$1" = 5177 ]; then
  if [ "$terms" = 0 ] || [ "$stop_mode" = alive ]; then echo 5834; return 0; fi
  if [ "$stop_mode" = reused ]; then echo 9999; return 0; fi
  return 1
 fi
 echo 222
}
rm() { if [ "$1" = -f ] && [ "${2:-}" = "$SOCKET" ]; then unlinks=$((unlinks+1)); echo ACTION_UNLINK; fi; command rm "$@"; }
rc_run_start_parent() { starts=$((starts+1)); bound_wid=$pe_wid; echo ACTION_START; echo 8080 > "$1"; return 0; }
summary() { echo RESULT rc=$r terms=$terms unlinks=$unlinks starts=$starts reason=$rc_epoch_reason parent=$parent hold=$rc_epoch_hold; }
'''

CASES = [
 ('epoch_success', '', 'rc_parent_epoch_switch 31; r=$?; summary', 'rc=0 terms=1 unlinks=1 starts=1', 'control'),
 ('live_direct_child', '', 'kids=9000; rc_parent_epoch_switch 31; r=$?; summary', 'rc=1 terms=0 unlinks=0 starts=0', 'control'),
 ('enumeration_error', '', 'kids=unknown; rc_parent_epoch_switch 31; r=$?; summary', 'rc=1 terms=0 unlinks=0 starts=0 reason=children_unknown', 'control'),
 ('stranger_socket_holder', '', 'holders="5177 9000"; rc_parent_epoch_switch 31; r=$?; summary', 'rc=1 terms=0 unlinks=0 starts=0', 'control'),
 ('stop_timeout', '', 'stop_mode=alive; rc_parent_epoch_switch 31; r=$?; summary; rc_parent_epoch_switch 31; r=$?; summary', 'rc=2 terms=1 unlinks=0 starts=0 reason=epoch_hold', 'control'),
 ('birth_read_failure_after_term', '', 'stop_mode=unreadable; rc_parent_epoch_switch 31; r=$?; summary', 'rc=0 terms=1 unlinks=1 starts=1', 'counterexample'),
 ('pid_reuse_after_term', '', 'stop_mode=reused; rc_parent_epoch_switch 31; r=$?; summary', 'rc=0 terms=1 unlinks=1 starts=1', 'counterexample'),
 ('malformed_proc_stat', 'rc_direct_children', 'mkdir -p "$PROC/9000"; echo malformed > "$PROC/9000/stat"; rc_parent_epoch_switch 31; r=$?; summary', 'rc=0 terms=1 unlinks=1 starts=1', 'counterexample'),
 ('missing_proc_root', 'rc_direct_children', 'PROC="$F/nonexistent"; rc_direct_children 5177; echo RESULT rc=$?', 'RESULT rc=0', 'counterexample'),
 ('missing_fd_directory', 'rc_fd_holders', 'mkdir -p "$PROC/9000"; found=$(rc_fd_holders 333); echo RESULT rc=$? holders=$found', 'RESULT rc=0 holders=', 'counterexample'),
 ('failed_fd_readlink', 'rc_fd_holders', 'mkdir -p "$PROC/9000/fd"; touch "$PROC/9000/fd/4"; readlink() { return 1; }; found=$(rc_fd_holders 333); echo RESULT rc=$? holders=$found', 'RESULT rc=0 holders=', 'counterexample'),
 ('nonlistener_socket_row', 'rc_socket_inode_of', 'mkdir -p "$PROC/5177/net"; echo "x: 00000002 00000000 00000000 0001 03 333 $SOCKET" > "$PROC/5177/net/unix"; found=$(rc_socket_inode_of 5177); echo RESULT rc=$? inode=$found', 'RESULT rc=0 inode=333', 'counterexample'),
 ('live_child_new_host_loop', '', 'ret_key=; child_owned() { :; }; rb_birth() { echo 7475; }; rc_focus_state() { loop_focus; rc_focus_result=$(echo "$rc_focus_result" | sed "s/^host /newhost /"); }; rc_reentry_loop; r=$?; summary', 'rc=0 terms=0 unlinks=0 starts=0', 'control'),
 ('failed_start_sticky', '', 'rc_run_start_parent() { starts=$((starts+1)); return 1; }; rc_parent_epoch_switch 31; r=$?; summary; rc_parent_epoch_switch 31; r=$?; summary', 'rc=2 terms=1 unlinks=1 starts=1 reason=epoch_hold', 'control'),
 ('newhost_two_edges_one_epoch_spawn', '', 'rc_run_start_parent() { starts=$((starts+1)); echo 9090 > "$1"; }; rc_focus_state() { loop_focus; rc_focus_result=$(echo "$rc_focus_result" | sed "s/^host /newhost /"); }; rc_reentry_loop; r=$?; summary; echo COUNTS terms=$terms starts=$starts spawns=$spawn_calls parent=$parent child=$child seq=$seq', 'COUNTS terms=1 starts=1 spawns=1 parent=9090 child=8080 seq=2', 'control'),
 ('newhost_owned_enum_failure', '', 'enum_rc=7; rc_run_start_parent() { starts=$((starts+1)); echo 9090 > "$1"; }; rc_focus_state() { loop_focus; rc_focus_result=$(echo "$rc_focus_result" | sed "s/^host /newhost /"); }; rc_reentry_loop; r=$?; summary; echo COUNTS terms=$terms starts=$starts spawns=$spawn_calls', 'COUNTS terms=1 starts=1 spawns=1', 'counterexample'),
]

def run(out=None, snapshot=SNAP):
    w = functions(snapshot / 'watchdog-reentry-r4.sh')
    prod = w + '\n' + functions(snapshot / 'reentry-common-r4.sh') + '\n' + (replay.BASE / 'reentry-seams.sh').read_text()
    rows=[]
    for name, restore, body, expect, kind in CASES:
        restored = ''
        if restore:
            restored = re.search(r'^' + restore + r'\(\) \{[^\n]*\n.*?^\}', w, re.M | re.S).group(0)
        script = prod + '\n' + replay.SETUP + '\n' + EXTRA + '\n' + restored + '\n' + body + '\n'
        with tempfile.TemporaryDirectory(prefix='t37-candidate-') as td:
            p=Path(td);(p/'case.sh').write_text(script)
            r=subprocess.run(['/bin/sh','case.sh','fixture'],cwd=p,capture_output=True,text=True,timeout=10)
        row=dict(case=name,kind=kind,rc=r.returncode,stdout=r.stdout,stderr=r.stderr,expected_observation=expect,
                 reproduced=r.returncode==0 and expect in r.stdout,script_sha256=hashlib.sha256(script.encode()).hexdigest())
        rows.append(row)
        if out:
            (out/(name+'.sh')).write_text(script)
            (out/(name+'.receipt.json')).write_text(json.dumps(row,indent=2)+'\n')
    result=dict(schema='t37-candidate-replay/v1',source_pins=json.loads((snapshot/'pins.json').read_text()),cases=rows,
                all_reproduced=all(x['reproduced'] for x in rows),candidate_accepted=False,device_access=False,
                scope='WIP snapshot production epoch/loop functions; signal/start/OS seams synthetic; primitive enumeration functions restored per case.')
    if out:(out/'results.json').write_text(json.dumps(result,indent=2)+'\n')
    return result

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--out',type=Path);p.add_argument('--snapshot',type=Path,default=SNAP);a=p.parse_args()
    if a.out:a.out.mkdir(parents=True,exist_ok=False)
    r=run(a.out,a.snapshot);print(json.dumps(r,indent=2));raise SystemExit(0 if r['all_reproduced'] else 1)
