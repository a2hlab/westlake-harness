"""VM-only: install the four accepted patches into the existing operator45 runtime."""
from board45 import *
r=R/'morning46';r.mkdir(exist_ok=True)
d=json.loads((R/'warm/device-report.json').read_text())
root=pathlib.Path(__file__).resolve().parents[1]
cmd=sys.argv[1]
def checked_kill(pid):
 st=dev(f'cat /proc/{pid}/stat 2>/dev/null')
 if ') ' not in st:return
 birth=st.rsplit(') ',1)[1].split()[19]
 now=dev(f'cat /proc/{pid}/stat 2>/dev/null')
 if ') ' in now and now.rsplit(') ',1)[1].split()[19]==birth:dev(f'kill -9 {pid}')
def launch(name):
 out=R/name;assert not out.exists();out.mkdir()
 rows=[json.loads(x) for x in (R/'warm/commands.jsonl').read_text().splitlines()]
 parent=next(x['command'] for x in rows if x['command'].startswith('nohup ') and 'source_app_namespace' in x['command'])
 spawn=next(x['command'] for x in rows if '/host_spawn /dev/unix' in x['command'])
 dev('echo 1048576 > /proc/sys/vm/max_map_count; power-shell timeout -o 86400000; power-shell wakeup; aa start -b org.westlake.imehost -a EntryAbility')
 dev('rm -f '+d['socket']);d['parent']=int(dev(parent).strip())
 for _ in range(120):
  if 'READY' in dev('if [ -S '+d['socket']+' ]; then echo READY; fi'):break
  time.sleep(.25)
 else:raise RuntimeError('parent socket not ready')
 d['child']=int(re.search(r'result=0 pid=(\d+)',dev(spawn))[1])
 box=f'/proc/{d["child"]}/root/data/local/tmp/noice_tap.{d["child"]}'
 dev(f': > {box}; chown 20010053:20010053 {box}; chmod 666 {box}; ln -sf {box} /data/local/tmp/noice_tap')
 (out/'device-report.json').write_text(json.dumps(d,indent=2)+'\n')
 (out/'commands.jsonl').write_bytes((R/'warm/commands.jsonl').read_bytes())
 recv(d['runtime']+'/run.sh',out/'run.sh')
 print('LIVE',name,d['child'],d['parent'],flush=True)
if cmd=='deploy':
 assert not (r/'deployment.json').exists(),'already deployed'
 # Stop the resident guardian before archiving/patching the old instance.
 guard=dev('cat /data/local/tmp/operator45/guard.pid').strip()
 dev('touch /data/local/tmp/operator45/stop; kill '+guard);time.sleep(4)
 assert not dev('cat /proc/'+guard+'/stat 2>/dev/null').strip()
 archive='/data/local/tmp/operator45-crashes/morning46-upgrade'
 dev('mkdir -p '+archive+'; cp /data/local/tmp/operator45/watchdog.sh '+archive+'/watchdog-before.sh; cp '+d['stage']+'/parent.log '+archive+'/parent-before.log')
 for pid in dev('pidof com.ss.android.article.news').split():
  dev('cp '+d['runtime']+'/private-tmp/adapter_child_'+pid+'.stderr '+archive+'/child-'+pid+'.stderr 2>/dev/null')
  checked_kill(pid)
 checked_kill(dev('cat /data/local/tmp/operator45/parent.pid').strip())
 dev('rm -f /data/local/tmp/operator45/guard.pid; rmdir /data/local/tmp/operator45/guard.lock 2>/dev/null')
 inputs=[('webview-t-lib/libwebview_bionic_shim.so','out-wv46/patched/libwebview_bionic_shim.so','ecc7b12c3591c979f3d9aece5bb1d414acc04d01d2c500a88364525082f9df9f'),('liboh_adapter_bridge.so','out-mc46/patched/liboh_adapter_bridge.so','d4fae8e5802f3153a85175243edf665714900381d463ffc5ca1e64d0b308775b'),('lib/arm64-v8a/libnpth.so','out-npth46/libnpth.so','8b8d559c50130a997b5fbf3383e8ebf6291ebe54ab2b5ed5fbc8e1ac73fe36af')]
 records=[]
 def install(source,target):
  before=dev('sha256sum '+target).split()[0]
  backup=archive+'/'+pathlib.Path(target).name+'.'+before
  dev('cp '+target+' '+backup);assert dev('sha256sum '+backup).split()[0]==before
  send(source,target+'.morning46');dev('chmod 644 '+target+'.morning46; mv '+target+'.morning46 '+target)
  after=dev('sha256sum '+target).split()[0];assert after==sha(source)
  records.append({'target':target,'backup':backup,'before':before,'after':after})
 for rel,source,expected in inputs:
  p=pathlib.Path.home()/'a2hlab/ws'/source;assert sha(p)==expected
  install(p,d['runtime']+'/'+rel)
 before=r/'run-before.sh';after=r/'run.sh';recv(d['runtime']+'/run.sh',before)
 helper='/Users/zhaoyue/orca/workspaces/westlake-harness-triage46/benchmark/2026-09-26-toutiao-crash-triage/scripts/apply_tt_targets.py'
 subprocess.run([sys.executable,helper,str(before),str(after),'libttcrypto.so,libttboringssl.so,libdelta.so,liblynxsecurity.so'],check=True)
 install(after,d['runtime']+'/run.sh');dev('chmod 755 '+d['runtime']+'/run.sh')
 setup=dev('date '+time.strftime('%m%d%H%M%Y.%S')+'; echo 1048576 > /proc/sys/vm/max_map_count; cat /proc/sys/vm/max_map_count; power-shell timeout -o 86400000; power-shell wakeup; ifconfig wlan0; ping -c 2 -W 3 223.5.5.5')
 (r/'setup.txt').write_text(setup)
 (r/'deployment.json').write_text(json.dumps({'board':S,'runtime':d['runtime'],'stage':d['stage'],'patches':records,'app_data':'preserved; prior consent retained'},indent=2)+'\n')
 print('DEPLOYED',json.dumps(records),flush=True)
elif cmd=='launch':launch(sys.argv[2])
else:raise SystemExit('deploy | launch NAME')
