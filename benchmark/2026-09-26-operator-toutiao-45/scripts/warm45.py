"""Preserve all app data; replace only this task's child/parent and mailbox."""
from board45 import *
oldname,name=sys.argv[1:3];old=R/oldname;r=R/name;assert not r.exists();r.mkdir()
d=json.loads((old/'device-report.json').read_text());runtime=d['runtime']
for key,path in [('child.stderr',runtime+f'/private-tmp/adapter_child_{d["child"]}.stderr'),('parent.log',d['stage']+'/parent.log')]:recv(path,old/key)
(r/'data-before.txt').write_text(dev(f'find {runtime}/app-data {runtime}/data {runtime}/webview-t-data -type f | head -n 100'))
dev('sync')
for key in ('child','parent'):
 p=d[key];st=dev(f'cat /proc/{p}/stat 2>/dev/null')
 if ') ' in st:
  start=st.rsplit(') ',1)[1].split()[19];now=dev(f'cat /proc/{p}/stat 2>/dev/null')
  if ') ' in now and now.rsplit(') ',1)[1].split()[19]==start:dev(f'kill -9 {p}')
assert not dev('cat /proc/[0-9]*/mountinfo 2>/dev/null | grep '+pathlib.Path(runtime).name,120).strip(),'live namespace'
dev('aa start -b org.westlake.imehost -a EntryAbility');time.sleep(1);dev('uinput -T -d 1150 1140 -u 1150 1140')
rows=[json.loads(s) for s in (old/'commands.jsonl').read_text().splitlines()]
dev('rm -f '+d['socket'])
c=next(x['command'] for x in rows if x['command'].startswith('nohup ') and 'source_app_namespace' in x['command'])
d['parent']=int(dev(c).strip())
for _ in range(120):
 if 'READY' in dev('if [ -S '+d['socket']+' ]; then echo READY; fi'):break
 time.sleep(.25)
else:raise RuntimeError('parent not ready')
c=next(x['command'] for x in rows if '/host_spawn /dev/unix' in x['command']);d['child']=int(re.search(r'result=0 pid=(\d+)',dev(c))[1])
uid=20010053;box=f'/proc/{d["child"]}/root/data/local/tmp/noice_tap.{d["child"]}'
dev(f': > {box}; chown {uid}:{uid} {box}; chmod 666 {box}; ln -sf {box} /data/local/tmp/noice_tap')
(r/'device-report.json').write_text(json.dumps(d,indent=2)+'\n');(r/'commands.jsonl').write_bytes((old/'commands.jsonl').read_bytes());(r/'run.sh').write_bytes((old/'run.sh').read_bytes())
(r/'data-provenance.json').write_text(json.dumps({'origin':oldname,'fresh':False,'cleared':[]},indent=2)+'\n')
print('OPERATOR45_WARM_LIVE',json.dumps({k:d[k] for k in ('parent','child','stage','runtime')}),flush=True)
