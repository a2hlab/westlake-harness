"""Read-only per-window VM health receipt. Never restarts or takes device locks."""
import datetime,json,subprocess,time,sys
from pathlib import Path
rows=[]
for line in subprocess.run(['ps','-axo','pid=,rss=,command='],capture_output=True,text=True,check=True).stdout.splitlines():
 if 'OrbStack Helper vmgr' in line:
  fields=line.split(None,2);rows.append({'pid':int(fields[0]),'rss_kib':int(fields[1])})
t=time.monotonic()
try:
 p=subprocess.run(['orb','-m','a2hlab','true'],capture_output=True,text=True,timeout=25)
 probe={'rc':p.returncode,'stdout':p.stdout,'stderr':p.stderr,'latency_seconds':time.monotonic()-t}
except subprocess.TimeoutExpired:
 probe={'rc':'timeout','latency_seconds':time.monotonic()-t}
r={'at':datetime.datetime.now().astimezone().isoformat(),'vmgr':rows,'orb':probe,'restart_required_before_lock':any(x['rss_kib']>3*1024*1024 for x in rows)}
Path(sys.argv[1]).write_text(json.dumps(r,indent=2)+'\n');print(json.dumps(r))
