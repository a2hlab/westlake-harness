from pathlib import Path
import sys,json,hashlib
p=Path(__file__).with_name('warm48.py');sys.argv=[str(p),'guardian-install','inspect'];x={'__file__':str(p)};exec(p.read_text().split('if op in (')[0],x);r=x['r'];r.mkdir(exist_ok=True);c=x['c'];dev=x['dev'];hdc=x['hdc']
s=Path(__file__).with_name('fresh-watchdog.sh.in').read_text()
for k,v in {'RUNTIME':x['rt'],'STAGE':x['stage'],'SOCKET':c['socket'],'PARENT_COMMAND':'timeout 20 /system/bin/sh /data/local/tmp/operator45/fresh48/start-parent.sh','SPAWN_COMMAND':'timeout 15 /system/bin/sh /data/local/tmp/operator45/fresh48/spawn.sh'}.items():s=s.replace('@@'+k+'@@',v)
assert '@@' not in s
(r/'fresh-watchdog.sh').write_text(s)
(r/'start-parent.sh').write_text('#!/system/bin/sh\n'+c['parent_command']+'\n')
(r/'spawn.sh').write_text('#!/system/bin/sh\n'+c['spawn_command']+'\n')
print(dev('mkdir -p /data/local/tmp/operator45/fresh48; touch /data/local/tmp/operator45/fresh48/stop /data/local/tmp/operator45/stop',5))
for name in ('fresh-watchdog.sh','start-parent.sh','spawn.sh'):
 hdc(['file','send',name,'/data/local/tmp/operator45/fresh48/'+name],r,10)
print(dev('chmod 755 /data/local/tmp/operator45/fresh48/*.sh; /system/bin/sh -n /data/local/tmp/operator45/fresh48/fresh-watchdog.sh; sha256sum /data/local/tmp/operator45/fresh48/*.sh /data/local/tmp/operator45/screen-gate',5))
