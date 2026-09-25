"""VM-only, one clean profile and parent per round; guardian recovery never counts as survival."""
from board48 import *
name,op=sys.argv[1:3];assert re.fullmatch(r'[a-z0-9-]+',name)
r=R/name
old=R.parent/'operator45'
config=R/'config.json'
if not config.exists():
 c=json.loads((old/'morning46-handoff/device-report.json').read_text())
 rows=[json.loads(x) for x in (old/'warm/commands.jsonl').read_text().splitlines()]
 c['parent_command']=next(x['command'] for x in rows if x['command'].startswith('nohup ') and 'source_app_namespace' in x['command'])
 c['spawn_command']=next(x['command'] for x in rows if '/host_spawn /dev/unix' in x['command'])
 config.write_text(json.dumps(c,indent=2)+'\n')
c=json.loads(config.read_text());runtime=c['runtime'];stage=c['stage']
src=runtime+'/lib/arm64-v8a/libmetasec_ml.so'
dst=runtime+'/app-data/'+PKG+'/app_lib/libmetasec_ml.so'
def collect(d):
 recv(runtime+f'/private-tmp/adapter_child_{d["child"]}.stderr',r/'child.stderr')
 recv(stage+'/parent.log',r/'parent.log')
 (r/'post-state.txt').write_text(dev('date; cat /proc/uptime; cat '+D+'/child.pid; ls -lZ '+dst+' '+src+'; readlink '+dst+'; sha256sum '+src+'; cat '+D+'/startup-settings.log; cat /data/local/tmp/operator45-crashes/INDEX'))
 p=subprocess.run(['bash',str(ROOT/'scripts/assert_metasec_exit_gone.sh'),str(r/'child.stderr')],capture_output=True,text=True)
 (r/'assertions.txt').write_text(p.stdout+p.stderr+'\nEXIT='+str(p.returncode)+'\n')
 print(p.stdout,flush=True)
