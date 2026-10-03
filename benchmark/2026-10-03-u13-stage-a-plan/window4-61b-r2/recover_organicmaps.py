"""RUNBOOK OrganicMaps recovery: exact BMS UID/PPID guarded batched drain."""
import json,sys,time
from pathlib import Path
M=Path(__file__).resolve().parents[4]/'westlake-harness'
sys.path.insert(0,str(M/'scripts/lab'))
import u7_executor as u
out=Path(sys.argv[1]);out.mkdir(parents=True,exist_ok=True)
io=u.DeviceIO('61b0657200000000000000000324012c','cx-t0',out)
uid=io.b.parse_bundle(io.shell('bm dump -n app.organicmaps'),'app.organicmaps')['uid']
assert type(uid) is int and uid>=20000000
for attempt in range(4):
 rows=io.ps();parents=[r for r in rows if r['name']=='appspawn-x' and r['uid']==0 and r['ppid']==1]
 residual=[r for r in rows if r['name']=='appspawn-x' and r['uid']!=0]
 receipt={'attempt':attempt,'uid':uid,'boot':io.boot,'before':rows}
 if not residual:
  io.shell('begetctl stop_service appspawn-x');receipt['after']=io.ps()
  (out/f'drain-{attempt}.json').write_text(json.dumps(receipt,indent=2))
  assert not any(r['name']=='appspawn-x' for r in receipt['after'])
  print('DRAIN_AND_SERVICE_STOP_PASS',flush=True);break
 assert len(parents)==1 and all(r['uid']==uid and r['ppid']==parents[0]['pid'] for r in residual),'unidentified owner'
 commands=[]
 for r in residual:
  pid,ppid=r['pid'],r['ppid']
  commands.append(r"""if [ -d /proc/{pid} ]; then test "$(sed -n 's/^Uid:[[:space:]]*\([0-9]*\).*/\1/p' /proc/{pid}/status)" = {uid} && test "$(sed -n 's/^PPid:[[:space:]]*\([0-9]*\).*/\1/p' /proc/{pid}/status)" = {ppid} && kill -9 {pid}; fi""".format(pid=pid,uid=uid,ppid=ppid))
 command='\n'.join(commands)
 (out/f'drain-{attempt}.sh').write_text(command)
 io.shell(command);receipt['after']=io.ps()
 (out/f'drain-{attempt}.json').write_text(json.dumps(receipt,indent=2))
 print('DRAIN',attempt,len(residual),flush=True)
else:raise RuntimeError('persistent respawn: retain lock')
