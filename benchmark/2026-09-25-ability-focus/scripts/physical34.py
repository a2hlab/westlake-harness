"""Physical uinput only; fresh view snapshots and authoritative main-loop idle gate."""
from launch34 import *
name,mode=sys.argv[1:3]
assert mode in ('article','tab','scroll')
origin=next((x.split('=',1)[1] for x in sys.argv if x.startswith('--origin=')),None)
dev('power-shell dump -t; power-shell wakeup');dev('aa start -b org.westlake.imehost -a EntryAbility');time.sleep(1)
dev('uinput -T -d 1150 1140 -u 1150 1140') # SETUP_ONLY: dismiss known host keyboard before spawning.
r,d=restart(name,origin) if origin else launch(name,'full');pid=d['child'];log=d['runtime']+f'/private-tmp/adapter_child_{pid}.stderr'
preview=pathlib.Path(__file__).resolve().parents[1]/'preview'/name;preview.mkdir(parents=True,exist_ok=True)
def action(c,kind='observe',timeout=60):
 out=dev(c,timeout)
 with (r/'actions.jsonl').open('a') as f:f.write(json.dumps({'epoch':time.time(),'kind':kind,'command':c,'output':out})+'\n')
 return out
def shot(label):
 remote='/data/local/tmp/ability38-physical.jpeg';action('snapshot_display -f '+remote+' >/dev/null')
 recv(remote,r/(label+'.jpeg'));(preview/(label+'.jpeg')).write_bytes((r/(label+'.jpeg')).read_bytes())
def vt(label):
 line=int(dev('wc -l < '+log).strip())
 action('echo v > /data/local/tmp/noice_tap');time.sleep(.8)
 raw=dev(f'tail -n +{line+1} '+log);(r/(label+'.txt')).write_text(raw);return raw
for fp in d.get('touch',{}).get('forwarder_pid','').split():
 exe=action(f'readlink /proc/{int(fp)}/exe').strip()
 if 'touchfwd' in exe and 'a2hlab-' in exe:action(f'kill {int(fp)}','disable-forwarder')
