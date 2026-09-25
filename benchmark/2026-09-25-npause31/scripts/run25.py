from board25 import *
import threading
A=pathlib.Path('/home/dspfac/a2hlab/source-closure/verify')
UID=20010053
PKG='com.ss.android.article.news'
def network(offline):
 for binary in ['iptables','ip6tables']:
  rule=f'-m owner --uid-owner {UID} -m comment --comment touch25 -j DROP'
  if offline:dev(f'{binary} -C OUTPUT {rule} 2>/dev/null || {binary} -I OUTPUT 1 {rule}')
  else:dev(f'{binary} -C OUTPUT {rule} 2>/dev/null && {binary} -D OUTPUT {rule}; true')
 return dev('iptables -nvxL OUTPUT; ip6tables -nvxL OUTPUT; ifconfig wlan0')
def collect(r,d):
 for key,path in [('child.stderr',d['runtime']+'/private-tmp/adapter_child_'+str(d['child'])+'.stderr'),('parent.log',d['stage']+'/parent.log')]:
  recv(path,r/key)
 faults=dev(f'find /data/log/faultlog -type f -name "*-{d["child"]}-*"')
 (r/'fault-paths.txt').write_text(faults)
 for f in faults.splitlines():
  if f.startswith('/'):recv(f,r/pathlib.Path(f).name)
def stop(d,parent=True):
 for key in (['child','parent'] if parent else ['child']):
  p=d[key];st=dev(f'cat /proc/{p}/stat 2>/dev/null')
  if ') ' in st:
   start=st.rsplit(') ',1)[1].split()[19];now=dev(f'cat /proc/{p}/stat 2>/dev/null')
   if ') ' in now and now.rsplit(') ',1)[1].split()[19]==start:dev(f'kill -9 {p}')
def launch(name,old=None):
 r=R/name
 if old:
  r.mkdir();d=json.loads((old/'device-report.json').read_text());prev=d['child']
  rows=[json.loads(l) for l in (old/'commands.jsonl').read_text().splitlines()]
  c=next(x['command'] for x in rows if '/host_spawn /dev/unix' in x['command'])
  reply=dev(c);d['child']=int(re.search(r'result=0 pid=(\d+)',reply)[1])
  (r/'reuse.json').write_text(json.dumps({'previous_run':str(old),'previous_child':prev,'command':c,'reply':reply},indent=2))
  (r/'commands.jsonl').write_text((old/'commands.jsonl').read_text())
  (r/'device-report.json').write_text(json.dumps(d,indent=2))
  box=f'/proc/{d["child"]}/root/data/local/tmp/noice_tap.{d["child"]}'
  dev(f': > {box}; chown {UID}:{UID} {box}; chmod 666 {box}; ln -sf {box} /data/local/tmp/noice_tap')
 else:
  cmd=['python3',str(A/'out-touch21/probe-local/tools/probe_source_app.py'),'--workspace',str(A),'--westlake-source',str(A/'westlake-touch21'),'--framework-report',str(R/'framework-wake/device-report.json'),'--app-input',str(pathlib.Path.home()/'a2hlab/app-inputs/toutiao'),'--app','toutiao','--hdc',H,'--serial',S,'--out',str(r),'--host-build',str(A/'out/signed-host'),'--webview-input',str(A/'out/webview-input-source'),'--source-webview-build',str(A/'out-sp20/webview-candidate'),'--runtime-env','WL_TOUCH_TRACE=1','--android-native-target','libvision_core.so','--android-native-target','libc++_shared.so','--android-native-target','libsscronet.so','--android-native-net-target','libsscronet.so']
  with (R/(name+'.log')).open('w') as f:subprocess.run(cmd,cwd=pathlib.Path.home()/'a2hlab/manifest',stdout=f,stderr=subprocess.STDOUT,check=True)
  d=json.loads((r/'device-report.json').read_text())
 return r,d
def measure(r,d,fresh):
 pid=d['child'];log=d['runtime']+f'/private-tmp/adapter_child_{pid}.stderr'
 events=[]
 def action(c):
  t=time.time();o=dev(c);events.append({'epoch':t,'command':c,'output':o});(r/'actions.json').write_text(json.dumps(events,indent=2));return o
 action(f'cat /proc/{pid}/status; readlink /data/local/tmp/noice_tap; cat /proc/uptime')
 start=time.monotonic();consented=not fresh
 for i in range(130):
  action('echo v > /data/local/tmp/noice_tap');time.sleep(.4)
  raw=dev('tail -n 900 '+log)
  if not consented and '"同意"' in raw:
   (r/'consent-vt.txt').write_text(raw);action('echo c 600 1273 > /data/local/tmp/noice_tap');consented=True
  if consented and ('FontTextView' in raw and '"头条"' in raw):
   (r/'before-vt.txt').write_text(raw);break
  if '[INITCHILD-FAIL]' in raw:raise RuntimeError('UI exited before measurement')
  if time.monotonic()-start>110:raise RuntimeError('No category UI')
 else:raise RuntimeError('No category UI')
 action('aa start -b org.westlake.imehost -a EntryAbility')
 time.sleep(1)
 # Baseline: no SIGQUIT during the click; identify main afterwards.
 action('echo i 309 213 > /data/local/tmp/noice_tap')
 for i in range(60):
  time.sleep(1)
  tail=dev('tail -n 1800 '+log)
  if '[TOUCH21] run action=1 ' in tail:break
 else:raise RuntimeError('Touch not consumed in 60s')
 action(f'kill -3 {pid}')
 time.sleep(1)
 action('echo v > /data/local/tmp/noice_tap');time.sleep(2)
 (r/'after-tail.txt').write_text(dev('tail -n 1600 '+log))
 (r/'network-end.txt').write_text(dev('iptables -nvxL OUTPUT; ip6tables -nvxL OUTPUT; ifconfig wlan0'))
 collect(r,d)
 print('MEASURED',r.name,flush=True)
if __name__=='__main__':
 mode=sys.argv[1]
 if mode=='online':print(network(False));sys.exit()
 offline=mode=='offline';rep=sys.argv[2]
 (R/f'{mode}-{rep}-network.txt').write_text(network(offline))
 d=None
 try:
  r,d=launch(f'{mode}-fresh-{rep}');print('LAUNCHED',r.name,d['child'],flush=True)
  measure(r,d,True);stop(d,parent=False)
  if len(sys.argv)>3 and sys.argv[3]=='fresh-only':
   stop(d);sys.exit()
  r2,d2=launch(f'{mode}-reuse-{rep}',r);d=d2;print('LAUNCHED',r2.name,d2['child'],flush=True)
  measure(r2,d2,False);stop(d2)
 except Exception:
  if d:
   try:collect(r2 if 'r2' in locals() else r,d);stop(d)
   except Exception as e:print('cleanup error',repr(e),flush=True)
  raise
 finally:network(False)
