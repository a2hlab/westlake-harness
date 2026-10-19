import json,subprocess,sys,tempfile,unittest
from pathlib import Path
from derive import *
from tool import power,process_stat
class Offline(unittest.TestCase):
 def test_profile_and_preview(self):
  self.assertEqual(power('ScreenOffTime: Timeout=10000ms OverrideTimeout=10000ms'),{'timeout':10000,'override':10000})
  for raw in ['Timeout=10000ms','ScreenOffTime: Timeout=10000ms OverrideTimeout=-1ms']:
   with self.assertRaises(ValueError):power(raw)
  for uid in [20010018,0]:
   with self.assertRaises(ValueError):derive('/data/westlake-demo/toutiao/recovery-attempts/icon-manual-5cd-t12-unit',uid,999999)
  p=subprocess.run([sys.executable,str(HERE/'tool.py'),'apply'],capture_output=True,text=True);self.assertEqual(p.returncode,0,p.stderr);self.assertEqual(json.loads(p.stdout)['device_calls'],0)
 def test_source_and_generated_shell(self):
  src=sources();p=derive('/data/westlake-demo/toutiao/recovery-attempts/icon-manual-5cd-t12-unit',DESKTOP_UID,999999)
  self.assertEqual(p['spawn.sh'].replace('t12_launch_guard\n',''),src['spawn-prepared.sh'])
  self.assertEqual(p['launch-common.sh'],src['launch-common.sh'])
  self.assertNotIn(' # Original first-launch chain:',p['watchdog.sh'])
  self.assertIn('existing_parent_wait_actual_desktop_icon',p['watchdog.sh'])
  self.assertIn('while ! t12_deadline_stop; do',p['watchdog.sh'])
  with tempfile.TemporaryDirectory() as d:
   for n,s in p.items():
    if n.endswith('.sh'):
     f=Path(d)/n;f.write_text(s);r=subprocess.run(['sh','-n',str(f)],capture_output=True,text=True);self.assertEqual(r.returncode,0,r.stderr)
 def case(self,focus,verdict='ok',expected=0):
  with tempfile.TemporaryDirectory() as d:
   root=Path(d);payload=derive('/data/westlake-demo/toutiao/recovery-attempts/icon-manual-5cd-t12-unit',DESKTOP_UID,999999)
   for n,s in payload.items():
    if n=='watchdog.sh':s=s.rsplit('\nmain "$@"',1)[0]+'\n'
    (root/n).write_text(s)
   (root/'focus').write_text('\n'.join(focus)+'\n')
   runner=root/'runner.sh'
   runner.write_text('''#!/bin/sh
. "$(dirname "$0")/watchdog.sh"
F=$(dirname "$0"); TT_DEADLINE_UPTIME=999999; seq=0; i=1; calls=0
uptime_s(){ echo 1; }
rc_gates_ok(){ return 0; }
rc_focus_state(){ rc_focus_result=$(sed -n "${i}p" "$F/focus"); [ -n "$rc_focus_result" ] || rc_focus_result=other; }
rc_sleep(){ i=$((i+1)); [ "$i" -le '''+str(len(focus)+1)+''' ] || printf 'done\n' > "$F/stop"; }
rc_child_state(){ echo gone; }
rc_owned_window_present(){ rc_owned_result=no; }
rc_do_spawn(){ calls=$((calls+1)); '''+('seq=$((seq+1)); rc_spawn_result="ok 777 888"' if verdict=='ok' else 'rc_spawn_result="unknown failed"')+'''; return 0; }
rc_after_spawn_ok(){ return 0; }
rc_event(){ :; }
rc_reentry_loop
printf 'CALLS=%s\n' "$calls"
''')
   r=subprocess.run(['sh',str(runner)],capture_output=True,text=True,timeout=5);self.assertEqual(r.returncode,0,r.stderr);self.assertIn('CALLS='+str(expected),r.stdout)
 def test_real_reentry_loop_initial_host_no_spawn(self):self.case(['host 29','host 29','other'],expected=0)
 def test_real_reentry_loop_edge_once(self):self.case(['desktop','host 29','desktop','host 29'],expected=1)
 def test_real_reentry_loop_unknown_holds(self):self.case(['desktop','host 29','desktop','host 29'],verdict='unknown',expected=1)
 def test_deadline_and_child_none_parser(self):
  with tempfile.TemporaryDirectory() as d:
   root=Path(d);p=derive('/data/westlake-demo/toutiao/recovery-attempts/icon-manual-5cd-t12-unit',DESKTOP_UID,1)
   for n,s in p.items():
    if n=='watchdog.sh':s=s.rsplit('\nmain "$@"',1)[0]+'\n'
    (root/n).write_text(s)
   (root/'runner.sh').write_text('''#!/bin/sh
. "$(dirname "$0")/watchdog.sh"
F=$(dirname "$0"); TT_DEADLINE_UPTIME=1
uptime_s(){ echo 2; }
t12_deadline_stop || exit 7
[ "$(cat "$F/stop")" = deadline ] || exit 8
child=none
rb_owned_pids(){ :; }
rc_capture_wms(){ :; }
rc_parse_owned_window(){ [ -z "$2" ] || return 1; echo no; }
rc_owned_window_present
[ "$rc_owned_result" = no ] || exit 9
''')
   r=subprocess.run(['sh',str(root/'runner.sh')],capture_output=True,text=True,timeout=5);self.assertEqual(r.returncode,0,r.stderr)
 def test_stop_before_external_spawn(self):
  with tempfile.TemporaryDirectory() as d:
   root=Path(d);p=derive('/data/westlake-demo/toutiao/recovery-attempts/icon-manual-5cd-t12-unit',DESKTOP_UID,1)
   for n,t in p.items():
    if n=='watchdog.sh':t=t.rsplit('\nmain "$@"',1)[0]+'\n'
    (root/n).write_text(t)
   (root/'runner.sh').write_text('''#!/bin/sh
. "$(dirname "$0")/watchdog.sh"
F=$(dirname "$0"); TT_DEADLINE_UPTIME=1; BOOT=fixture; self_birth=1
uptime_s(){ echo 2; }
verify_exact(){ :; }
rb_owned_pids(){ :; }
timeout(){ printf BAD_EXTERNAL_SPAWN; return 7; }
do_one_launch; got=$?
[ "$got" = 2 ] && [ "$do_spawn_started" = 0 ] && [ "$do_reason" = t12_stop_before_spawn ]
''')
   r=subprocess.run(['sh',str(root/'runner.sh')],capture_output=True,text=True,timeout=5);self.assertEqual(r.returncode,0,r.stderr);self.assertNotIn('BAD_EXTERNAL_SPAWN',r.stdout)
if __name__=='__main__':unittest.main()
