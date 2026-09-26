"""Read-only evidence capture while board supervisor remains in control."""
from pathlib import Path
import sys,json,time
label=sys.argv[1];p=Path(__file__).with_name('board_api.py');sys.argv=[str(p),'capture-'+label,'inspect'];x={'__file__':str(p)};exec(p.read_text(),x);r=x['r'];r.mkdir(exist_ok=True);dev=x['dev'];recv=x['recv'];F='/data/local/tmp/operator45/selfheal48'
s=dev('cat '+F+'/instance.txt',5);(r/'instance.txt').write_text(s);d=dict(l.split('=',1) for l in s.splitlines());pid=d['child']
for name in ['state','events.log','metrics.log','ui.log','guardian.log','watchdog.sh','start-parent.sh','spawn.sh']:
 recv(F+'/'+name,r/name,10)
(r/'process-state.txt').write_text(dev('cat /proc/uptime; echo APP; pidof com.ss.android.article.news; echo PARENT; pidof appspawn-x; cat /proc/'+pid+'/status; free -m; cat /proc/meminfo',8))
for n in ['child.stderr','parent.log']:
 src=x['rt']+'/private-tmp/adapter_child_'+pid+'.stderr' if n=='child.stderr' else x['stage']+'/parent.log';recv(src,r/n,15)
raw='/data/local/tmp/selfheal48-evidence.maps';dev('cat /proc/'+pid+'/maps > '+raw,5);recv(raw,r/'live.maps',8)
names=['libnpth.so','libmetasec_ml.so','libgodzilla-memsponge.so','libgodzilla-sysopt.so','libmonitorcollector-lib.so','libsscronet.so','libbytehook.so','libshadowhook.so']
paths=' '.join('/proc/'+pid+'/root/data/local/tmp/asx/lib/arm64-v8a/'+n for n in names)
(r/'native-identity.txt').write_text(dev('sha256sum '+paths+'; stat -c "%i %s %n" '+paths,10))
(r/'terminal-birth.txt').write_text(dev('cat /proc/'+pid+'/stat',5))
print('CAPTURED',label,pid)
