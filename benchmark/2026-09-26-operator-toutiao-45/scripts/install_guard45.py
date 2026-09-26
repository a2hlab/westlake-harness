from board45 import *
from jit_cache45 import prepare_jit_cache
name=sys.argv[1];r=R/name;d=json.loads((r/'device-report.json').read_text())
update='--update' in sys.argv
if update:
 d['child']=int(dev('cat /data/local/tmp/operator45/child.pid').strip());d['parent']=int(dev('cat /data/local/tmp/operator45/parent.pid').strip())
 old=int(dev('cat /data/local/tmp/operator45/guard.pid').strip());dev('touch /data/local/tmp/operator45/stop; kill '+str(old));time.sleep(4)
 assert not dev('cat /proc/'+str(old)+'/stat 2>/dev/null').strip(),'old guard still alive'
 dev('rm -f /data/local/tmp/operator45/stop /data/local/tmp/operator45/guard.pid')
rows=[json.loads(s) for s in (r/'commands.jsonl').read_text().splitlines()]
parent=next(x['command'] for x in rows if x['command'].startswith('nohup ') and 'source_app_namespace' in x['command'])
spawn=next(x['command'] for x in rows if '/host_spawn /dev/unix' in x['command'])
prepare_jit_cache(dev,send,d['runtime'])
t=pathlib.Path(__file__).with_name('watchdog45.sh.in').read_text()
for key,val in {'RUNTIME':shlex.quote(d['runtime']),'STAGE':shlex.quote(d['stage']),'SOCKET':shlex.quote(d['socket']),'UID':'20010053','PARENT_COMMAND':parent,'SPAWN_COMMAND':spawn}.items():t=t.replace('@@'+key+'@@',val)
p=R/'watchdog45.sh';p.write_text(t)
assert not dev('cat /data/local/tmp/operator45/guard.pid 2>/dev/null').strip(),'guard already configured'
dev('mkdir -p /data/local/tmp/operator45 /data/local/tmp/operator45-crashes');send(p,'/data/local/tmp/operator45/watchdog.sh')
dev('chmod 755 /data/local/tmp/operator45/watchdog.sh; echo '+str(d['child'])+' > /data/local/tmp/operator45/child.pid; echo '+str(d['parent'])+' > /data/local/tmp/operator45/parent.pid; echo '+shlex.quote(d['runtime']+f'/private-tmp/adapter_child_{d["child"]}.stderr')+' > /data/local/tmp/operator45/child.stderr.path')
result=dev('nohup /system/bin/sh /data/local/tmp/operator45/watchdog.sh >/data/local/tmp/operator45/watchdog.log 2>&1 </dev/null & echo $!').strip();dev('echo '+result+' > /data/local/tmp/operator45/guard.pid')
(R/'guard.json').write_text(json.dumps({'pid':int(result),'initial_child':d['child'],'interval_seconds':3,'board_script':'/data/local/tmp/operator45/watchdog.sh','stop':'touch /data/local/tmp/operator45/stop; kill $(cat /data/local/tmp/operator45/guard.pid)','archive':'/data/local/tmp/operator45-crashes','stage':d['stage'],'runtime':d['runtime']},indent=2)+'\n');print('GUARD_STARTED',result)
