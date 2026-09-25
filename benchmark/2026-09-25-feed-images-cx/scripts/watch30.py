from launch30 import *
args=[x for x in sys.argv[1:] if not x.startswith('--')]
name,variant=args[:2]
r,d=restart(name,args[2]) if len(args)>2 else launch(name,variant);pid=d['child'];log=d['runtime']+f'/private-tmp/adapter_child_{pid}.stderr'
preview=pathlib.Path(__file__).resolve().parents[1]/'preview'/name;preview.mkdir(parents=True,exist_ok=True)
print('LAUNCHED',name,pid,flush=True)
def action(c):
 t=time.time();out=dev(c)
 with (r/'actions.jsonl').open('a') as f:f.write(json.dumps({'epoch':t,'command':c,'output':out})+'\n')
 return out
(r/'network-before.txt').write_text(action('ping -c 5 -W 2 1.1.1.1'))
(r/'start-state.txt').write_text(action(f'cat /proc/{pid}/stat; cat /proc/uptime; iptables -S OUTPUT; ip6tables -S OUTPUT; ifconfig wlan0'))
start=time.monotonic();consent=False;last_shot=-100;last_login=-100;first=None;explored=False;clicked=False
try:
 action('aa start -b org.westlake.imehost -a EntryAbility')
 while time.monotonic()-start<180 and not (r/'stop-request').exists():
  elapsed=time.monotonic()-start
  action('echo v > /data/local/tmp/noice_tap');time.sleep(.5)
  raw=dev('tail -n 1600 '+log)
  if not consent and '"同意"' in raw:
   (r/'consent-vt.txt').write_text(raw);action('echo c 600 1273 > /data/local/tmp/noice_tap');consent=True
  if '登录体验 完整功能' in raw and elapsed-last_login>15:
   action('echo back > /data/local/tmp/noice_tap');last_login=elapsed
  if ('FontTextView' in raw and '"头条"' in raw) or elapsed>60:
   if elapsed-last_shot>=10:
    action('aa start -b org.westlake.imehost -a EntryAbility');time.sleep(1)
    n=f'frame-{int(elapsed):03}.jpeg';remote='/data/local/tmp/images30-'+n
    action('snapshot_display -f '+remote+' >/dev/null');recv(remote,r/n);(preview/n).write_bytes((r/n).read_bytes())
    (r/(n+'.txt')).write_text(raw)
    (preview/'latest.json').write_text(json.dumps({'elapsed':elapsed,'file':str(preview/n),'pid':pid}))
    last_shot=elapsed;print('FRAME',name,n,flush=True)
    if '--scroll' in sys.argv and elapsed>=100 and not explored:
     action('echo 600 1650 600 500 > /data/local/tmp/noice_tap');explored=True
    if '--article' in sys.argv and elapsed>=70 and not clicked:
     action('echo i 380 297 > /data/local/tmp/noice_tap');clicked=True
    (r/'maps.txt').write_text(dev(f'cat /proc/{pid}/maps'))
  if '[INITCHILD-FAIL]' in raw or not dev(f'cat /proc/{pid}/stat 2>/dev/null').strip():
   (r/'ui-exit-tail.txt').write_text(raw);print('UI_EXIT',name,flush=True);break
  time.sleep(1)
finally:
 collect(r,d);(r/'end-state.txt').write_text(action(f'cat /proc/{pid}/stat; cat /proc/uptime'));stop(d)
 print('COLLECTED_STOPPED',name,flush=True)