if op=='prepare':
 assert not r.exists();r.mkdir()
 guard=dev('cat '+D+'/guard.pid').strip()
 dev('touch '+D+'/stop; kill '+guard);time.sleep(4)
 assert not live(guard),'guardian did not stop'
 child=dev('cat '+D+'/child.pid').strip();parent=dev('cat '+D+'/parent.pid').strip()
 (r/'before.txt').write_text(dev('date; cat /proc/uptime; pidof '+PKG+'; cat '+D+'/child.pid '+D+'/parent.pid'))
 recv(runtime+'/private-tmp/adapter_child_'+child+'.stderr',r/'previous-child.stderr')
 for pid in dev('pidof '+PKG).split():kill_checked(pid)
 kill_checked(parent)
 assert not any(live(pid) for pid in dev('pidof '+PKG).split())
 backup='/data/local/tmp/operator45-crashes/metasec48-original'
 if not (R/'baseline.json').exists():
  dev('mkdir -p '+backup+'; cp '+D+'/watchdog.sh '+backup+'/watchdog.sh; cp '+src+' '+backup+'/libmetasec_ml.so')
  recv(src,R/'original-libmetasec_ml.so');recv(D+'/watchdog.sh',R/'original-watchdog.sh')
  (R/'baseline.json').write_text(json.dumps({'metasec_sha256':sha(R/'original-libmetasec_ml.so'),'backup':backup},indent=2)+'\n')
 base=json.loads((R/'baseline.json').read_text())
 before=dev('sha256sum '+src).split()[0]
 if before!=base['metasec_sha256']:
  dev('cp '+src+' '+backup+'/mutated-before-'+name+'.so; cp '+backup+'/libmetasec_ml.so '+src)
  assert dev('sha256sum '+src).split()[0]==base['metasec_sha256']
 profile=runtime+'/profile-backups/metasec48-before-'+name
 assert not dev('ls -d '+profile+' 2>/dev/null').strip()
 dev('mkdir -p '+profile)
 for part in ('app-data','data','webview-t-data'):dev('if [ -d '+runtime+'/'+part+' ]; then mv '+runtime+'/'+part+' '+profile+'/'+part+'; fi')
 if name.startswith('a1-'):
  artifact=pathlib.Path.home()/'a2hlab/ws/out-operator48/libart.so'
  expected='ae2cb1829ffa9eca08e1a0fe816edfc33bbe0e1ca3e2f43aaa99e522924a8937'
  assert sha(artifact)==expected
  target=runtime+'/libart.so';prior=dev('sha256sum '+target).split()[0]
  assert prior in ('009a08fb8282b4ed8b857eaf014038adb93bb5cac0daa5d32ab89a13f29c8bbc',expected)
  if prior!=expected:
   dev('cp '+target+' '+backup+'/libart.'+prior+'.so')
   send(artifact,target+'.a1');dev('chmod 644 '+target+'.a1; mv '+target+'.a1 '+target)
  assert dev('sha256sum '+target).split()[0]==expected
  (r/'a1-deployment.json').write_text(json.dumps({'before':prior,'after':expected,'backup':backup,'target':target},indent=2)+'\n')
 dev(f'mkdir -p {runtime}/data/dalvik-cache/arm64 {runtime}/app-data/{PKG}/code_cache/art-volatile {runtime}/app-data/{PKG}/app_webview {runtime}/app-data/org.westlake.imehost {runtime}/webview-t-data; chown -R 20010053:20010053 {runtime}/data {runtime}/app-data {runtime}/webview-t-data; chcon -R u:object_r:data_app_el2_file:s0 {runtime}/app-data/{PKG}')
 send(ROOT/'scripts/preseed_metasec_applib.sh',runtime+'/preseed_metasec48.sh')
 dev('chmod 755 '+runtime+'/preseed_metasec48.sh; echo 1048576 > /proc/sys/vm/max_map_count; power-shell timeout -o 86400000; power-shell wakeup; aa start -b org.westlake.imehost -a EntryAbility; rm -f '+c['socket'])
 c['parent']=int(dev(c['parent_command']).strip())
 for _ in range(120):
  if 'READY' in dev('if [ -S '+c['socket']+' ]; then echo READY; fi'):break
  time.sleep(.25)
 else:raise RuntimeError('parent socket not ready')
 hook=f'/bin/nsenter -t {c["parent"]} -m /system/bin/sh /data/local/tmp/asx/preseed_metasec48.sh'
 if name.startswith('a2-'):
  out=dev(hook+'; echo HOOK_RC=$?');(r/'preseed.txt').write_text(out);assert 'HOOK_RC=0' in out
 check=dev(f'ls -lZ {dst} {src}; readlink {dst}; sha256sum {src}; cat /proc/{c["parent"]}/mountinfo')
 (r/'preseed-identity.txt').write_text(check)
 if name.startswith('a2-'):assert '/data/local/tmp/asx/lib/arm64-v8a/libmetasec_ml.so' in check
 c['child']=int(re.search(r'result=0 pid=(\d+)',dev(c['spawn_command']))[1])
 s=stat(c['child']);c['birth']=s.rsplit(') ',1)[1].split()[19] if s else None
 c['profile_backup']=profile;c['original_metasec_sha256']=base['metasec_sha256']
 (r/'device-report.json').write_text(json.dumps(c,indent=2)+'\n')
 t=(ROOT.parent/'2026-09-26-operator-toutiao-45/scripts/watchdog45.sh.in').read_text()
 for k,v in {'RUNTIME':shlex.quote(runtime),'STAGE':shlex.quote(stage),'SOCKET':shlex.quote(c['socket']),'UID':'20010053','PARENT_COMMAND':c['parent_command'],'SPAWN_COMMAND':c['spawn_command']}.items():t=t.replace('@@'+k+'@@',v)
 p=r/'watchdog.sh';p.write_text(t);send(p,D+'/watchdog.sh')
 toggle='touch' if name.startswith('a2-') else 'rm -f'
 dev(f'chmod 755 {D}/watchdog.sh; echo {c["child"]} > {D}/child.pid; echo {c["parent"]} > {D}/parent.pid; echo {runtime}/private-tmp/adapter_child_{c["child"]}.stderr > {D}/child.stderr.path; {toggle} {D}/preseed48.enabled; rm -f {D}/guard.pid {D}/stop; rmdir {D}/guard.lock 2>/dev/null')
 g=dev(f'nohup /system/bin/sh {D}/watchdog.sh >{D}/watchdog.log 2>&1 </dev/null & echo $!').strip();dev('echo '+g+' > '+D+'/guard.pid')
 print('ROUND_STARTED',name,c['child'],c['parent'],'GUARD',g,flush=True)
else:
 d=json.loads((r/'device-report.json').read_text())
 if op=='shot':shot(r,sys.argv[3])
 elif op=='input':
  assert live(d['child'],d['birth']) and dev('cat '+D+'/child.pid').strip()==str(d['child']),'bound original exited; no input to replacement'
  xy=sys.argv[3:];assert len(xy)==2 and all(x.isdigit() for x in xy)
  cmd='cat /proc/uptime; uinput -T -d '+' '.join(xy)+' -u '+' '.join(xy)
  out=dev(cmd)
  with (r/'inputs.jsonl').open('a') as f:f.write(json.dumps({'command':cmd,'output':out,'epoch':time.time()})+'\n')
  print(out)
 elif op=='collect':collect(d)
 elif op=='monitor':
  duration=int(sys.argv[3]);start=time.monotonic();lastshot=-1
  while True:
   elapsed=time.monotonic()-start
   out=dev(f'cat /proc/uptime; cat {D}/child.pid; cat /proc/{d["child"]}/stat; ls -lZ {dst}; readlink {dst}; wc -l /proc/{d["child"]}/maps')
   with (r/'samples.jsonl').open('a') as f:f.write(json.dumps({'elapsed':elapsed,'output':out})+'\n')
   alive=live(d['child'],d['birth'])
   if not alive or elapsed>=duration:break
   if int(elapsed)//60>lastshot:lastshot=int(elapsed)//60;shot(r,'monitor-'+str(lastshot*60))
   time.sleep(3)
  shot(r,'monitor-end');collect(d)
  result={'round':name,'original_child':d['child'],'observed_seconds':elapsed,'original_alive_at_end':alive,'birth':d['birth']}
  (r/'result.json').write_text(json.dumps(result,indent=2)+'\n');print('ROUND_RESULT',json.dumps(result),flush=True)
 else:raise SystemExit(op)
