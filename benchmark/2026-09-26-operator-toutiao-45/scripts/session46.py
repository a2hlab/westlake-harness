"""VM: bounded observation of the operator instance; never restarts or injects input."""
from board45 import *
name=sys.argv[1];r=R/name;r.mkdir(exist_ok=True)
d=json.loads((R/'morning46-first/device-report.json').read_text())
d['child']=int(dev('cat /data/local/tmp/operator45/child.pid').strip())
d['parent']=int(dev('cat /data/local/tmp/operator45/parent.pid').strip())
(r/'device-report.json').write_text(json.dumps(d,indent=2)+'\n')
root=pathlib.Path(__file__).resolve().parents[1]
if len(sys.argv)==2:print('BOUND',name,d['child']);raise SystemExit
assert sys.argv[2]=='monitor'
duration=int(sys.argv[3]);begin=time.monotonic();shots=[90,duration]
while True:
 elapsed=time.monotonic()-begin
 command=f'cat /proc/uptime; cat /data/local/tmp/operator45/child.pid /data/local/tmp/operator45/guard.pid; cat /proc/{d["child"]}/stat; wc -l /proc/{d["child"]}/maps; cat /proc/{d["child"]}/status; cat /proc/sys/vm/max_map_count; cat /data/local/tmp/operator45/sequence'
 state=dev(command)
 with (r/'stability.jsonl').open('a') as f:f.write(json.dumps({'elapsed':elapsed,'command':command,'output':state})+'\n')
 if shots and elapsed>=shots[0]:
  sec=shots.pop(0);remote='/data/local/tmp/operator45-stability.jpeg'
  dev('snapshot_display -f '+remote+' >/dev/null');recv(remote,r/f'stable-{sec}s.jpeg')
  p=root/'preview'/name/f'stable-{sec}s.jpeg';p.parent.mkdir(parents=True,exist_ok=True);p.write_bytes((r/f'stable-{sec}s.jpeg').read_bytes());print('SHOT',sec,flush=True)
 if elapsed>=duration:break
 time.sleep(3)
recv(d['runtime']+f'/private-tmp/adapter_child_{d["child"]}.stderr',r/'child.stderr')
recv(d['stage']+'/parent.log',r/'parent.log')
s=(r/'child.stderr').read_text(errors='replace')
lines=[x for x in s.splitlines() if x.startswith(('[B47-SLA] ENTRY','[ABILITY38-RESUMED]','Fatal signal')) or (len(x)<3000 and any(k in x for k in ['UnsatisfiedLinkError','GLES library translated','GrGLInterface creation failed','InitializeGL failure']))]
(r/'lifecycle-errors.txt').write_text('\n'.join(lines)+'\n')
(r/'guard-final.txt').write_text(dev('cat /data/local/tmp/operator45-crashes/INDEX; cat /data/local/tmp/operator45/startup-settings.log; cat /data/local/tmp/operator45/child.pid /data/local/tmp/operator45/parent.pid /data/local/tmp/operator45/guard.pid; cat /data/local/tmp/operator45/child.stderr.path; pidof com.ss.android.article.news'))
print('MONITOR_COMPLETE',d['child'],flush=True)
