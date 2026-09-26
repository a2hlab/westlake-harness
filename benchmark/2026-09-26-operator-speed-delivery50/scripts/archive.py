from pathlib import Path
import sys,json
p=Path(__file__).with_name('board_api.py');sys.argv=[str(p),'board-archive','inspect'];x={'__file__':str(p)};exec(p.read_text(),x);r=x['r'];r.mkdir(exist_ok=True);dev=x['dev'];recv=x['recv'];F='/data/local/tmp/operator45/selfheal48';C='/data/local/tmp/operator45-crashes'
for name in ['events.log','metrics.log','ui.log','guardian.log','state','instance.txt','guardian.pid','sequence','watchdog.sh','start-parent.sh','spawn.sh','stop']:
 try:recv(F+'/'+name,r/name,10)
 except RuntimeError:
  if name!='stop':raise
paths=dev('find '+F+' -maxdepth 1 -type f -name "*.png"; find '+C+' -maxdepth 2 -path "'+C+'/selfheal-*/*" -type f',10)
for src in paths.splitlines():
 if not src.startswith((F+'/',C+'/selfheal-')):continue
 dst=r/(('guardian/'+src[len(F)+1:]) if src.startswith(F+'/') else ('crashes/'+src[len(C)+1:]))
 recv(src,dst,20)
recv(C+'/INDEX',r/'INDEX',10)
print('ARCHIVED',len(paths.splitlines()))
