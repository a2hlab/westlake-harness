"""Offline production-function regressions. No HDC/SSH/UI/device execution."""
import json,os,subprocess,sys,tempfile,unittest
from pathlib import Path
from derive import *
ROOT='/data/westlake-demo/toutiao/recovery-attempts/icon-manual-5cd-t13-unit'
class Production(unittest.TestCase):
 def fixture(self,d):
  p=Path(d);payload=derive(ROOT,DESKTOP_UID,99999999)
  for n,s in payload.items():
   if n=='watchdog.sh':s=s.rsplit('\nmain "$@"',1)[0]+'\n'
   if n=='term-once.sh':s=s[s.index('t13_term_once() {'):].rsplit('\nt13_term_once',1)[0]+'\n'
   (p/n).write_text(s)
  for rel in ['proc/sys/kernel/random','proc/1','runtime/app-data','runtime/data','runtime/webview-t-data']:(p/rel).mkdir(parents=True,exist_ok=True)
  (p/'proc/sys/kernel/random/boot_id').write_text(BOOT+'\n');(p/'proc/uptime').write_text('10.0 0\n')
  for pid,birth,parent,uid in [(CHILD,CHILD_BIRTH,PARENT,UID),(PARENT,BIRTH,1,0),(777,888,PARENT,UID)]:
   (p/f'proc/{pid}').mkdir();(p/f'proc/{pid}/stat').write_text(self.row(pid,birth,parent))
   (p/f'proc/{pid}/status').write_text(f'Uid:\t{uid}\t{uid}\t{uid}\t{uid}\nTracerPid:\t0\n')
  return p
 def row(self,pid,birth,parent,state='S'):return f'{pid} (fixture) {state} {parent} '+'0 '*17+str(birth)+' 0\n'
 def run_shell(self,body,expected=0):
  with tempfile.TemporaryDirectory() as d:
   p=self.fixture(d)
   setup='''#!/bin/sh
. "$(dirname "$0")/watchdog.sh"
F=$(dirname "$0"); HERE=$F; PROC=$F/proc; RB_PROC=$PROC; RUNTIME=$F/runtime; RB_RUNTIME=$RUNTIME
RB_OWNER_UID='''+str(UID)+'''; BOOT='''+BOOT+'''; parent='''+str(PARENT)+'''; parent_birth='''+str(BIRTH)+'''; child='''+str(CHILD)+'''; child_birth='''+str(CHILD_BIRTH)+'''
TT_DEADLINE_UPTIME=99999999; self_birth=99; TT_RECOVERY_EXECUTE=1; TT_EXPECT_BOOT=$BOOT; RC_DESKTOP_UID='''+str(DESKTOP_UID)+'''
readlink(){ case "$1" in */ns/mnt) case "$1" in */1/ns/mnt) echo init;; *) echo private;; esac;; */exe) echo /data/local/tmp/asx/appspawn-x;; *) return 9;; esac; }
sha256sum(){ case "$1" in */exe) echo "$RB_SPAWNER_SHA  $1";; *) command shasum -a 256 "$1";; esac; }
stat(){ case "$*" in *%d:%i*) if [ -f "$F/inode-drift" ]; then case "$*" in *root/data*) echo 9:9;; *) echo 7:8;; esac; else echo 7:8; fi;; *) return 9;; esac; }
'''
   (p/'runner.sh').write_text(setup+body+'\n')
   r=subprocess.run(['sh',str(p/'runner.sh')],capture_output=True,text=True,timeout=10)
   print(json.dumps({'case':self._testMethodName,'rc':r.returncode,'stdout':r.stdout,'stderr':r.stderr}),flush=True)
   self.assertEqual(r.returncode,expected,r.stdout+r.stderr)
   return r
 def test_profile_syntax_preview(self):
  payload=derive(ROOT,DESKTOP_UID,99999999);src=sources()
  for n in ['real-spawn.sh','route-b-owner.sh','readiness-probe.sh','launch-common.sh','reentry-seams.sh','exit-verdict.sh']:self.assertEqual(payload[n],src[n])
  self.assertEqual(payload['spawn.sh'].replace('t12_launch_guard\n',''),src['spawn-prepared.sh'])
  with tempfile.TemporaryDirectory() as d:
   for n,s in payload.items():
    if n.endswith('.sh'):
     f=Path(d)/n;f.write_text(s);r=subprocess.run(['sh','-n',str(f)],capture_output=True,text=True);self.assertEqual(r.returncode,0,r.stderr)
  for action in ['preflight','apply','term-once','stop','restore']:
   r=subprocess.run([sys.executable,str(HERE/'tool.py'),action],capture_output=True,text=True);self.assertEqual(r.returncode,0,r.stderr);self.assertEqual(json.loads(r.stdout)['device_calls'],0)
  with self.assertRaises(ValueError):derive(ROOT,20010018,9999)
 def test_owned_identity_drift(self):
  self.run_shell('''child_owned 31210 7485570 || exit 10
child_owned 31210 999 && exit 11
sed 's/20011300/20010018/g' "$PROC/31210/status" > "$F/status"; cp "$F/status" "$PROC/31210/status"
child_owned 31210 7485570 && exit 12
printf 'Uid:\t20011300\t20011300\t20011300\t20011300\n' > "$PROC/31210/status"
touch "$F/inode-drift"; child_owned 31210 7485570 && exit 13
rm "$F/inode-drift"
sed 's/S 19163/S 1/' "$PROC/31210/stat" > "$F/st"; cp "$F/st" "$PROC/31210/stat"
child_owned 31210 7485570 && exit 14
rm "$PROC/31210/stat"; child_owned 31210 7485570 && exit 15
exit 0''')
 def main_body(self,env):
  return '''capture_init(){ :; }; release_lock(){ :; }
# Supply this fixture shell's own stat, retain actual preconditions/main/write_exact/instance/child_owned.
printf '%s (fixture) S 1 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 99 0\n' "$$" > "$F/selfstat"
mkdir "$PROC/$$"; cp "$F/selfstat" "$PROC/$$/stat"
TT_PARENT_PID=19163; TT_PARENT_BIRTH=7265322
'''+env+'''
do_one_launch(){ echo FORBIDDEN_SPAWN; return 7; }
monitor_child(){ [ "$seq:$child:$child_birth" = 1:31210:7485570 ] || return 7; [ -f "$F/adopted" ] || return 8; echo MONITOR_ADOPTED; return 0; }
rc_reentry_loop(){ [ "$(cat "$F/state")" = AWAITING_REENTRY ] || return 8; echo MANUAL_WAIT; }
main; code=$?
printf 'MAIN_RC=%s SEQ=%s CHILD=%s BIRTH=%s\n' "$code" "$seq" "$child" "$child_birth"
'''
 def test_main_adopts_real_branch(self):
  r=self.run_shell(self.main_body('TT_CHILD_PID=31210; TT_CHILD_BIRTH=7485570')+'[ "$code" = 0 ] && [ "$seq" = 1 ]')
  self.assertIn('MONITOR_ADOPTED',r.stdout);self.assertIn('MANUAL_WAIT',r.stdout);self.assertNotIn('FORBIDDEN_SPAWN',r.stdout)
 def test_main_missing_child_no_fallback(self):
  r=self.run_shell(self.main_body('unset TT_CHILD_PID TT_CHILD_BIRTH')+'[ "$code" = 2 ] && [ ! -e "$F/adopted" ]')
  self.assertNotIn('FORBIDDEN_SPAWN',r.stdout)
 def test_main_reused_child_refuses(self):
  r=self.run_shell(self.main_body('TT_CHILD_PID=31210; TT_CHILD_BIRTH=999')+'[ "$code" = 2 ] && [ ! -e "$F/adopted" ]')
  self.assertNotIn('FORBIDDEN_SPAWN',r.stdout)
 def term_setup(self):return '''. "$F/term-once.sh"
# Guardian/boot/window boundaries are checked separately by adoption guard tests.
t13_adoption_guard(){ [ ! -e "$F/guard-fail" ]; }
kill(){ [ -s "$F/term.intent" ] || return 77; printf '%s %s\n' "$1" "$2" >> "$F/signals"; return "${kill_rc:-0}"; }
'''
 def test_term_once_real_rb_signal(self):
  self.run_shell(self.term_setup()+'''t13_term_once || exit 10
t13_term_once && exit 11
[ "$(cat "$F/signals")" = '-TERM 31210' ] || exit 12
[ "$(wc -l < "$F/signals")" -eq 1 ]''')
 def test_term_failure_receipt_lost_no_repeat(self):
  self.run_shell(self.term_setup()+'''kill_rc=9
t13_term_once && exit 10
kill_rc=0
t13_term_once && exit 11
[ "$(wc -l < "$F/signals")" -eq 1 ]''')
 def test_term_drift_zero_signal(self):
  self.run_shell(self.term_setup()+'''sed 's/7485570/999/' "$PROC/31210/stat" > "$F/st"; cp "$F/st" "$PROC/31210/stat"
t13_term_once && exit 11
[ ! -e "$F/signals" ] && [ ! -e "$F/term.intent" ]''')
 def test_term_identity_race_after_intent(self):
  self.run_shell(self.term_setup()+'''checks=0
child_owned(){ checks=$((checks+1)); if [ "$checks" = 2 ]; then sed 's/7485570/999/' "$PROC/31210/stat" > "$F/st"; cp "$F/st" "$PROC/31210/stat"; fi; return 0; }
t13_term_once && exit 10
[ -f "$F/term.intent" ] && [ ! -e "$F/signals" ] || exit 11
t13_term_once && exit 12
[ ! -e "$F/signals" ]''')
 def spawn_setup(self):return '''mkdir "$F/lock"; printf '%s 99 %s\n' "$$" "$BOOT" > "$F/lock/owner"
seq=1; printf '1\n' > "$F/sequence"
rb_owned_pids(){ :; }
timeout(){
 case "$3" in
 "$F/spawn.sh") printf 'spawn\n' >> "$F/external"; [ "${spawn_fail:-0}" = 0 ] || return 8; echo 'result=0 pid=777';;
 "$F/readiness-probe.sh") printf 'readiness\n' >> "$F/external";;
 *) echo "UNEXPECTED_TIMEOUT $*" >&2; return 99;;
 esac
}
'''
 def test_real_spawn_parent_shell_seq2(self):
  self.run_shell(self.spawn_setup()+'''rc_do_spawn
[ "$rc_spawn_result" = 'ok 777 888' ] && [ "$seq:$child:$child_birth" = 2:777:888 ] || exit 10
[ "$(cat "$F/sequence")" = 2 ] || exit 11
rc_stop_present || exit 12
[ "$(cat "$F/stop")" = single_launch_complete ] || exit 13
[ "$(cat "$F/external")" = "$(printf 'spawn\nreadiness')" ]''')
 def test_real_spawn_failure_sticky_intent(self):
  self.run_shell(self.spawn_setup()+'''spawn_fail=1; rc_do_spawn
case "$rc_spawn_result" in unknown*) :;; *) exit 11;; esac
spawn_fail=0; rc_do_spawn
case "$rc_spawn_result" in unknown*) :;; *) exit 12;; esac
[ "$(cat "$F/external")" = spawn ]''')
 def test_stop_deadline_before_spawn(self):
  self.run_shell(self.spawn_setup()+'''rc_stop_present && exit 9
TT_DEADLINE_UPTIME=10
rc_do_spawn
[ "$do_spawn_started" = 0 ] && [ ! -e "$F/external" ] && [ "$(cat "$F/stop")" = deadline ]''')
 def test_stop_arriving_during_owner_scan(self):
  self.run_shell(self.spawn_setup()+'''rb_owned_pids(){ printf 'stop\n' > "$F/stop"; }
rc_do_spawn
[ "$do_spawn_started" = 0 ] && [ ! -e "$F/external" ]''')
 def test_monitor_zombie_and_reuse(self):
  self.run_shell('''mkdir "$F/lock"; printf '%s 99 %s\n' "$$" "$BOOT" > "$F/lock/owner"
sed 's/) S /) Z /' "$PROC/31210/stat" > "$F/st"; cp "$F/st" "$PROC/31210/stat"
monitor_child || exit 10
sed 's/7485570/999/' "$PROC/31210/stat" > "$F/st"; cp "$F/st" "$PROC/31210/stat"
monitor_child && exit 11
[ "$(cat "$F/state")" = OWNER_REFUSED ]''')
 def test_exit_absent_unknown_and_boot(self):
  self.run_shell('''rm "$PROC/31210/stat"
[ "$(child_exit_verdict 31210 7485570 "$BOOT")" = unknown ] || exit 10
rmdir "$PROC/31210" 2>/dev/null || { rm "$PROC/31210/status"; rmdir "$PROC/31210"; }
[ "$(child_exit_verdict 31210 7485570 "$BOOT")" = exited ] || exit 11
printf 'bad\n' > "$PROC/sys/kernel/random/boot_id"
[ "$(child_exit_verdict 31210 7485570 "$BOOT")" = unknown ]''')
 def test_real_reentry_edge(self):
  self.run_shell(self.spawn_setup()+'''i=1
rc_gates_ok(){ return 0; }
rc_focus_state(){ case "$i" in 1) rc_focus_result='host 29';; 2) rc_focus_result=desktop;; *) rc_focus_result='host 29';; esac; }
rc_sleep(){ i=$((i+1)); [ "$i" -lt 8 ] || touch "$F/stop"; }
rc_child_state(){ echo gone; }
rc_owned_window_present(){ rc_owned_result=no; }
rc_after_spawn_ok(){ [ "$1:$2:$seq" = 777:888:2 ]; }
rc_reentry_loop || exit 10
[ "$(cat "$F/external")" = "$(printf 'spawn\nreadiness')" ] && [ "$seq" = 2 ]''')
 def test_owned_window_child_none(self):
  self.run_shell('''child=none; rb_owned_pids(){ :; }; rc_capture_wms(){ :; }
rc_parse_owned_window(){ [ -z "$2" ] || return 2; echo no; }
rc_owned_window_present
[ "$rc_owned_result" = no ]''')
 def test_adopted_instance_guard(self):
  self.run_shell('''. "$F/adoption-guard.sh"
t12_launch_guard(){ [ ! -e "$F/stop" ]; }
mkdir "$PROC/999" "$F/lock"
printf '999 (guardian) S 1 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 123 0\n' > "$PROC/999/stat"
printf 'Uid:\t0\t0\t0\t0\n' > "$PROC/999/status"
printf '/system/bin/sh\n%s\n' "$HERE/watchdog.sh" > "$PROC/999/cmdline"
readlink(){ case "$1" in */999/exe) echo /system/bin/sh;; */ns/mnt) case "$1" in */1/ns/mnt) echo init;; *) echo private;; esac;; */exe) echo /data/local/tmp/asx/appspawn-x;; *) return 9;; esac; }
timeout(){ [ "$1:$2" = 2:strings ] || return 99; cat "$3"; }
printf '999 123 %s 19163 7265322 31210 7485570 1\n' "$BOOT" > "$F/adopted"
printf '999 123 %s\n' "$BOOT" > "$F/lock/owner"
printf '1\n' > "$F/sequence"; seq=1; instance
t13_adoption_guard || exit 10
printf '2\n' > "$F/sequence"; t13_adoption_guard && exit 11
printf '1\n' > "$F/sequence"; printf 'foreign\n' > "$F/lock/owner"; t13_adoption_guard && exit 12
printf '999 123 %s\n' "$BOOT" > "$F/lock/owner"
sed 's/123/124/' "$PROC/999/stat" > "$F/st"; cp "$F/st" "$PROC/999/stat"
t13_adoption_guard && exit 13
exit 0''')
 def test_spawn_wrapper_guards_after_jit(self):
  # Run actual generated spawn wrapper with a fixture config/launch boundary.
  # Original JIT and host_spawn commands are intercepted; none run on a device.
  with tempfile.TemporaryDirectory() as d:
   p=self.fixture(d)
   (p/'config-common.sh').write_text('''AUTH_RUNTIME=fixture; AUTH_STAGE=fixture; AUTH_SOCKET=fixture; AUTH_UID=20011300
TT_PARENT_PID=19163; TT_PARENT_BIRTH=7265322
fail(){ exit 2; }
t12_launch_guard(){ [ ! -e "$HERE/stop" ] || fail stopped; }
timeout(){ touch "$HERE/stop"; echo JIT_BOUNDARY; }
''')
   (p/'launch-common.sh').write_text('verify_parent_window(){ :; }; parent_owned(){ :; }\n')
   # Original source has fixed JIT SHA checks before the guarded invocation.
   raw=(p/'spawn.sh').read_text()
   # Test final guard using actual production command suffix after JIT; no real-spawn exec can occur.
   tail=raw[raw.index('t12_launch_guard\ntimeout 8 /bin/nsenter'):]
   (p/'runner.sh').write_text('HERE=$(dirname "$0"); . "$HERE/config-common.sh"; . "$HERE/launch-common.sh"\n'+tail)
   r=subprocess.run(['sh',str(p/'runner.sh')],capture_output=True,text=True,timeout=5)
   print(json.dumps({'case':self._testMethodName,'rc':r.returncode,'stdout':r.stdout,'stderr':r.stderr}))
   self.assertEqual(r.returncode,2,r.stderr);self.assertIn('JIT_BOUNDARY',r.stderr);self.assertNotIn('not found',r.stderr)
if __name__=='__main__':unittest.main()
