#!/usr/bin/env python3
"""Actual R3 loop/launch methods with external OH/JNI/process seams only."""
import argparse, hashlib, json, subprocess, tempfile
from pathlib import Path
import replay

EXTRA=r'''
ret_key=; monitor_child; phase=exited; ticks=0; spawn_calls=0; fail_spawn=0; extra_pids=; max_ticks=4
rb_owned_pids() { [ -z "$extra_pids" ] || echo "$extra_pids"; return 0; }
rb_birth() { if [ "$1" = 8080 ]; then echo "${new_birth:-222}"; elif [ "$phase" = exited ]; then return 1; elif [ "$phase" = reused ]; then echo 9999; else echo 7475; fi; }
timeout() { case "$*" in *spawn.sh*) spawn_calls=$((spawn_calls+1)); [ "$fail_spawn" = 0 ] || return 1; echo 'HOST_SPAWN result=0 pid=8080';; *) echo readiness_fixture;; esac; return 0; }
rb_guard_json() { :; }
rc_capture_wms() { return 0; }
rc_focus_state() { ticks=$((ticks+1)); case "$ticks" in 1|3|5) rc_focus_result=desktop;; *) rc_focus_result='host 30';; esac; return 0; }
rc_stop_present() { [ "$ticks" -ge "$max_ticks" ]; }
rc_sleep() { :; }
TT_MAX_POLLS=1
printf '%s\n' 'WindowName DisplayId Pid WinId Type Mode Flag ZOrd Orientation [ x y w h ]' 'imehost0 0 55 30 1 1 0 1 0 [ 0 0 100 100 ]' > "$F/wms-owned.txt"
'''
TAIL=r'''
printf '%s\n' 'Focus window: 30' 'All Focus window:' 'DisplayId: 0 WindowId: 30' 'Total window num: 9' 'Highlighted windows: 30' >> "$F/wms-owned.txt"
'''
CASES={
 'empty_windows_one_spawn': (TAIL+'rc_reentry_loop; printf "RESULT rc=%s calls=%s seq=%s child=%s birth=%s retired=%s state=%s\\n" "$?" "$spawn_calls" "$seq" "$child" "$child_birth" "$ret_key" "$(rc_child_state)"', ['calls=1 seq=2 child=8080 birth=222 retired= state=alive']),
 'retired_pid_window': ('echo "old 0 7172 99 1 1 0 -1 0 [ 0 0 100 100 ]" >> "$F/wms-owned.txt"\n'+TAIL+'rc_reentry_loop; printf "RESULT calls=%s owned=%s child=%s\\n" "$spawn_calls" "$rc_owned_result" "$child"', ['calls=0 owned=unknown child=7172','consume_live_or_window']),
 'other_owned_window': ('extra_pids=999; echo "other 0 999 99 1 1 0 -1 0 [ 0 0 100 100 ]" >> "$F/wms-owned.txt"\n'+TAIL+'rc_reentry_loop; printf "RESULT calls=%s owned=%s\\n" "$spawn_calls" "$rc_owned_result"', ['calls=0 owned=yes','consume_live_or_window']),
 'invalid_wms': ('echo broken > "$F/wms-owned.txt"; rc_reentry_loop; printf "RESULT calls=%s owned=%s\\n" "$spawn_calls" "$rc_owned_result"', ['calls=0 owned=unknown']),
 'owned_prelaunch_refusal_keeps_retirement': ('extra_pids=999; old_key=$ret_key; do_one_launch; r=$?; phase=reused; rc_gates_ok; g=$?; printf "RESULT launch=%s started=%s calls=%s key_kept=%s gate=%s\\n" "$r" "$do_spawn_started" "$spawn_calls" "$([ "$ret_key" = "$old_key" ] && echo yes)" "$g"', ['launch=2 started=0 calls=0 key_kept=yes gate=0']),
 'unknown_spawn_sticky_no_retry': (TAIL+'fail_spawn=1; max_ticks=6; rc_reentry_loop; printf "RESULT calls=%s hold=%s retired=%s\\n" "$spawn_calls" "$rc_hold" "$ret_key"', ['calls=1 hold=1 retired=','reentry_spawn_unknown_hold','reentry_hold_fail_closed']),
 'new_child_guard_restored': ('do_one_launch; r=$?; new_birth=333; rc_gates_ok; printf "RESULT launch=%s gate=%s reason=%s retired=%s\\n" "$r" "$?" "$rc_gate_reason" "$ret_key"', ['launch=0 gate=1 reason=child_identity retired=']),
}
CASES['actual_main_adopt_clears_retirement'] = (r'''
TT_PARENT_PID=5177; TT_PARENT_BIRTH=5834; TT_CHILD_PID=8080; TT_CHILD_BIRTH=222
preconditions() { :; }; capture_init() { :; }; release_lock() { :; }
rb_birth() { if [ "$1" = "$$" ]; then echo 1; elif [ "$1" = 8080 ]; then echo "${new_birth:-222}"; else return 1; fi; }
rm "$F/lock/owner"; rmdir "$F/lock"
''' + TAIL + r'''
main; m=$?; new_birth=333; rc_gates_ok; g=$?
printf 'RESULT main=%s calls=%s child=%s birth=%s seq=%s retired=%s gate=%s reason=%s\n' "$m" "$spawn_calls" "$child" "$child_birth" "$seq" "$ret_key" "$g" "$rc_gate_reason"
''', ['main=0 calls=0 child=8080 birth=222 seq=2 retired= gate=1 reason=child_identity','child_retirement_cleared adopt'])

def main():
 ap=argparse.ArgumentParser();ap.add_argument('--source',type=Path,required=True);ap.add_argument('--common',type=Path,required=True);ap.add_argument('--parser',type=Path,required=True);ap.add_argument('--out',type=Path,required=True);a=ap.parse_args();a.out.mkdir(parents=True,exist_ok=False)
 pins={k:replay.digest(getattr(a,k)) for k in ['source','common','parser']}; rows=[]
 for name,(body,expected) in CASES.items():
  script=replay.functions(a.source)+'\n'+replay.functions(a.common)+'\n'+a.parser.read_text()+'\n'+replay.SETUP+'\n'+EXTRA+'\n'+body+'\n'
  (a.out/(name+'.sh')).write_text(script)
  with tempfile.TemporaryDirectory(prefix='retirement-edge-') as td:
   Path(td,'case.sh').write_text(script);argv=['/bin/sh','case.sh','fixture'];r=subprocess.run(argv,cwd=td,capture_output=True,timeout=5)
  for ext,b in [('stdout',r.stdout),('stderr',r.stderr),('rc',str(r.returncode).encode())]:(a.out/(name+'.'+ext)).write_bytes(b)
  (a.out/(name+'.argv.json')).write_text(json.dumps(argv)+'\n')
  text=r.stdout.decode(); ok=r.returncode==0 and all(x in text for x in expected)
  rows.append({'case':name,'pass':ok,'expected_fragments':expected,'stdout':text,'stderr':r.stderr.decode(),'rc':r.returncode})
 result={'pins':pins,'after_pins':{k:replay.digest(getattr(a,k)) for k in pins},'host_only':True,'cases':rows};result['passed']=all(x['pass'] for x in rows) and pins==result['after_pins'];(a.out/'results.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result,indent=2));return 0 if result['passed'] else 1
if __name__=='__main__':raise SystemExit(main())
