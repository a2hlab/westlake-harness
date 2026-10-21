#!/usr/bin/env python3
"""Replay the T37 peer counterexamples (replay_candidate.py, imported read-only, its case scripts
unchanged) against the r4b revision with an ADDITIVE fixture, so each case reaches the code path it
targets instead of stopping at r4b's new epoch-record precondition.

The fixture adds what r4b now requires and the real device has: the guardian's own /proc entry
(live-view witness), mount-namespace links, a bound epoch record, and — for the peer's "exited" stop
mode — removal of the old parent's /proc entry (on Linux an exited process has no entry). The
per-case expectations below are the REQUIRED behaviour, not observed bugs: controls keep the peer's
expected observation; counterexamples must now refuse or hold. Usage: replay_r4b.py PEER_DIR SNAPSHOT OUT
"""
import hashlib, json, subprocess, sys, tempfile
from pathlib import Path

peer, snap, out = Path(sys.argv[1]).resolve(), Path(sys.argv[2]).resolve(), Path(sys.argv[3])
sys.dont_write_bytecode = True
sys.path.insert(0, str(peer))
import replay_candidate as rc  # noqa: E402
import replay  # noqa: E402

FIX = r'''
# ---- r4b additive fixture (see module docstring) ----
RB_PROC=$PROC   # watchdog top level (line 19); the peer harness extracts functions only
self_birth=222; printf '%s %s %s\n' "$$" "$self_birth" "$BOOT" > "$F/lock/owner"
mkdir -p "$PROC/$$/fd" "$PROC/5177/ns" "$PROC/8080/ns" "$PROC/9090/ns"
printf '%s (sh) S 1 1 1 0 -1 0 0 0 0 0 0 0 0 0 20 0 1 0 222 0 0\n' "$$" > "$PROC/$$/stat"
printf 'Uid:\t0\t0\t0\t0\n' > "$PROC/$$/status"; : > "$PROC/$$/net-unix-empty"
mkdir -p "$PROC/$$/net"; : > "$PROC/$$/net/unix"
for np in 5177 8080 9090; do ln -s "mnt:[40265$np]" "$PROC/$np/ns/mnt"; printf 'Uid:\t0\t0\t0\t0\n' > "$PROC/$np/status"; done
printf 'phase=bound parent=5177:5834 mntns=mnt:[402655177] sock=333 sockfile=1:20\n' > "$F/parent-epoch"
write_exact() { printf '%s\n' "$2" > "$1"; }
# Old parent's fd vanishes with it; a started parent becomes the sole holder of its new listener.
rc_fd_holders() { if [ "$starts" -gt 0 ]; then cat "$F/parent-start-epoch.txt" 2>/dev/null; else [ -z "$holders" ] || echo "$holders"; fi; return 0; }
rc_send_term() { terms=$((terms+1)); holders=; echo ACTION_TERM; [ "$stop_mode" != exited ] || rm -rf "${PROC:?}/5177"; }
'''

