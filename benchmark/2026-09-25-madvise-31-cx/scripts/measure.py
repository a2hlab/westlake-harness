from launch30 import *
import argparse,gzip
ap=argparse.ArgumentParser();ap.add_argument('name');ap.add_argument('variant',choices=['baseline','candidate']);ap.add_argument('--p2-wait',type=int,default=120);a=ap.parse_args()
r,d=launch(a.name,a.variant);pid=d['child'];log=d['runtime']+f'/private-tmp/adapter_child_{pid}.stderr';t0=float(d['spawn_uptime_before'].split()[0]);trace=False;trace_stopped=False;consent=False;lastshot=-10;lastlogin=-100;events=[]
def now():return float(dev('cat /proc/uptime').split()[0])-t0
def event(kind,**kw):
 e={'kind':kind,'elapsed':now(),**kw};events.append(e);(r/'events.json').write_text(json.dumps(events,indent=2));print(a.name,e,flush=True)
def finishtrace():
 global trace
 path='/data/local/tmp/madvise31-'+a.name+'.trace.gz'
 dev('echo 0 > /sys/kernel/tracing/tracing_on')
 result=dev('cat /sys/kernel/tracing/trace | gzip -1 > '+path,180)
 (r/'trace-finish.txt').write_text(result+dev('hitrace --trace_finish_nodump',60))
 recv(path,r/'sched.trace.gz');trace=True;event('trace_saved')

try:
 event('launched',pid=pid,t0_uptime=t0,p2_wait=a.p2_wait)
 dev('aa start -b org.westlake.imehost -a EntryAbility')
 while now()<a.p2_wait:
  elapsed=now()
  if elapsed>=30 and not trace_stopped:
   dev('echo 0 > /sys/kernel/tracing/tracing_on');trace_stopped=True;event('trace_stopped')
  stat=dev(f'cat /proc/{pid}/stat 2>/dev/null')
  if not stat.strip():event('process_exited');break
  dev('echo v > /data/local/tmp/noice_tap');time.sleep(.25)
  raw=dev('tail -n 1500 '+log)
  if elapsed-lastshot>=5:
   n=f'frame-{elapsed:07.2f}';(r/(n+'.txt')).write_text(raw)
   before=now();remote='/data/local/tmp/madvise31-frame.jpeg';dev('snapshot_display -f '+remote+' >/dev/null');after=now();recv(remote,r/(n+'.jpeg'));event('frame',name=n,lower=before,upper=after);lastshot=elapsed
   (r/'threads.txt').write_text(dev(f'for x in /proc/{pid}/task/*; do cat $x/stat; done'))
  if not consent and '"同意"' in raw:
   (r/'consent-vt.txt').write_text(raw);event('consent_inject');dev('echo c 600 1273 > /data/local/tmp/noice_tap');consent=True
  if '登录体验 完整功能' in raw and elapsed-lastlogin>15:dev('echo back > /data/local/tmp/noice_tap');event('login_back');lastlogin=elapsed
  if '[INITCHILD-FAIL]' in raw:event('ui_failed');break
  time.sleep(.5)
finally:
 if not trace:finishtrace()
 (r/'end-state.txt').write_text(dev(f'cat /proc/{pid}/stat; cat /proc/uptime'))
 collect(r,d);stop(d);event('collected_stopped')
