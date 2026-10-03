"""Read-only window infrastructure receipt; absence is unknown, never zero RSS."""
import datetime,json,subprocess,time,sys
from pathlib import Path
rows=[]
for line in subprocess.check_output(['ps','-axo','pid,rss,command'],text=True).splitlines()[1:]:
 p=line.strip().split(None,2)
 if len(p)==3 and 'OrbStack.app/' in p[2] and ' vmgr ' in p[2]:
  rows.append({'pid':int(p[0]),'rss_kib':int(p[1]),'command':p[2]})
t=time.monotonic()
try:
 r=subprocess.run(['orb','-m','a2hlab','true'],timeout=25,capture_output=True,text=True)
 rc=r.returncode;error=r.stderr
except subprocess.TimeoutExpired:
 rc=124;error='orb readiness timeout'
rss=sum(r['rss_kib'] for r in rows) if rows else None
report={'timestamp':datetime.datetime.now().astimezone().isoformat(),'vmgr':rows,'rss_kib':rss,'orb_rc':rc,'orb_latency_seconds':time.monotonic()-t,'error':error,'restart_required':rss is None or rss>3*1024*1024}
Path(sys.argv[1]).write_text(json.dumps(report,indent=2)+'\n')
print(json.dumps(report))
