"""VM-only, one clean profile and parent per round; guardian recovery never counts as survival."""
from boardrefined48 import *
from deploymentrefined48 import verify_components, deploy_stub
name,op=sys.argv[1:3];assert re.fullmatch(r'[a-z0-9-]+',name)
r=R/name
config=R/'config.json'
if not config.exists():
 config.write_bytes((R.parent/'metasec48/config.json').read_bytes())
 (R/'baseline.json').write_bytes((R.parent/'metasec48/baseline.json').read_bytes())
c=json.loads(config.read_text());runtime=c['runtime'];stage=c['stage']
src=runtime+'/lib/arm64-v8a/libmetasec_ml.so'
dst=runtime+'/app-data/'+PKG+'/app_lib/libmetasec_ml.so'
def collect(d):
 if live(d['child'],d['birth']):
  recv('/proc/'+str(d['child'])+'/maps',r/'maps.txt')
  (r/'identity.txt').write_text(dev('cat /proc/'+str(d['child'])+'/status /proc/'+str(d['child'])+'/attr/current'))
 recv(runtime+f"/private-tmp/adapter_child_{d['child']}.stderr",r/'child.stderr')
 recv(stage+'/parent.log',r/'parent.log')
 paths=dev('find /data/log/faultlog -type f -name "*-'+str(d['child'])+'-*" 2>/dev/null')
 (r/'fault-paths.txt').write_text(paths)
 for path in paths.splitlines():
  if path.startswith('/data/log/faultlog/'):
   recv(path,r/(path.rsplit('/',1)[-1]+'.txt'))
 (r/'post-state.txt').write_text(dev('date; cat /proc/uptime; cat '+D+'/child.pid; ls -lZ '+dst+' '+src+'; readlink '+dst+'; sha256sum '+src+'; cat '+D+'/startup-settings.log; cat /data/local/tmp/operator45-crashes/INDEX'))
 verify_components(runtime,r/'components-after-observation.json')
 p=subprocess.run(['bash',str(ROOT/'scripts/assert_heap_corruption_gone.sh'),str(r)],capture_output=True,text=True)
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
 base=json.loads((R/'baseline.json').read_text())
 profile=runtime+'/profile-backups/refined48-before-'+name
 assert not dev('ls -d '+profile+' 2>/dev/null').strip()
 dev('mkdir -p '+profile)
 for part in ('app-data','data','webview-t-data'):dev('if [ -d '+runtime+'/'+part+' ]; then mv '+runtime+'/'+part+' '+profile+'/'+part+'; fi')
 deploy_stub(runtime,r)
 verify_components(runtime,r/'components-before-start.json')
 dev(f'mkdir -p {runtime}/data/dalvik-cache/arm64 {runtime}/app-data/{PKG}/code_cache/art-volatile {runtime}/app-data/{PKG}/app_webview {runtime}/app-data/org.westlake.imehost {runtime}/webview-t-data; chown -R 20010053:20010053 {runtime}/data {runtime}/app-data {runtime}/webview-t-data; chcon -R u:object_r:data_app_el2_file:s0 {runtime}/app-data/{PKG}')
 dev('echo 1048576 > /proc/sys/vm/max_map_count; power-shell timeout -o 86400000; power-shell wakeup; aa start -b org.westlake.imehost -a EntryAbility; rm -f '+c['socket'])
 setting=dev('cat /proc/sys/vm/max_map_count');assert setting.strip()=='1048576',setting
 (r/'max-map-count.txt').write_text(setting)
 c['parent']=int(dev(c['parent_command']).strip())
 for _ in range(120):
  if 'READY' in dev('if [ -S '+c['socket']+' ]; then echo READY; fi'):break
  time.sleep(.25)
 else:raise RuntimeError('parent socket not ready')
 sys.path.insert(0,str(ROOT.parent/'2026-09-26-operator-toutiao-45/scripts'))
 from jit_cache45 import prepare_jit_cache
 (r/'jit-prepare.txt').write_text(prepare_jit_cache(dev,send,runtime,c['parent']))
 c['child']=int(re.search(r'result=0 pid=(\d+)',dev(c['spawn_command']))[1])
 s=stat(c['child']);c['birth']=s.rsplit(') ',1)[1].split()[19] if s else None
 c['profile_backup']=profile;c['real_metasec_sha256']=base['metasec_sha256'];c['candidate_metasec_sha256']=dev('sha256sum '+src).split()[0]
 (r/'device-report.json').write_text(json.dumps(c,indent=2)+'\n')
 t=(ROOT.parent/'2026-09-26-operator-toutiao-45/scripts/watchdog45.sh.in').read_text()
 for k,v in {'RUNTIME':shlex.quote(runtime),'STAGE':shlex.quote(stage),'SOCKET':shlex.quote(c['socket']),'UID':'20010053','PARENT_COMMAND':c['parent_command'],'SPAWN_COMMAND':c['spawn_command']}.items():t=t.replace('@@'+k+'@@',v)
 p=r/'watchdog.sh';p.write_text(t);send(p,D+'/watchdog.sh')
 dev(f'chmod 755 {D}/watchdog.sh; echo {c["child"]} > {D}/child.pid; echo {c["parent"]} > {D}/parent.pid; echo {runtime}/private-tmp/adapter_child_{c["child"]}.stderr > {D}/child.stderr.path; rm -f {D}/preseed48.enabled; rm -f {D}/guard.pid {D}/stop; rmdir {D}/guard.lock 2>/dev/null')
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
 elif op=='swipe':
  assert live(d['child'],d['birth']) and dev('cat '+D+'/child.pid').strip()==str(d['child']),'original exited'
  xy=sys.argv[3:];assert len(xy)==4 and all(x.isdigit() for x in xy)
  cmd='cat /proc/uptime; uinput -T -m '+' '.join(xy)+' 800'
  out=dev(cmd)
  with (r/'inputs.jsonl').open('a') as f:f.write(json.dumps({'command':cmd,'output':out,'epoch':time.time()})+'\n')
  print(out)
 elif op=='collect':collect(d)
 elif op=='monitor':
  duration=int(sys.argv[3]);start=time.monotonic();lastshot=-1
  segment=1
  while (r/f'result-segment-{segment}.json').exists():segment+=1
  if (r/'result.json').exists():
   (r/f'result-segment-{segment}.json').write_bytes((r/'result.json').read_bytes())
   segment+=1
  shotprefix='monitor' if segment==1 else f'monitor-segment-{segment}'
  while True:
   elapsed=time.monotonic()-start
   out=dev(f"cat /proc/uptime; cat {D}/child.pid; cat /proc/{d['child']}/stat; ls -lZ {dst}; readlink {dst}; wc -l /proc/{d['child']}/maps; grep -E 'libnpth_(xasan|heap_tracker)' /proc/{d['child']}/maps; grep -E '^(VmRSS|VmSize|Threads):' /proc/{d['child']}/status")
   with (r/'samples.jsonl').open('a') as f:f.write(json.dumps({'elapsed':elapsed,'output':out})+'\n')
   alive=live(d['child'],d['birth'])
   if not alive or elapsed>=duration:break
   if int(elapsed)//60>lastshot:lastshot=int(elapsed)//60;shot(r,shotprefix+'-'+str(lastshot*60))
   time.sleep(3)
  shot(r,shotprefix+'-end');collect(d)
  result={'round':name,'original_child':d['child'],'observed_seconds':elapsed,'original_alive_at_end':alive,'birth':d['birth']}
  (r/'result.json').write_text(json.dumps(result,indent=2)+'\n');print('ROUND_RESULT',json.dumps(result),flush=True)
 else:raise SystemExit(op)