E = 'rc=2 terms=1 unlinks=0 starts=0'
EXPECT = {
 'epoch_success': 'rc=0 terms=1 unlinks=1 starts=1',
 'live_direct_child': 'rc=1 terms=0 unlinks=0 starts=0 reason=children_present:9000',
 'enumeration_error': 'rc=1 terms=0 unlinks=0 starts=0 reason=children_unknown',
 'stranger_socket_holder': 'rc=1 terms=0 unlinks=0 starts=0 reason=socket_owner_unknown',
 'stop_timeout': E + ' reason=epoch_hold',
 'birth_read_failure_after_term': E + ' reason=old_parent_exit_unknown',
 'pid_reuse_after_term': E + ' reason=old_parent_pid_reused',
 'malformed_proc_stat': 'rc=1 terms=0 unlinks=0 starts=0 reason=children_unknown',
 'missing_proc_root': 'RESULT rc=1',
 'missing_fd_directory': 'RESULT rc=1 holders=',
 'failed_fd_readlink': 'RESULT rc=1 holders=',
 'nonlistener_socket_row': 'RESULT rc=1 inode=',
 'live_child_new_host_loop': 'rc=0 terms=0 unlinks=0 starts=0',
 'failed_start_sticky': 'rc=2 terms=1 unlinks=1 starts=1 reason=epoch_hold',
 'newhost_two_edges_one_epoch_spawn': 'COUNTS terms=1 starts=1 spawns=1 parent=9090 child=8080 seq=2',
 'newhost_owned_enum_failure': 'COUNTS terms=0 starts=0 spawns=0',
}
# The peer's rc7 lever stubs rb_owned_pids, which r4b no longer trusts (the frozen helper's rc is the
# last loop test, not completeness). Model the same failure as an existing, unclassifiable /proc entry.
UNCLASSIFIABLE = 'mkdir -p "$PROC/9100"; '
BODY_PREFIX = {'newhost_owned_enum_failure': UNCLASSIFIABLE}
LOOP = 'rc_focus_state() { loop_focus; rc_focus_result=$(echo "$rc_focus_result" | sed "s/^host /newhost /"); }; '
NEW = [
 ('epoch_record_missing', '', 'rm -f "$F/parent-epoch"; rc_parent_epoch_switch 31; r=$?; summary', 'rc=1 terms=0 unlinks=0 starts=0 reason=epoch_record_missing'),
 ('epoch_parent_mismatch', '', 'printf "phase=bound parent=5177:1 mntns=mnt:[402655177] sock=333 sockfile=1:20\\n" > "$F/parent-epoch"; rc_parent_epoch_switch 31; r=$?; summary', 'rc=1 terms=0 unlinks=0 starts=0 reason=epoch_parent_mismatch'),
 ('epoch_namespace_changed', '', 'rm -f "$PROC/5177/ns/mnt"; ln -s "mnt:[9]" "$PROC/5177/ns/mnt"; rc_parent_epoch_switch 31; r=$?; summary', 'rc=1 terms=0 unlinks=0 starts=0 reason=epoch_binding_changed'),
 ('epoch_record_stopping_after_crash', '', 'printf "phase=stopping old=5177:5834 wid=31 sock=333 sockfile=1:20\\n" > "$F/parent-epoch"; rc_parent_epoch_switch 31; r=$?; summary', 'rc=1 terms=0 unlinks=0 starts=0 reason=epoch_not_bound'),
 ('owned_unclassifiable_before_term', '', UNCLASSIFIABLE + 'rc_parent_epoch_switch 31; r=$?; summary', 'rc=1 terms=0 unlinks=0 starts=0 reason=owned_enumeration_unknown'),
 ('listener_reappears_after_exit', '', 'rc_wait_exit() { echo "x: 00000002 00000000 00010000 0001 01 777 $SOCKET" > "$PROC/$$/net/unix"; return 0; }; rc_parent_epoch_switch 31; r=$?; summary', E + ' reason=socket_listener_after_exit:1'),
 ('same_host_launch_owned_enum_unknown', '', UNCLASSIFIABLE + 'rc_focus_state() { loop_focus; }; rc_reentry_loop; r=$?; summary; echo COUNTS spawns=$spawn_calls', 'COUNTS spawns=0'),
 ('malformed_stat_primitive', 'rc_direct_children', 'for np in 5177 8080 9090; do printf "%s (x) S 1 1 1 0 -1 0 0 0 0 0 0 0 0 0 20 0 1 0 9 0 0\\n" "$np" > "$PROC/$np/stat"; done; mkdir -p "$PROC/9000"; echo malformed > "$PROC/9000/stat"; found=$(rc_direct_children 5177); echo RESULT rc=$? kids=$found', 'RESULT rc=1 kids='),
 ('wellformed_stat_primitive_control', 'rc_direct_children', 'for np in 5177 8080 9090; do printf "%s (x) S 1 1 1 0 -1 0 0 0 0 0 0 0 0 0 20 0 1 0 9 0 0\\n" "$np" > "$PROC/$np/stat"; done; mkdir -p "$PROC/9000"; printf "9000 (k) S 5177 1 1 0 -1 0 0 0 0 0 0 0 0 0 20 0 1 0 9 0 0\\n" > "$PROC/9000/stat"; found=$(rc_direct_children 5177); echo RESULT rc=$? kids=$found', 'RESULT rc=0 kids=9000'),
 ('newhost_loop_exit_unknown', '', 'stop_mode=unreadable; mkdir -p "$PROC/5177"; ' + LOOP + 'rc_reentry_loop; r=$?; summary; echo COUNTS terms=$terms starts=$starts spawns=$spawn_calls', 'COUNTS terms=1 starts=0 spawns=0'),
]