print('LAUNCHED',name,pid,flush=True)
start=time.monotonic();consent=False;ready=False;consent_done=None;sampler_pid=None;pause_pid=None
delay=next((float(x.split("=",1)[1]) for x in sys.argv if x.startswith("--delay-consent=")),None)
try:
 action('power-shell dump -t; power-shell wakeup','keep-screen-on')
 while time.monotonic()-start<180:
  raw=vt('latest-vt')
  if not consent and '"同意"' in raw and time.monotonic()-start>100:
   found=list(re.finditer(r'rect=\[(\d+),(\d+) (\d+)x(\d+)\].*\"同意\"',raw))
   if found:
    x,y,w,h=map(int,found[-1].groups())
    shot('consent-before');action('echo CONSENT_BEFORE; cat /proc/uptime; uinput -T -d 600 1273 -u 600 1273; echo CONSENT_AFTER; cat /proc/uptime','SETUP_ONLY_uinput_consent');consent=True;consent_done=time.monotonic()
  if '[INITCHILD-FAIL]' in raw or not dev(f'cat /proc/{pid}/stat 2>/dev/null').strip():
   print('UI_EXIT_BEFORE_TEST',flush=True);break
  if '"同意"' not in raw and 'FeedCommonRecyclerView' in raw and ('FeedLightTextView' in raw or 'FeedTitleTextView' in raw) and time.monotonic()-start > (10 if '--warm' in sys.argv else 50):
   ready=True;break
  time.sleep(1)
 if ready and '--wait-idle' in sys.argv:
  idle=False
  for attempt in range(70):
   line=int(action('wc -l < '+log).strip())
   action('echo T > /data/local/tmp/noice_tap','STACK_ONLY_T');time.sleep(.8)
   stacks=action(f'tail -n +{line+1} '+log+' | grep JSTACK')
   (r/f'idle-stack-{attempt:02d}.txt').write_text(stacks)
   groups=stacks.split('JSTACK -- ')
   main=next((x for x in groups if 'android.app.ActivityThread.main' in x),'')
   if re.search(r'JSTACK\s+#0 android.os.MessageQueue.nativePollOnce',main):
    action('cat /proc/uptime','MAIN_IDLE_OBSERVED');idle=True;break
   if action("grep -m 1 '^\\[INITCHILD-FAIL\\]' "+log).strip():break
   if not dev(f'cat /proc/{pid}/stat 2>/dev/null').strip():break
   time.sleep(1.5)
  if not idle:raise RuntimeError('Main loop did not reach nativePollOnce; no acceptance touch')
 if ready:
  if delay is not None:
   if consent_done is None:raise RuntimeError('Fixed-age trial requires actual consent')
   time.sleep(max(0,consent_done+delay-10-time.monotonic()))
   if '--npth-pause' in sys.argv:
    cmd=f'/data/local/tmp/ability38-proc pause {pid} 75'
    pause_pid=int(action('nohup '+cmd+' > /data/local/tmp/ability38-pause-npth.log 2>&1 </dev/null & echo $!','NPTH_SINGLE_THREAD_PAUSE').strip())
    (r/'npth-pause-launch.txt').write_text(str(pause_pid))
    time.sleep(1)
    state=action('cat /data/local/tmp/ability38-pause-npth.log')
    (r/'npth-pause-before.txt').write_text(state)
    if 'PAUSED_MATCHED_LOOP' not in state:raise RuntimeError('npth loop intervention not established')
   (r/'maps-before.txt').write_text(action(f'cat /proc/{pid}/maps'))
   (r/'tasks-before.txt').write_text(action(f'cat /proc/{pid}/task/*/stat'))
   (r/'cmdline-before.txt').write_text(action(f'cat /proc/{pid}/cmdline'))
   (r/'clock-ticks.txt').write_text(action('getconf CLK_TCK'))
  shot('before');vt('before')
  if '--manual-ready' in sys.argv:
   print('READY_FOR_SCREENSHOT_CHECK',flush=True)
   deadline=time.monotonic()+300
   while not (r/'go-physical').exists():
    if time.monotonic()>deadline:raise RuntimeError('No validated visible feed before physical action')
    time.sleep(.2)
   shot('before-final');vt('before-final')
  (r/'window-before.txt').write_text(action('hidumper -s WindowManagerService -a "-a"'))
  n=int(action('wc -l < '+log).strip())
  gesture='uinput -T -d 380 297 -u 380 297' if mode=='article' else 'uinput -T -d 306 210 -u 306 210' if mode=='tab' else 'uinput -T -m 600 1600 600 500'
  if mode=='article' and '--select-title' in sys.argv:
   selection=vt('selection')
   candidates=re.findall(r'VT +Feed(?:Title|Light)TextView[^\n]*rect=\[(\d+),(\d+) (\d+)x(\d+)\][^"\n]*"([^"\n]+)"',selection)
   candidates=[(int(x),int(y),int(w),int(h),text) for x,y,w,h,text in candidates if int(w)>300 and 254<=int(y)<800]
   if not candidates:raise RuntimeError('No visible feed title for physical selection')
   x,y,w,h,title=min(candidates,key=lambda z:z[1]);tx=min(x+w//2,600);ty=y+h//2
   (r/'selected-title.json').write_text(json.dumps({'text':title,'rect':[x,y,w,h],'touch':[tx,ty]},ensure_ascii=False))
   gesture=f'uinput -T -d {tx} {ty} -u {tx} {ty}'
  if '--profile-detail' in sys.argv:
   early=action("grep -m 1 '^\\[TOUCH21-POLL\\] enter' "+log)
   main_tid=int(re.search(r'\[TOUCH21-POLL\] enter now=\d+ tid=(\d+)',early)[1])
   (r/'main-thread.json').write_text(json.dumps({'pid':pid,'tid':main_tid,'exclude_from_latency_cohort':True}))
   (r/'maps-before.txt').write_text(action(f'cat /proc/{pid}/maps'))
   (r/'tasks-before.txt').write_text(action(f'cat /proc/{pid}/task/*/stat'))
   perf_command=f'echo PROFILE_BEFORE; cat /proc/uptime; /bin/hiperf record -p {pid} -d 20 -f 400 -e sw-task-clock -s dwarf,16384 --symbol-dir /data/local/tmp/a2hlab-framework-ability38-v7 -o /data/local/tmp/ability38-detail.data; echo PROFILE_RC=$?; cat /proc/uptime'
   action('nohup /system/bin/sh -c '+shlex.quote(perf_command)+' >/data/local/tmp/ability38-detail-record.txt 2>&1 </dev/null & echo $!','CPU_PROFILE_NOT_LATENCY')
   time.sleep(.5)
  if '--offcpu' in sys.argv:
   early=action("grep -m 1 '^\\[TOUCH21-POLL\\] enter' "+log)
   main_tid=int(re.search(r'\[TOUCH21-POLL\] enter now=\d+ tid=(\d+)',early)[1])
   (r/'main-thread.json').write_text(json.dumps({'pid':pid,'tid':main_tid,'offcpu_interval_ms':50,'java_request_interval_ms':500}))
   (r/'fds-before.txt').write_text(action(f'ls -l /proc/{pid}/fd'))
   cmd=f'/data/local/tmp/ability38-proc sample {pid} {main_tid} 60 /data/local/tmp/noice_tap'
   sampler_pid=int(action('nohup '+cmd+' >/data/local/tmp/ability38-offcpu.txt 2>&1 </dev/null & echo $!','OFFCPU_SAMPLER').strip())
  if delay is not None:
   if time.monotonic()>consent_done+delay+2:raise RuntimeError('Missed fixed consent-age deadline')
   time.sleep(max(0,consent_done+delay-time.monotonic()))
  command='echo INPUT_BEFORE; cat /proc/uptime; '+gesture+'; echo INPUT_AFTER; cat /proc/uptime'
  (r/'physical-result.txt').write_text(action(command,'UINPUT_ACCEPTANCE',30))
  touch_done=time.monotonic()
  for deadline,label in [(2,'after-2s'),(5,'after-5s'),(15,'after-15s'),(45,'after-45s')]:
   time.sleep(max(0,touch_done+deadline-time.monotonic()))
   action('cat /proc/uptime','SCREENSHOT_TIME_'+label);shot(label);vt(label)
   fresh=action(f'tail -n +{n+1} '+log)
   lines=[line for line in fresh.splitlines() if line.startswith('[B47-SLA]')]
   (r/(label+'-lifecycle.txt')).write_text('\n'.join(lines)+'\n')
  print('PHYSICAL_ACTION_COMPLETE',mode,flush=True)
  (r/'window-after.txt').write_text(action('hidumper -s WindowManagerService -a "-a"'))
  if '--profile-detail' in sys.argv:
   recv('/data/local/tmp/ability38-detail.data',r/'perf.data')
   recv('/data/local/tmp/ability38-detail-record.txt',r/'record.txt')
   for label,filters in [('main',f'--tids {main_tid}'),('render','--comms RenderThread'),('all','')]:
    (r/f'report-{label}.txt').write_text(action(f'/bin/hiperf report -i /data/local/tmp/ability38-detail.data --symbol-dir /data/local/tmp/a2hlab-framework-ability38-v7 {filters} --sort tid,comm,dso,func --limit-percent 0',timeout=180))
   (r/'report-stacks.txt').write_text(action(f'/bin/hiperf report -i /data/local/tmp/ability38-detail.data --symbol-dir /data/local/tmp/a2hlab-framework-ability38-v7 --tids {main_tid} --sort tid,comm,dso,func -s --limit-percent 0.1',timeout=180))
finally:
 for helper in (sampler_pid,pause_pid):
  if helper and action(f'readlink /proc/{helper}/exe').strip()=='/data/local/tmp/ability38-proc':action(f'kill {helper}')
 if '--offcpu' in sys.argv:
  recv('/data/local/tmp/ability38-offcpu.txt',r/'offcpu.txt')
 if '--npth-pause' in sys.argv:
  (r/'npth-pause-after.txt').write_text(action('cat /data/local/tmp/ability38-pause-npth.log'))
 collect(r,d);stop(d);print('COLLECTED_STOPPED',name,flush=True)
