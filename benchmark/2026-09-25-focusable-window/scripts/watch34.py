from launch34 import *
args=[x for x in sys.argv[1:] if not x.startswith('--')]
name,variant=args[:2]
app=next((x.split('=',1)[1] for x in sys.argv if x.startswith('--app=')),'toutiao')
r,d=restart(name,args[2]) if len(args)>2 else launch(name,variant,app);pid=d['child'];log=d['runtime']+f'/private-tmp/adapter_child_{pid}.stderr'
preview=pathlib.Path(__file__).resolve().parents[1]/'preview'/name;preview.mkdir(parents=True,exist_ok=True)
print('LAUNCHED',name,pid,flush=True)
def action(c):
 t=time.time();out=dev(c)
 with (r/'actions.jsonl').open('a') as f:f.write(json.dumps({'epoch':t,'command':c,'output':out})+'\n')
 return out
(r/'start-state.txt').write_text(action(f'cat /proc/{pid}/stat; cat /proc/uptime; iptables -S OUTPUT; ip6tables -S OUTPUT; ifconfig wlan0'))
if '--candidate' in sys.argv:
 for fp in d.get('touch',{}).get('forwarder_pid','').split():
  exe=action(f'readlink /proc/{int(fp)}/exe').strip()
  if 'touchfwd' in exe and 'a2hlab-' in exe: action(f'kill {int(fp)}')
start=time.monotonic();consent=False;last_shot=-100;last_login=-100;first=None;explored=False;clicked=False
try:
 action('aa start -b org.westlake.imehost -a EntryAbility')
 while time.monotonic()-start<300 and not (r/'stop-request').exists():
  elapsed=time.monotonic()-start
  action('echo v > /data/local/tmp/noice_tap');time.sleep(.5)
  raw=dev('tail -n 1600 '+log)
  if not consent and '"同意"' in raw:
   (r/'consent-vt.txt').write_text(raw);action('echo c 600 1273 > /data/local/tmp/noice_tap');consent=True
  if '登录体验 完整功能' in raw and elapsed-last_login>15:
   action('echo back > /data/local/tmp/noice_tap');last_login=elapsed
  if ('FontTextView' in raw and '"头条"' in raw) or elapsed>60:
   if elapsed-last_shot>=10:
    action('aa start -b org.westlake.imehost -a EntryAbility')
    time.sleep(1)
    n=f'frame-{int(elapsed):03}.jpeg';remote='/data/local/tmp/focus34-'+n
    action('snapshot_display -f '+remote+' >/dev/null');recv(remote,r/n);(preview/n).write_bytes((r/n).read_bytes())
    (r/(n+'.txt')).write_text(raw)
    (preview/'latest.json').write_text(json.dumps({'elapsed':elapsed,'file':str(preview/n),'pid':pid}))
    last_shot=elapsed;print('FRAME',name,n,flush=True)
    if '--scroll' in sys.argv and elapsed>=100 and not explored:
     action('echo 600 1650 600 500 > /data/local/tmp/noice_tap');explored=True
    if '--hardware' in sys.argv and elapsed>=55 and not clicked:
     xy='380 297' if app=='toutiao' else '1119 1840' if app=='noice' else '1149 1867'
     command=f'cat /proc/uptime; uinput -T -d {xy} -u {xy}; cat /proc/uptime'
     if app=='toutiao':
      command += f'; n=0; while [ "$n" -lt 100 ]; do if grep -m 1 "B47-SLA.*ENTRY.*NewDetailActivity" {log}; then cat /proc/uptime; break; fi; n=$((n+1)); sleep 0.05; done; cat /proc/uptime'
     action(command)
     if app=='toutiao':
      action(command)
     clicked=True
     (r/'physical-input-state.txt').write_text(action('hidumper -s WindowManagerService -a "-a"'))
    if '--baseline-fallback' in sys.argv and elapsed>=95 and not explored:
     action('echo i 380 297 > /data/local/tmp/noice_tap');explored=True
    if '--article' in sys.argv and elapsed>=70 and not clicked:
     action('echo i 380 297 > /data/local/tmp/noice_tap');clicked=True
    (r/'maps.txt').write_text(dev(f'cat /proc/{pid}/maps'))
  if '[INITCHILD-FAIL]' in raw or not dev(f'cat /proc/{pid}/stat 2>/dev/null').strip():
   (r/'ui-exit-tail.txt').write_text(raw);print('UI_EXIT',name,flush=True);break
  time.sleep(1)
finally:
 collect(r,d);(r/'end-state.txt').write_text(action(f'cat /proc/{pid}/stat; cat /proc/uptime'));stop(d)
 print('COLLECTED_STOPPED',name,flush=True)
