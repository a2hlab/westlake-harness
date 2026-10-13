"""Offline review: unchanged dispatcher, extended T0 transport fixture only."""
import hashlib,json,sys
from pathlib import Path
H=Path(__file__).resolve().parent
sys.path.insert(0,str(H/'snapshot'))
source=(H/'snapshot/test_dispatch.py').read_text()
rows=[]
def case(name,insertion='',replacement=None):
 text=source.replace('    commands.append(cmd)\n','    commands.append(cmd)\n'+insertion)
 if replacement:
  old,new=replacement;assert old in text;text=text.replace(old,new)
 ns={'__file__':str(H/'snapshot/test_dispatch.py'),'__name__':'review_fixture'}
 exec(compile(text,'review-fixture','exec'),ns)
 commands,error=ns['Dispatch']().run_case('cx-t0')
 assert error is not None,(name,'accepted')
 assert not any('unlock' in c for c in commands),(name,'unlocked')
 assert not any(len(c)>1 and c[1].endswith('/scripts/lab/board_run.py') for c in commands),(name,'second recovery window')
 rows.append({'case':name,'passed':True,'error':str(error).replace(str(H.resolve()),'$REVIEW'),'transport':'mocked','device_calls':0})
for phase in ['recover-retained','verify-recovered']:
 case(phase+' failure',f"    if {phase!r} in cmd:return SimpleNamespace(returncode=7)\n")
case('HWZZ failure',"    if len(cmd)>1 and cmd[1].endswith('activation_smoke.py'):return SimpleNamespace(returncode=7)\n")
case('held stderr',"    if 'held' in cmd:return SimpleNamespace(returncode=0,stdout=held,stderr='warning')\n")
case('held malformed',"    if 'held' in cmd:return SimpleNamespace(returncode=0,stdout='cx-t0',stderr='')\n")
case('held changed before unlock',"    if 'held' in cmd and sum('held' in x for x in commands)>1:return SimpleNamespace(returncode=0,stdout=held.replace('123','456'),stderr='')\n")
case('watch actual handoff SHA mismatch',replacement=("sha256=d.sha(q['batch_handoff'])","sha256='0'*64"))
case('handoff actual authorization SHA mismatch',replacement=("sha256=d.sha(ar)","sha256='0'*64"))
result={'reviewed_script_sha256':hashlib.sha256((H/'snapshot/serial_dispatch.py').read_bytes()).hexdigest(),'cases':rows,'passed':len(rows),'device_calls':0}
(H/'negative-results.json').write_text(json.dumps(result,indent=2)+'\n')
print(json.dumps(result,indent=2))
