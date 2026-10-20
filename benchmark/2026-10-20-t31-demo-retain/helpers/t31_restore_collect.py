from pathlib import Path
import json,subprocess,time
from window_paths import BASE,WINDOW,context,budget
repo=Path.cwd();base=BASE;w=WINDOW;c=context();deadline=time.monotonic()+budget(c,True);boot=json.loads((w/'restored-boot.json').read_text())['boot']
jobs=[('restored-snapshot',['python3','scripts/lab/board_state_snapshot.py',c['serial'],'--out',str(w/'restored-snapshot'),'--plan',str(base/'t16-reviewed-snapshot-plan.json'),'--hdc',c['hdc'],'--label','T31 restored original runtime after fresh boot']),('restored-supplement',['python3','benchmark/2026-10-20-t16-snapshot-scope/collect_supplement.py','--execute','--repo',str(repo),'--out',str(w/'restored-supplement'),'--hdc',c['hdc'],'--boot',boot,'--holder',c['holder']])]
for tag,a in jobs:
 assert time.monotonic()<deadline
 h=subprocess.run(['bash','scripts/lab/board_note.sh','held',c['serial']],capture_output=True,timeout=min(5,deadline-time.monotonic()));assert h.returncode==0 and h.stdout.decode().strip()==c['holder']
 (w/(tag+'.argv.json')).write_text(json.dumps(a))
 with (w/(tag+'.stdout')).open('wb') as so,(w/(tag+'.stderr')).open('wb') as se:
  r=subprocess.run(a,stdout=so,stderr=se,timeout=min(150,deadline-time.monotonic()))
 (w/(tag+'.rc')).write_text(str(r.returncode));print(tag,r.returncode,flush=True);assert r.returncode==0
