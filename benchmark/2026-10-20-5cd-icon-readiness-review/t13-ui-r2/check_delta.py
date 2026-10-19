"""Exact revised UI class + production Board.shell/raw_shell; mock transport, local fixture only."""
from pathlib import Path
import ast,copy,hashlib,importlib.util,json,shlex,subprocess,time,types
HERE=Path(__file__).resolve().parent
ROOT=next(p for p in HERE.parents if (p/'scripts/lab/run_facts.py').is_file())
main=ROOT.parent/'westlake-harness';src=main/'benchmark/2026-09-28-bms-route-deploy/batch/bms_batch.py'
spec=importlib.util.spec_from_file_location('review_bms',src);b=importlib.util.module_from_spec(spec);spec.loader.exec_module(b)
node=next(x for x in ast.parse((HERE/'ui.py.reviewed.txt').read_text()).body if isinstance(x,ast.ClassDef) and x.name=='UI')
results=[]
for case in ['success','stop_at_dispatch','wrong_state','lost_reply','awake_failure']:
 f=HERE/'.private'/case;f.mkdir(parents=True,exist_ok=False)
 (f/'state').write_text('FOREIGN' if case=='wrong_state' else 'AWAITING_REENTRY');(f/'icon.intent').write_text('intent')
 (f/'config-common.sh').write_text('uitest(){ printf "clicked\\n" >> "$HERE/clicks"; }\n')
 (f/'launch-common.sh').write_text('')
 (f/'adoption-guard.sh').write_text('t13_adoption_guard(){ test ! -e "$HERE/stop"; }\n')
 record={'selected_icon':{'center':[736,507]}};env={'b':b,'a':types.SimpleNamespace(action='launch'),'record':record,'authority':{'root':str(f)},'out':f,'shlex':shlex,'time':time}
 exec(compile(ast.Module(body=[node],type_ignores=[]),'<exact-ui>','exec'),env)
 class MockTransport(env['UI']):
  def ready(self):
   if case=='stop_at_dispatch':(f/'stop').touch()
  def command(self,argv,timeout=60):
   assert argv[:4]==['mock-hdc','-t','test-serial','shell']
   cmd=argv[-1];self.calls.append(cmd)
   if 'uitest uiInput click' in cmd and case=='lost_reply':raise b.BatchStop('simulated lost reply; outcome unknown')
   if 'power-shell timeout' in cmd and case=='awake_failure':raise b.BatchStop('simulated awake failure')
   if cmd.startswith('power-shell'):
    # Retain production marker parsing; replace only unavailable fixture command.
    cmd=cmd.replace('power-shell dump -s',"printf 'OverrideTimeout=86400000ms\\n'").replace('power-shell timeout -o 86400000',':')
   run=subprocess.run(['sh','-c',cmd],capture_output=True,text=True,timeout=3)
   return run.returncode,run.stdout+run.stderr
 q=MockTransport.__new__(MockTransport);q.hdc=['mock-hdc'];q.serial='test-serial';q.calls=[];error=None
 try:q.shell('uitest uiInput click 736 507')
 except b.BatchStop as e:error=str(e)
 except b.AppFailure as e:error=str(e)
 clicks=len((f/'clicks').read_text().splitlines()) if (f/'clicks').exists() else 0
 assert len([x for x in q.calls if 'uitest uiInput click' in x])==1
 if case in ['success','awake_failure']:assert clicks==1 and record['clicked'] is True
 else:assert clicks==0 and not record.get('clicked') and record['ui_calls'][-1]['result']=='unknown'
 if case!='success':assert error is not None
 results.append({'case':case,'pass':True,'local_fixture_clicks':clicks,'clicked_record':record.get('clicked'),'ui_result':record['ui_calls'][-1]['result'],'error':None if error is None else error.replace(str(ROOT),'$LANE_REPO')})
print(json.dumps({'cases':results,'production_bms_sha256':hashlib.sha256(src.read_bytes()).hexdigest(),'raw_shell_marker_used':True,'device_calls':0},indent=2))
