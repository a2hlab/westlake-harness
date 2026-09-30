#!/usr/bin/env python3
"""Read-only maps observer; captures all appspawn children, never calls a signal handler."""
import gzip,hashlib,json,shlex,sys,time,subprocess
from pathlib import Path
H=Path(__file__).resolve().parent;R=H.parents[1];sys.path.insert(0,str(R/'scripts/lab'));import lab_paths
phase=sys.argv[1] if len(sys.argv)>1 else 'n5'
serial='5ea34a4500000000000000001123012c';out=H/'maps';out.mkdir(exist_ok=True)
libs=['liboh_adapter_bridge.so','liboh_android_runtime.so','libappexecfwk_base.z.so','liblog.so','libbionic_compat.so']
cmd='ps -A -o PID,PPID,UID,NAME'
while not (H/'stop-watch').exists():
 t=time.time();p=subprocess.run([str(R/'benchmark/2026-09-30-n3-61b/transport/hdc_mac.sh'),'-t',serial,'shell',cmd],capture_output=True,timeout=25)
 data=p.stdout
 ps=[v for line in data.decode(errors='replace').splitlines() if len(v:=line.split())>=4 and v[0].isdigit() and v[1].isdigit() and v[2].isdigit()]
 parents={v[0] for v in ps if v[3]=='appspawn-x' and v[2]=='0'}
 children=[int(v[0]) for v in ps if v[1] in parents]
 if children:
  query='; '.join(f'echo MAPS_BEGIN:{pid}; cat /proc/{pid}/maps; echo MAPS_END:{pid}' for pid in children)
  m=subprocess.run([str(R/'benchmark/2026-09-30-n3-61b/transport/hdc_mac.sh'),'-t',serial,'shell',query],capture_output=True,timeout=25)
  data+=m.stdout
 digest=hashlib.sha256(data).hexdigest();f=out/(digest+'.txt.gz')
 if not f.exists():f.write_bytes(gzip.compress(data,mtime=0))
 rows=[];pid=None;maps=[]
 for line in data.decode(errors='replace').splitlines():
  if line.startswith('MAPS_BEGIN:'):pid=int(line.split(':')[1]);maps=[]
  elif line.startswith('MAPS_END:') and pid:
   counts={lib:sorted({tuple(x.split()[3:5]) for x in maps if len(x.split())>=6 and Path(x.split()[-1]).name==lib}) for lib in libs}
   rows.append(dict(pid=pid,libraries=counts,duplicate=any(len(v)>1 for v in counts.values())));pid=None
  elif pid:maps.append(line)
 with (H/('maps-observations.jsonl' if phase=='n5' else 'maps-observations-'+phase+'.jsonl')).open('a') as f:f.write(json.dumps(dict(phase=phase,time=t,file='maps/'+digest+'.txt.gz',returncode=p.returncode,processes=rows))+'\n')
 time.sleep(0.5)
