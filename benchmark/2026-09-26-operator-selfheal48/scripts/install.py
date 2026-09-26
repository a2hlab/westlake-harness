from pathlib import Path
import sys,json,hashlib
p=Path(__file__).with_name('board_api.py');sys.argv=[str(p),'install','inspect'];x={'__file__':str(p)};exec(p.read_text(),x)
r=x['r'];r.mkdir(exist_ok=True);dev=x['dev'];hdc=x['hdc'];F='/data/local/tmp/operator45/selfheal48'
pre=dev('echo APP; pidof com.ss.android.article.news; echo PARENT; pidof appspawn-x; echo GUARD; test -f /data/local/tmp/operator45/stop && test -f /data/local/tmp/operator45/fresh48/stop && test ! -d /data/local/tmp/operator45/fresh48/lock && echo STOPPED; sha256sum /data/local/tmp/operator45/screen-gate',10);(r/'preflight.txt').write_text(pre)
assert not pre.split('APP\n')[1].split('PARENT')[0].strip();assert not pre.split('PARENT\n')[1].split('GUARD')[0].strip();assert 'STOPPED' in pre
expected={}
for l in (x['R'].parent/'r1control48/deployment/after-hashes.txt').read_text().splitlines():
 h,n=l.split(maxsplit=1);expected[n]=h
out=dev('sha256sum '+' '.join(expected),20);(r/'baseline-hashes.txt').write_text(out)
for n,h in expected.items():assert h+'  '+n in out,n
s=Path(__file__).with_name('watchdog.sh.in').read_text()
for k,v in {'RUNTIME':x['rt'],'STAGE':x['stage'],'SOCKET':x['c']['socket']}.items():s=s.replace('@@'+k+'@@',v)
assert '@@' not in s
(r/'watchdog.sh').write_text(s)
for name,k in [('start-parent.sh','parent_command'),('spawn.sh','spawn_command')]:
 (r/name).write_text('#!/system/bin/sh\n'+x['c'][k]+'\n')
print(dev('test ! -d '+F+'/lock || exit 9; mkdir -p '+F+'; touch '+F+'/stop',10))
for name in ['watchdog.sh','start-parent.sh','spawn.sh']:hdc(['file','send',name,F+'/'+name],r,10)
hdc(['file','send','screen-gate',F+'/screen-gate'],x['R'],10)
s=dev('chmod 755 '+F+'/screen-gate; chmod 755 '+F+'/*.sh; /system/bin/sh -n '+F+'/watchdog.sh; sha256sum '+F+'/*.sh',10);(r/'installed.txt').write_text(s);print(s)
