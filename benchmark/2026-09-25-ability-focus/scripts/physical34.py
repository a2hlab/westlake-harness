"""Physical uinput only; fresh view snapshots and authoritative main-loop idle gate."""
from launch34 import *
name,mode=sys.argv[1:3]
assert mode in ('article','tab','scroll')
origin=next((x.split('=',1)[1] for x in sys.argv if x.startswith('--origin=')),None)
dev('power-shell dump -t; power-shell wakeup');dev('aa start -b org.westlake.imehost -a EntryAbility');time.sleep(1)
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
start=time.monotonic();consent=False;ready=False
try:
 action('power-shell dump -t; power-shell wakeup','keep-screen-on')
 while time.monotonic()-start<180:
  raw=vt('latest-vt')
  if not consent and '"同意"' in raw:
   found=list(re.finditer(r'rect=\[(\d+),(\d+) (\d+)x(\d+)\].*\"同意\"',raw))
   if found:
    x,y,w,h=map(int,found[-1].groups())
    shot('consent-before');action(f'uinput -T -d {x+w//2} {y+h//2} -u {x+w//2} {y+h//2}','SETUP_ONLY_uinput_consent');consent=True
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
finally:
 collect(r,d);stop(d);print('COLLECTED_STOPPED',name,flush=True)
