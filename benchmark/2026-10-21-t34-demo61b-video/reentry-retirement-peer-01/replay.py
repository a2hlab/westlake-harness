#!/usr/bin/env python3
"""Offline replay of extracted production functions; never sources main/device entry."""
import argparse, hashlib, json, re, subprocess, tempfile
from pathlib import Path

def digest(p): return hashlib.sha256(p.read_bytes()).hexdigest()
def functions(p):
    return '\n'.join(re.findall(r'^\w+\(\) \{[^\n]+\}$', p.read_text(), re.M) + re.findall(r'^\w+\(\) \{\n.*?^\}', p.read_text(), re.M | re.S))

SETUP = r'''
F=$1; PROC=$F/proc; BOOT=boot; self_birth=1; child=7172; child_birth=7475; parent=5177; parent_birth=5834; seq=1
keep_lock=0; polls=0; TT_MAX_POLLS=0; owner_verified=1; phase=exited; parent_rc=0; verdict=exited
mkdir -p "$F/lock" "$PROC/sys/kernel/random"
printf '%s\n' "$BOOT" > "$PROC/sys/kernel/random/boot_id"
printf '%s %s %s\n' "$$" "$self_birth" "$BOOT" > "$F/lock/owner"
printf '1\n' > "$F/sequence"
parent_owned() { return "$parent_rc"; }
rb_birth() { case "$phase" in exited|unknown) return 1;; reused) echo 9999;; *) echo 7475;; esac; }
child_owned() { if [ "$phase" = during_owned ]; then echo death >&2; return 1; fi; return 0; }
child_exit_verdict() { echo "$verdict"; }
owned_failure_kind() { echo death; }
event() { printf 'event %s\n' "$*"; }
state() { printf 'state %s\n' "$*"; }
control_file() { :; }
verify_exact() { [ "$(cat "$1")" = "$2" ]; }
io_fail() { echo "IO_FAIL $*"; exit 70; }
capture_frame() { capture_rc=1; capture_reason=fixture; return 1; }
sleep() { :; }
'''
CASES = {
 'strict_first_exit_then_reuse': 'monitor_child; m=$?; phase=reused; rc_gates_ok; g=$?; printf "RESULT monitor=%s gate=%s reason=%s state=%s child=%s birth=%s\\n" "$m" "$g" "$rc_gate_reason" "$(rc_child_state)" "$child" "$child_birth"',
 'strict_owned_exit_then_reuse': 'phase=during_owned; monitor_child; m=$?; phase=reused; rc_gates_ok; g=$?; printf "RESULT monitor=%s gate=%s state=%s\\n" "$m" "$g" "$(rc_child_state)"',
 'unconfirmed_reuse': 'phase=reused; rc_gates_ok; printf "RESULT gate=%s reason=%s\\n" "$?" "$rc_gate_reason"',
 'unknown_not_retired': 'phase=unknown; verdict=unknown; monitor_child; m=$?; phase=reused; rc_gates_ok; printf "RESULT monitor=%s gate=%s\\n" "$m" "$?"',
 'limit_not_retired': 'phase=alive; TT_MAX_POLLS=1; monitor_child; m=$?; phase=reused; rc_gates_ok; printf "RESULT monitor=%s gate=%s\\n" "$m" "$?"',
 'stop_not_retired': 'touch "$F/stop"; monitor_child; m=$?; rm "$F/stop"; phase=reused; rc_gates_ok; printf "RESULT monitor=%s gate=%s\\n" "$m" "$?"',
 'parent_drift': 'monitor_child; phase=reused; parent_rc=1; rc_gates_ok; printf "RESULT gate=%s reason=%s\\n" "$?" "$rc_gate_reason"',
 'boot_drift': 'monitor_child; phase=reused; echo other > "$PROC/sys/kernel/random/boot_id"; rc_gates_ok; printf "RESULT gate=%s reason=%s\\n" "$?" "$rc_gate_reason"',
 'lock_drift': 'monitor_child; phase=reused; echo foreign > "$F/lock/owner"; rc_gates_ok; printf "RESULT gate=%s reason=%s\\n" "$?" "$rc_gate_reason"',
}
for key in ['BOOT','seq','child','child_birth']:
    CASES['retired_tuple_drift_'+key] = f'monitor_child; phase=reused; {key}=999; rc_gates_ok; printf "RESULT gate=%s reason=%s\\n" "$?" "$rc_gate_reason"'

def main():
    ap=argparse.ArgumentParser();ap.add_argument('--source',type=Path,required=True);ap.add_argument('--out',type=Path,required=True);ap.add_argument('--expect',choices=['r2','r3'],required=True);a=ap.parse_args()
    a.out.mkdir(parents=True,exist_ok=False); before=digest(a.source);rows=[]
    for name,body in CASES.items():
        script=functions(a.source)+'\n'+SETUP+'\n'+body+'\n'
        (a.out/(name+'.sh')).write_text(script)
        with tempfile.TemporaryDirectory(prefix='retirement-peer-') as td:
            Path(td,'case.sh').write_text(script)
            argv=['/bin/sh','case.sh','fixture']
            r=subprocess.run(argv,cwd=td,capture_output=True,timeout=5)
        for ext,data in [('stdout',r.stdout),('stderr',r.stderr),('rc',str(r.returncode).encode())]: (a.out/(name+'.'+ext)).write_bytes(data)
        (a.out/(name+'.argv.json')).write_text(json.dumps(argv,indent=2)+'\n')
        line=[l for l in r.stdout.decode().splitlines() if l.startswith('RESULT ')][-1]
        gate='gate=0' if name.startswith('strict_') and a.expect=='r3' else 'gate=1'
        ok=r.returncode==0 and gate in line
        if name.startswith('strict_'):ok=ok and 'monitor=0' in line and ('state=gone' if a.expect=='r3' else 'state=invalid') in line
        if name in ['limit_not_retired','stop_not_retired']:ok=ok and 'monitor=0' in line
        if name=='unknown_not_retired':ok=ok and 'monitor=2' in line
        rows.append({'case':name,'pass':ok,'result':line})
    result={'schema':'retirement-peer-function-replay/v1','source_sha256':before,'source_after_sha256':digest(a.source),'expect':a.expect,'cases':rows,'host_only':True,'scope':'actual extracted production functions; external process/filesystem seams mocked; no device main'}
    result['passed']=all(x['pass'] for x in rows) and before==digest(a.source)
    (a.out/'results.json').write_text(json.dumps(result,indent=2)+'\n'); print(json.dumps(result,indent=2));return 0 if result['passed'] else 1
if __name__=='__main__': raise SystemExit(main())