w = rc.functions(snap / 'watchdog-reentry-r4.sh')
import re as _re
# The peer harness does not load route-b-owner.sh. Take the production rb_uid verbatim from the r3
# payload; rb_owned is a refusing stub (fixture entries all have uid 0, so it is never reached).
RBUID = _re.search(r'^rb_uid\(\)\{\n.*?^\}', (replay.BASE / 'route-b-owner.sh').read_text(), _re.M | _re.S).group(0) + '\nrb_owned() { return 1; }'

prod = w + '\n' + rc.functions(snap / 'reentry-common-r4.sh') + '\n' + (replay.BASE / 'reentry-seams.sh').read_text()
cases = [(n, r, BODY_PREFIX.get(n, '') + b, EXPECT[n], k) for n, r, b, _e, k in rc.CASES] + [(n, r, b, e, 'r4b-added') for n, r, b, e in NEW]
out.mkdir(parents=True, exist_ok=False)
rows = []
for name, restore, body, expect, kind in cases:
    restored = ''
    if restore:
        import re
        restored = re.search(r'^' + restore + r'\(\) \{[^\n]*\n.*?^\}', w, re.M | re.S).group(0)
    script = prod + '\n' + replay.SETUP + '\n' + rc.EXTRA + '\n' + RBUID + '\n' + FIX + '\n' + restored + '\n' + body + '\n'
    with tempfile.TemporaryDirectory(prefix='t36-r4b-') as td:
        (Path(td) / 'case.sh').write_text(script)
        p = subprocess.run(['/bin/sh', 'case.sh', 'fixture'], cwd=td, capture_output=True, text=True, timeout=30)
    row = dict(case=name, peer_kind=kind, rc=p.returncode, stdout=p.stdout, stderr=p.stderr, required=expect,
               passed=p.returncode == 0 and expect in p.stdout, script_sha256=hashlib.sha256(script.encode()).hexdigest())
    rows.append(row)
    (out / (name + '.sh')).write_text(script)
    (out / (name + '.receipt.json')).write_text(json.dumps(row, indent=2) + '\n')
    print(('PASS' if row['passed'] else 'FAIL'), kind, name, '|', ' | '.join(l for l in p.stdout.splitlines() if l.startswith(('RESULT', 'COUNTS'))))
res = dict(schema='t36-r4b-peer-replay/v1', snapshot_pins=json.loads((snap / 'pins.json').read_text()),
           peer_harness_sha256={f: hashlib.sha256((peer / f).read_bytes()).hexdigest() for f in ('replay.py', 'replay_candidate.py')},
           fixture_sha256=hashlib.sha256(FIX.encode()).hexdigest(), cases=rows, all_passed=all(r['passed'] for r in rows),
           candidate_accepted=False, device_access=False)
(out / 'results.json').write_text(json.dumps(res, indent=2) + '\n')
print(sum(r['passed'] for r in rows), 'passed,', sum(not r['passed'] for r in rows), 'failed')
sys.exit(0 if res['all_passed'] else 1)
