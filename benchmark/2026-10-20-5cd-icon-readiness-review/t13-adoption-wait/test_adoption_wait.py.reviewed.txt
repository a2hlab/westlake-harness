"""Actual generated readonly wait/adoption guard; local delayed proc fixture only."""
import ast,json,shlex,subprocess,tempfile,time,types,unittest
from pathlib import Path
import tool
from derive import derive,BOOT,PARENT,BIRTH,CHILD,CHILD_BIRTH,DESKTOP_UID
HERE=Path(__file__).resolve().parent
class AdoptionWait(unittest.TestCase):
 def fixture(self,case,budget,real_sleep=False):
  with tempfile.TemporaryDirectory() as d:
   p=Path(d);proc=p/'proc';(proc/'999').mkdir(parents=True)
   def row(birth):return '999 (sh) S 1 '+'0 '*17+str(birth)+' 0\n'
   (proc/'999/stat').write_text(row(123));(p/'drift-stat').write_text(row(124))
   (proc/'999/status').write_text('Uid:\t0\t0\t0\t0\n')
   (proc/'999/cmdline').write_text('/system/bin/sh\n'+str(p/'entry.sh')+'\n')
   (proc/'uptime').write_text('10.0 0\n')
   payload=derive('/data/westlake-demo/toutiao/recovery-attempts/icon-manual-5cd-t13-fixture',DESKTOP_UID,999999)
   for name in ['route-b-owner.sh','adoption-guard.sh']:(p/name).write_text(payload[name])
   (p/'config-common.sh').write_text('t12_launch_guard(){ [ ! -e "$HERE/stop" ] || exit 2; }\n')
   (p/'launch-common.sh').write_text('''PROC=$HERE/proc; RB_PROC=$PROC; RB_OWNER_UID=20011300
. "$HERE/route-b-owner.sh"
parent_owned(){ [ "$1:$2" = 19163:7265322 ]; }
readlink(){ [ "$1" = "$PROC/999/exe" ] || return 1; echo /system/bin/sh; }
timeout(){ [ "$1:$2" = 2:strings ] || return 1; cat "$3"; }
ticks=0
sleep(){
 ticks=$((ticks+1))
 printf '%s.0 0\\n' "$((10+ticks))" > "$PROC/uptime"
'''+(' command sleep "$1"\n' if real_sleep else '')+(''' if [ "$ticks" = 6 ]; then
  printf '/system/bin/sh\\n%s\\n' "$HERE/watchdog.sh" > "$PROC/999/cmdline"
  cp "$HERE/adopted-ready" "$HERE/adopted"
 fi
''' if case=='delayed' else ''' if [ "$ticks" = 2 ]; then cp "$HERE/drift-stat" "$PROC/999/stat"; fi
''' if case=='birth_drift' else ''' if [ "$ticks" = 2 ]; then printf '/system/bin/sh\\nforeign.sh\\n' > "$PROC/999/cmdline"; fi
''' if case=='cmdline_drift' else '')+'}\n')
   (p/'lock').mkdir();(p/'lock/owner').write_text(f'999 123 {BOOT}\n')
   (p/'sequence').write_text('1\n')
   (p/'instance.txt').write_text(f'boot_id={BOOT}\nchild={CHILD}\nparent={PARENT}\nbirth={CHILD_BIRTH}\nparent_birth={BIRTH}\nseq=1\nmode=preserve\n')
   expected=f'999 123 {BOOT} {PARENT} {BIRTH} {CHILD} {CHILD_BIRTH} 1'
   (p/'adopted-ready').write_text(expected+'\n')
   command='set -eu\n'+tool.adoption_wait(str(p),{'pid':999,'birth':123},budget)
   start=time.monotonic();r=subprocess.run(['sh','-c',command],capture_output=True,text=True,timeout=12);elapsed=time.monotonic()-start
   ticks=int((proc/'uptime').read_text().split('.')[0])-10
   print(json.dumps({'case':case,'budget_seconds':budget,'fixture_elapsed_ticks':ticks,'wall_seconds':elapsed,'rc':r.returncode,'stdout':r.stdout,'stderr':r.stderr,'device_calls':0}),flush=True)
   return r,elapsed,ticks,expected
 def test_delayed_after_five_seconds(self):
  r,elapsed,ticks,expected=self.fixture('delayed',30,True)
  self.assertEqual(r.returncode,0,r.stderr);self.assertGreater(elapsed,5);self.assertEqual(ticks,6);self.assertEqual(r.stdout.strip(),expected)
 def test_never_adopted_expires(self):
  r,_,ticks,_=self.fixture('absent',30)
  self.assertEqual(r.returncode,2);self.assertEqual(ticks,30);self.assertIn('ADOPTION_WAIT_EXPIRED',r.stderr)
 def test_guardian_birth_or_cmdline_drift_refuses(self):
  for case in ('birth_drift','cmdline_drift'):
   r,_,ticks,_=self.fixture(case,30)
   self.assertNotEqual(r.returncode,0);self.assertEqual(ticks,2);self.assertEqual(r.stdout,'')
 def test_actual_transport_timeout_and_reserve(self):
  # Extract unchanged nested production run(), retaining its timeout calculation.
  main=next(n for n in ast.parse((HERE/'tool.py').read_text()).body if isinstance(n,ast.FunctionDef) and n.name=='main')
  run=next(n for n in main.body if isinstance(n,ast.FunctionDef) and n.name=='run')
  factory=ast.parse('def factory():\n seq=0\n return run\n').body[0];factory.body.insert(1,run)
  with tempfile.TemporaryDirectory() as d:
   timeouts=[]
   def execute(argv,**kwargs):timeouts.append(kwargs['timeout']);return types.SimpleNamespace(returncode=0,stdout=b'ok',stderr=b'')
   env={'out':Path(d),'deadline':100,'time':types.SimpleNamespace(monotonic=lambda:0),'need':tool.need,'json':json,'subprocess':types.SimpleNamespace(run=execute,TimeoutExpired=subprocess.TimeoutExpired)}
   exec(compile(ast.fix_missing_locations(ast.Module(body=[factory],type_ignores=[])),'<actual-run>','exec'),env)
   actual=env['factory']();actual(['fixture'],'default');actual(['fixture'],'adopted',command_timeout=35,reserve=60)
   env['deadline']=80;actual(['fixture'],'clipped',command_timeout=35,reserve=60)
   self.assertEqual(timeouts,[15,35,20]);self.assertEqual(tool.adoption_wait_budget(100,0),30);self.assertEqual(tool.adoption_wait_budget(80,0),15)
   with self.assertRaises(ValueError):tool.adoption_wait_budget(65,0)
   print(json.dumps({'case':'actual_transport_timeout','timeouts':timeouts,'recovery_reserve':60,'device_calls':0}))
if __name__=='__main__':unittest.main()
